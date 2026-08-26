import uuid
import json
from decimal import Decimal
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.models.agreement import Agreement, AgreementStatus
from app.models.payment import PaymentStatus
from app.models.inventory_reservation import InventoryReservation, ReservationStatus
from app.models.product import Product
from app.models.buyer import Buyer
from app.models.merchant import Merchant
from app.models.negotiation import Negotiation, NegotiationState
from app.payments.razorpay_client import FakeRazorpayClient, get_razorpay_client
from app.database.connection import get_db

pytestmark = pytest.mark.asyncio

@pytest.fixture
async def db_session():
    async for session in get_db():
        yield session
        await session.rollback()

@pytest.fixture
def fake_razorpay():
    return FakeRazorpayClient()

@pytest.fixture(autouse=True)
def override_razorpay_dependency(app, fake_razorpay):
    app.dependency_overrides[get_razorpay_client] = lambda: fake_razorpay
    yield
    app.dependency_overrides.clear()

@pytest.fixture
async def setup_agreement(db_session: AsyncSession):
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
        delivery_days=7,
        warranty_months=12,
        status=AgreementStatus.VALIDATED.value
    )
    db_session.add(agreement)
    await db_session.commit()
    await db_session.refresh(agreement)
    return agreement

async def test_full_payment_inventory_flow(client: AsyncClient, db_session: AsyncSession, setup_agreement, fake_razorpay):
    """
    Test the full integration between Payment and Inventory.
    Agreement -> Initiation (reserves) -> Webhook (commits) -> Fulfill
    """
    # 1. Check initial inventory
    product_id = setup_agreement.product_id
    product = await db_session.get(Product, product_id)
    assert product.inventory == 1000
    
    quantity = setup_agreement.quantity
    
    # 2. Initiate Payment (Creates Order + Reservation)
    response = await client.post(
        "/api/v1/payments/initiate", 
        json={"agreement_id": str(setup_agreement.id)}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == PaymentStatus.CREATED.value
    order_id = data["razorpay_order_id"]
    
    # 3. Verify Reservation was created and inventory deducted
    await db_session.refresh(product)
    assert product.inventory == 1000 - quantity
    
    res_query = await db_session.execute(
        select(InventoryReservation).where(InventoryReservation.agreement_id == setup_agreement.id)
    )
    reservation = res_query.scalar_one()
    assert reservation.status == ReservationStatus.RESERVED.value
    assert reservation.quantity == quantity
    
    # 4. Simulate payment.captured webhook
    payment_id = f"pay_fake_{uuid.uuid4().hex[:8]}"
    event_id = f"evt_{uuid.uuid4().hex[:8]}"
    
    payload = {
        "entity": "event",
        "account_id": "acc_123",
        "event": "payment.captured",
        "id": event_id,
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": order_id,
                    "status": "captured"
                }
            }
        }
    }
    
    raw_body = json.dumps(payload).encode("utf-8")
    signature = "valid_signature" # Fake client accepts this
    
    webhook_response = await client.post(
        "/api/v1/webhooks/razorpay",
        content=raw_body,
        headers={"X-Razorpay-Signature": signature}
    )
    assert webhook_response.status_code == 200
    
    # 5. Verify Reservation is committed
    await db_session.refresh(reservation)
    assert reservation.status == ReservationStatus.COMMITTED.value
    assert reservation.expires_at is None
    
    # 6. Fulfill Reservation
    fulfill_res = await client.post(f"/api/v1/inventory/agreements/{setup_agreement.id}/fulfill")
    assert fulfill_res.status_code == 200
    
    await db_session.refresh(reservation)
    assert reservation.status == ReservationStatus.FULFILLED.value


async def test_payment_failure_releases_inventory(client: AsyncClient, db_session: AsyncSession, setup_agreement, fake_razorpay):
    # Initiate Payment
    response = await client.post(
        "/api/v1/payments/initiate", 
        json={"agreement_id": str(setup_agreement.id)}
    )
    assert response.status_code == 200
    order_id = response.json()["razorpay_order_id"]
    
    # Simulate payment.failed webhook
    payment_id = f"pay_fake_{uuid.uuid4().hex[:8]}"
    event_id = f"evt_{uuid.uuid4().hex[:8]}"
    
    payload = {
        "entity": "event",
        "event": "payment.failed",
        "id": event_id,
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": order_id,
                    "status": "failed"
                }
            }
        }
    }
    
    webhook_response = await client.post(
        "/api/v1/webhooks/razorpay",
        content=json.dumps(payload).encode("utf-8"),
        headers={"X-Razorpay-Signature": "valid_signature"}
    )
    assert webhook_response.status_code == 200
    
    # Verify reservation is RELEASED and inventory returned
    res_query = await db_session.execute(
        select(InventoryReservation).where(InventoryReservation.agreement_id == setup_agreement.id)
    )
    reservation = res_query.scalar_one()
    assert reservation.status == ReservationStatus.RELEASED.value
    
    product = await db_session.get(Product, setup_agreement.product_id)
    assert product.inventory == 1000 # Fully returned
