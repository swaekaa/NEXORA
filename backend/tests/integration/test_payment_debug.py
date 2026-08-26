import uuid
import json
import pytest
from httpx import AsyncClient
from decimal import Decimal

from app.models.agreement import Agreement, AgreementStatus
from app.models.payment import PaymentStatus
from app.models.negotiation import Negotiation, NegotiationState
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.buyer import Buyer
from app.models.merchant import Merchant
from app.models.product import Product
from app.payments.razorpay_client import get_razorpay_client, FakeRazorpayClient
from app.services.payment_service import initiate_payment, process_webhook_event

pytestmark = pytest.mark.asyncio

@pytest.fixture
def fake_razorpay():
    return FakeRazorpayClient()

@pytest.fixture
async def db_session():
    from app.database.connection import get_db
    async for session in get_db():
        yield session
        await session.rollback()

@pytest.fixture(autouse=True)
def override_razorpay_dependency(app, fake_razorpay):
    app.dependency_overrides[get_razorpay_client] = lambda: fake_razorpay
    yield
    app.dependency_overrides.clear()

@pytest.fixture
async def setup_db_entities(db_session: AsyncSession):
    buyer_id = uuid.uuid4()
    merchant_id = uuid.uuid4()
    product_id = uuid.uuid4()
    
    buyer = Buyer(id=buyer_id, name="Test Buyer", email=f"buyer_{buyer_id}@test.com")
    merchant = Merchant(id=merchant_id, name="Test Merchant", email=f"merchant_{merchant_id}@test.com")
    
    db_session.add(buyer)
    db_session.add(merchant)
    await db_session.flush()
    
    product = Product(
        id=product_id,
        merchant_id=merchant_id,
        sku=f"sku_{product_id}",
        name="Test Product",
        description="A product for testing.",
        price=Decimal("1500.00"),
        inventory=1000
    )
    db_session.add(product)
    await db_session.flush()
    
    from app.models.policy import Policy
    policy = Policy(
        merchant_id=merchant_id,
        name="Test Policy",
        minimum_price=Decimal("10.0"),
        maximum_discount_percent=Decimal("50.0"),
        maximum_autonomous_transaction=Decimal("50000.0"),
        human_approval_required=False,
        is_active=True
    )
    db_session.add(policy)
    await db_session.flush()
    
    return buyer_id, merchant_id, product_id


async def test_initiate_payment_api(client: AsyncClient, db_session, setup_db_entities):
    buyer_id, merchant_id, product_id = setup_db_entities
    
    negotiation = Negotiation(
        buyer_id=buyer_id,
        merchant_id=merchant_id,
        product_id=product_id,
        state=NegotiationState.ACCEPTED.value,
        round_count=1
    )
    db_session.add(negotiation)
    await db_session.flush()
    
    agreement = Agreement(
        negotiation_id=negotiation.id,
        merchant_id=merchant_id,
        buyer_id=buyer_id,
        product_id=product_id,
        product_name="Test Product",
        quantity=10,
        unit_price=Decimal("1500.00"),
        total_amount=Decimal("15000.00"),
        currency="INR",
        payment_terms="upfront",
        delivery_days=5,
        warranty_months=12,
        status=AgreementStatus.VALIDATED.value
    )
    db_session.add(agreement)
    await db_session.commit()
    await db_session.refresh(agreement)
    
    response = await client.post(
        "/api/v1/payments/initiate", 
        json={"agreement_id": str(agreement.id)}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["amount_paise"] == 1500000
    assert data["status"] == PaymentStatus.CREATED.value
    assert "razorpay_order_id" in data


async def test_webhook_api(client: AsyncClient, db_session, setup_db_entities):
    buyer_id, merchant_id, product_id = setup_db_entities
    
    negotiation = Negotiation(
        buyer_id=buyer_id,
        merchant_id=merchant_id,
        product_id=product_id,
        state=NegotiationState.ACCEPTED.value,
        round_count=1
    )
    db_session.add(negotiation)
    await db_session.flush()
    
    agreement = Agreement(
        negotiation_id=negotiation.id,
        merchant_id=merchant_id,
        buyer_id=buyer_id,
        product_id=product_id,
        product_name="Test Product",
        quantity=10,
        unit_price=Decimal("1500.00"),
        total_amount=Decimal("15000.00"),
        currency="INR",
        payment_terms="upfront",
        delivery_days=5,
        warranty_months=12,
        status=AgreementStatus.VALIDATED.value
    )
    db_session.add(agreement)
    await db_session.commit()
    await db_session.refresh(agreement)
    
    initiate_resp = await client.post(
        "/api/v1/payments/initiate", 
        json={"agreement_id": str(agreement.id)}
    )
    assert initiate_resp.status_code == 200, initiate_resp.text
    order_id = initiate_resp.json()["razorpay_order_id"]
    
    payment_id = f"pay_fake_{uuid.uuid4().hex[:8]}"
    
    payload = {
        "event": "payment.captured",
        "id": "evt_test_" + str(uuid.uuid4()),
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": order_id
                }
            }
        }
    }
    
    response = await client.post(
        "/api/v1/webhooks/razorpay",
        headers={"X-Razorpay-Signature": "valid_signature"},
        content=json.dumps(payload).encode("utf-8")
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.fixture
async def setup_agreement_service(db_session, setup_db_entities):
    buyer_id, merchant_id, product_id = setup_db_entities
    
    negotiation = Negotiation(
        buyer_id=buyer_id,
        merchant_id=merchant_id,
        product_id=product_id,
        state=NegotiationState.ACCEPTED.value,
        round_count=1
    )
    db_session.add(negotiation)
    await db_session.flush()
    
    agreement = Agreement(
        negotiation_id=negotiation.id,
        merchant_id=merchant_id,
        buyer_id=buyer_id,
        product_id=product_id,
        product_name="Test Product",
        quantity=10,
        unit_price=Decimal("1500.00"),
        total_amount=Decimal("15000.00"),
        currency="INR",
        payment_terms="upfront",
        delivery_days=5,
        warranty_months=12,
        status=AgreementStatus.VALIDATED.value
    )
    db_session.add(agreement)
    await db_session.commit()
    await db_session.refresh(agreement)
    return agreement

async def test_webhook_processing_success(db_session, setup_agreement_service, fake_razorpay):
    payment = await initiate_payment(db_session, setup_agreement_service.id, fake_razorpay)
    
    payment_id = f"pay_fake_{uuid.uuid4().hex[:8]}"
    
    payload = {
        "entity": "event",
        "account_id": "acc_123",
        "event": "payment.captured",
        "contains": ["payment"],
        "id": "event_valid_123_" + str(uuid.uuid4().hex[:8]),
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": payment.razorpay_order_id,
                    "status": "captured"
                }
            }
        }
    }
    raw_body = json.dumps(payload).encode("utf-8")
    signature = "valid_signature" 
    
    await process_webhook_event(db_session, raw_body, signature, fake_razorpay)
    
    await db_session.refresh(payment)
    assert payment.status == PaymentStatus.CAPTURED.value
    assert payment.razorpay_payment_id == payment_id
    
    await db_session.refresh(setup_agreement_service)
    assert setup_agreement_service.status == AgreementStatus.PAYMENT_CAPTURED.value
