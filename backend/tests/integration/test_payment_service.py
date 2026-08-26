import uuid
import json
import pytest
from decimal import Decimal
import hashlib
import hmac

from app.models.agreement import Agreement, AgreementStatus
from app.models.payment import Payment, PaymentStatus
from app.models.payment_webhook_event import PaymentWebhookEvent
from app.models.negotiation import Negotiation, NegotiationState
from app.services.payment_service import (
    initiate_payment, 
    process_webhook_event, 
    PaymentServiceError, 
    DuplicateWebhookError
)
from app.payments.razorpay_client import FakeRazorpayClient
from sqlalchemy import select
from app.database.connection import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.buyer import Buyer
from app.models.merchant import Merchant
from app.models.product import Product

pytestmark = pytest.mark.asyncio

@pytest.fixture
async def db_session():
    # Setup real DB session for integration test
    async for session in get_db():
        yield session
        await session.rollback()

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

pytestmark = pytest.mark.asyncio


@pytest.fixture
def fake_razorpay():
    return FakeRazorpayClient()


@pytest.fixture
async def setup_agreement(db_session, setup_db_entities):
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


async def test_initiate_payment_success(db_session, setup_agreement, fake_razorpay):
    payment = await initiate_payment(db_session, setup_agreement.id, fake_razorpay)
    
    assert payment.status == PaymentStatus.CREATED.value
    assert payment.amount_paise == 1500000
    assert payment.razorpay_order_id.startswith("order_fake_agr_")
    
    # Check Agreement Status
    await db_session.refresh(setup_agreement)
    assert setup_agreement.status == AgreementStatus.PAYMENT_INITIATED.value


async def test_initiate_payment_fails_if_unapproved(db_session, setup_agreement, fake_razorpay):
    setup_agreement.status = AgreementStatus.PENDING_APPROVAL.value
    db_session.add(setup_agreement)
    await db_session.commit()
    
    with pytest.raises(PaymentServiceError, match="not ready for payment"):
        await initiate_payment(db_session, setup_agreement.id, fake_razorpay)


async def test_payment_recovery_on_orphaned_order(db_session, setup_agreement, fake_razorpay):
    # Simulate first attempt where DB transaction (or network) failed but Razorpay got the order
    # so NO Payment record exists in the local DB yet, but Razorpay has an order for this receipt.
    amount_paise = 1500000
    receipt = f"agr_{str(setup_agreement.id)[:35]}"
    fake_razorpay.create_order(amount_paise, "INR", receipt, {})
    
    # Run initiate payment
    # It should detect the orphaned order by receipt and use it instead of creating a new one.
    payment = await initiate_payment(db_session, setup_agreement.id, fake_razorpay)
    
    assert payment.razorpay_order_id is not None
    # We should have used the existing order
    assert payment.razorpay_order_id == list(fake_razorpay.orders.keys())[0]
    # And we shouldn't have created a second order
    assert len(fake_razorpay.orders) == 1


async def test_webhook_processing_success(db_session, setup_agreement, fake_razorpay):
    payment = await initiate_payment(db_session, setup_agreement.id, fake_razorpay)
    
    payment_id = f"pay_fake_{uuid.uuid4().hex[:8]}"
    
    event_id = f"evt_{uuid.uuid4().hex[:8]}"
    
    payload = {
        "entity": "event",
        "account_id": "acc_123",
        "event": "payment.captured",
        "contains": ["payment"],
        "id": event_id,
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
    signature = "valid_signature" # Our fake client accepts this
    
    await process_webhook_event(db_session, raw_body, signature, fake_razorpay)
    
    await db_session.refresh(payment)
    assert payment.status == PaymentStatus.CAPTURED.value
    assert payment.razorpay_payment_id == payment_id
    
    await db_session.refresh(setup_agreement)
    assert setup_agreement.status == AgreementStatus.PAYMENT_CAPTURED.value
    
    # Check event was logged
    result = await db_session.execute(select(PaymentWebhookEvent).where(PaymentWebhookEvent.event_id == event_id))
    event = result.scalar_one()
    assert event.status == "PROCESSED"


async def test_webhook_invalid_signature(db_session, fake_razorpay):
    raw_body = b"{}"
    signature = "invalid_signature"
    
    with pytest.raises(PaymentServiceError, match="Invalid webhook signature"):
        await process_webhook_event(db_session, raw_body, signature, fake_razorpay)


async def test_webhook_duplicate_idempotency(db_session, setup_agreement, fake_razorpay):
    payment = await initiate_payment(db_session, setup_agreement.id, fake_razorpay)
    
    payment_id = f"pay_fake_{uuid.uuid4().hex[:8]}"
    
    event_id = f"evt_dup_{uuid.uuid4().hex[:8]}"
    
    payload = {
        "event": "payment.captured",
        "id": event_id,
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": payment.razorpay_order_id
                }
            }
        }
    }
    raw_body = json.dumps(payload).encode("utf-8")
    
    # First process works
    await process_webhook_event(db_session, raw_body, "valid_signature", fake_razorpay)
    
    # Second process raises DuplicateWebhookError (but HTTP endpoint catches and returns 200 OK)
    with pytest.raises(DuplicateWebhookError):
        await process_webhook_event(db_session, raw_body, "valid_signature", fake_razorpay)
