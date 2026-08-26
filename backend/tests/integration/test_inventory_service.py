import uuid
import asyncio
from decimal import Decimal
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import AsyncSessionLocal
from app.models.buyer import Buyer
from app.models.merchant import Merchant
from app.models.product import Product
from app.models.agreement import Agreement, AgreementStatus
from app.models.inventory_reservation import InventoryReservation, ReservationStatus
from app.services.inventory_service import (
    reserve_inventory,
    InsufficientInventoryError,
    commit_reservation,
    release_reservation,
    fulfill_reservation,
    release_expired_reservations
)

pytestmark = pytest.mark.asyncio


async def setup_test_data(inventory_qty: int):
    async with AsyncSessionLocal() as session:
        buyer_id = uuid.uuid4()
        merchant_id = uuid.uuid4()
        product_id = uuid.uuid4()
        
        buyer = Buyer(id=buyer_id, name="Test Buyer", email=f"buyer_{buyer_id}@test.com")
        merchant = Merchant(id=merchant_id, name="Test Merchant", email=f"merchant_{merchant_id}@test.com")
        
        session.add(buyer)
        session.add(merchant)
        await session.flush()
        
        product = Product(
            id=product_id,
            merchant_id=merchant_id,
            sku=f"sku_{product_id}",
            name="Test Product",
            description="A product for testing.",
            price=Decimal("1500.00"),
            inventory=inventory_qty
        )
        session.add(product)
        await session.commit()
        
        return buyer_id, merchant_id, product_id


async def create_agreement(buyer_id, merchant_id, product_id, quantity: int) -> uuid.UUID:
    async with AsyncSessionLocal() as session:
        agreement_id = uuid.uuid4()
        # Negotiation not strictly required for FK in this context since test data might skip it if we don't enforce it,
        # but let's create a negotiation to satisfy the FK.
        from app.models.negotiation import Negotiation, NegotiationState
        neg_id = uuid.uuid4()
        neg = Negotiation(
            id=neg_id,
            buyer_id=buyer_id,
            merchant_id=merchant_id,
            product_id=product_id,
            state=NegotiationState.ACCEPTED.value
        )
        session.add(neg)
        await session.flush()
        
        agreement = Agreement(
            id=agreement_id,
            negotiation_id=neg_id,
            merchant_id=merchant_id,
            buyer_id=buyer_id,
            product_id=product_id,
            product_name="Test Product",
            quantity=quantity,
            unit_price=Decimal("1500.00"),
            total_amount=Decimal("1500.00") * quantity,
            currency="INR",
            payment_terms="upfront",
            delivery_days=7,
            warranty_months=12,
            status=AgreementStatus.VALIDATED.value
        )
        session.add(agreement)
        await session.commit()
        return agreement_id


async def test_inventory_concurrency_oversell():
    # Setup inventory = 10
    buyer_id, merchant_id, product_id = await setup_test_data(10)
    
    # Request A = 7, Request B = 6
    agr_a_id = await create_agreement(buyer_id, merchant_id, product_id, 7)
    agr_b_id = await create_agreement(buyer_id, merchant_id, product_id, 6)
    
    async def run_reservation(agr_id: uuid.UUID):
        async with AsyncSessionLocal() as session:
            try:
                res = await reserve_inventory(session, agr_id)
                await session.commit()
                return True
            except InsufficientInventoryError:
                await session.rollback()
                return False

    # Execute both concurrently
    results = await asyncio.gather(
        run_reservation(agr_a_id),
        run_reservation(agr_b_id)
    )
    
    # Exactly one should succeed
    successes = sum(results)
    assert successes == 1, "Exactly one reservation should succeed"
    
    # Verify final inventory is either 3 (10 - 7) or 4 (10 - 6)
    async with AsyncSessionLocal() as session:
        product = await session.get(Product, product_id)
        assert product.inventory in (3, 4), "Inventory must not be negative or inconsistent"


async def test_inventory_concurrency_exact_stock():
    # Setup inventory = 1
    buyer_id, merchant_id, product_id = await setup_test_data(1)
    
    # Request A = 1, Request B = 1
    agr_a_id = await create_agreement(buyer_id, merchant_id, product_id, 1)
    agr_b_id = await create_agreement(buyer_id, merchant_id, product_id, 1)
    
    async def run_reservation(agr_id: uuid.UUID):
        async with AsyncSessionLocal() as session:
            try:
                await reserve_inventory(session, agr_id)
                await session.commit()
                return True
            except InsufficientInventoryError:
                await session.rollback()
                return False

    results = await asyncio.gather(
        run_reservation(agr_a_id),
        run_reservation(agr_b_id)
    )
    
    successes = sum(results)
    assert successes == 1, "Exactly one reservation should succeed"
    
    async with AsyncSessionLocal() as session:
        product = await session.get(Product, product_id)
        assert product.inventory == 0


async def test_reservation_lifecycle_success():
    buyer_id, merchant_id, product_id = await setup_test_data(5)
    agr_id = await create_agreement(buyer_id, merchant_id, product_id, 2)
    
    async with AsyncSessionLocal() as session:
        # Reserve
        await reserve_inventory(session, agr_id)
        await session.commit()
        
        product = await session.get(Product, product_id)
        assert product.inventory == 3
        
        # Commit
        await commit_reservation(session, agr_id)
        await session.commit()
        
        res_query = await session.execute(select(InventoryReservation).where(InventoryReservation.agreement_id == agr_id))
        reservation = res_query.scalar_one()
        assert reservation.status == ReservationStatus.COMMITTED.value
        assert reservation.expires_at is None
        
        # Fulfill
        await fulfill_reservation(session, agr_id)
        await session.commit()
        await session.refresh(reservation)
        assert reservation.status == ReservationStatus.FULFILLED.value


async def test_reservation_release_on_failure():
    buyer_id, merchant_id, product_id = await setup_test_data(5)
    agr_id = await create_agreement(buyer_id, merchant_id, product_id, 2)
    
    async with AsyncSessionLocal() as session:
        # Reserve
        await reserve_inventory(session, agr_id)
        await session.commit()
        
        # Simulate payment failure
        await release_reservation(session, agr_id)
        await session.commit()
        
        product = await session.get(Product, product_id)
        assert product.inventory == 5  # Returned
        
        res_query = await session.execute(select(InventoryReservation).where(InventoryReservation.agreement_id == agr_id))
        reservation = res_query.scalar_one()
        assert reservation.status == ReservationStatus.RELEASED.value


async def test_release_expired_reservations():
    buyer_id, merchant_id, product_id = await setup_test_data(10)
    agr_id = await create_agreement(buyer_id, merchant_id, product_id, 3)
    
    async with AsyncSessionLocal() as session:
        await reserve_inventory(session, agr_id)
        await session.commit()
        
        # Manually backdate the reservation expiration
        res_query = await session.execute(select(InventoryReservation).where(InventoryReservation.agreement_id == agr_id))
        reservation = res_query.scalar_one()
        
        from app.database.base import utcnow
        from datetime import timedelta
        reservation.expires_at = utcnow() - timedelta(minutes=5)
        session.add(reservation)
        await session.commit()
        
        # Run cleanup
        count = await release_expired_reservations(session)
        assert count >= 1
        await session.commit()
        
        product = await session.get(Product, product_id)
        assert product.inventory == 10
        await session.refresh(reservation)
        assert reservation.status == ReservationStatus.EXPIRED.value
