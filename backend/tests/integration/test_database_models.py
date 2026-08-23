"""
Phase 2 Integration Tests — Database Models

These tests require a live PostgreSQL database (started via Docker).
They verify:
  - Actual ORM INSERT/SELECT operations
  - Constraint enforcement at the database level
  - Relationship traversal
  - Unique constraint violations
  - Check constraint violations (negative inventory, bad status, etc.)
  - UUID generation
  - Decimal round-trip fidelity
  - Foreign key integrity
  - Cascade/Restrict deletion behavior

To run:
    # Start database first
    docker compose up db -d
    # Run migrations
    alembic upgrade head
    # Run tests
    pytest tests/integration/test_database_models.py -v

Environment:
    DATABASE_URL must point to the test database.
    The test session creates its own isolated transaction and rolls it back.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Agreement,
    AgreementStatus,
    Buyer,
    BuyerStatus,
    Merchant,
    MerchantStatus,
    MessageType,
    Negotiation,
    NegotiationMessage,
    NegotiationState,
    Payment,
    PaymentStatus,
    Policy,
    Product,
    ProductStatus,
    SenderType,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db(app) -> AsyncSession:
    """
    Provide an async DB session for each test.
    Each test runs in its own transaction that is rolled back afterwards,
    keeping the database clean between tests.
    """
    from app.database.connection import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest_asyncio.fixture
async def merchant(db: AsyncSession) -> Merchant:
    m = Merchant(
        name="TechSupply Pro",
        email=f"merchant_{uuid.uuid4().hex[:8]}@test.nexora.ai",
        status=MerchantStatus.ACTIVE,
    )
    db.add(m)
    await db.flush()
    return m


@pytest_asyncio.fixture
async def buyer(db: AsyncSession) -> Buyer:
    b = Buyer(
        name="Horizon Corp Procurement",
        email=f"buyer_{uuid.uuid4().hex[:8]}@test.nexora.ai",
        organization="Horizon Corp",
        status=BuyerStatus.ACTIVE,
    )
    db.add(b)
    await db.flush()
    return b


@pytest_asyncio.fixture
async def policy(db: AsyncSession, merchant: Merchant) -> Policy:
    p = Policy(
        merchant_id=merchant.id,
        name="Default Policy",
        minimum_price=Decimal("10500.00"),
        maximum_discount_percent=Decimal("15.00"),
        maximum_autonomous_transaction=Decimal("2000000.00"),
        human_approval_required=False,
        is_active=True,
    )
    db.add(p)
    await db.flush()
    return p


@pytest_asyncio.fixture
async def product(db: AsyncSession, merchant: Merchant) -> Product:
    pr = Product(
        merchant_id=merchant.id,
        name='Dell 24" FHD Monitor',
        sku="DELL-24-FHD-001",
        description="Dell 24-inch Full HD IPS Display",
        price=Decimal("12000.00"),
        currency="INR",
        inventory=500,
        status=ProductStatus.ACTIVE,
    )
    db.add(pr)
    await db.flush()
    return pr


@pytest_asyncio.fixture
async def negotiation(db: AsyncSession, buyer: Buyer, merchant: Merchant, product: Product) -> Negotiation:
    n = Negotiation(
        buyer_id=buyer.id,
        merchant_id=merchant.id,
        product_id=product.id,
        state=NegotiationState.DISCOVER.value,
        round_count=0,
        max_rounds=10,
    )
    db.add(n)
    await db.flush()
    return n


@pytest_asyncio.fixture
async def agreement(db: AsyncSession, negotiation: Negotiation, product: Product, merchant: Merchant, buyer: Buyer) -> Agreement:
    a = Agreement(
        negotiation_id=negotiation.id,
        merchant_id=merchant.id,
        buyer_id=buyer.id,
        product_id=product.id,
        product_name=product.name,
        quantity=100,
        unit_price=Decimal("10819.20"),
        total_amount=Decimal("1081920.00"),
        currency="INR",
        payment_terms="upfront",
        delivery_days=5,
        warranty_months=12,
        status=AgreementStatus.PENDING_VALIDATION.value,
    )
    db.add(a)
    await db.flush()
    return a


# ══════════════════════════════════════════════════════════════════════════════
# Merchant Integration Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestMerchantIntegration:
    async def test_merchant_created_with_uuid(self, merchant: Merchant):
        assert merchant.id is not None
        assert isinstance(merchant.id, uuid.UUID)

    async def test_merchant_created_at_set(self, merchant: Merchant):
        assert merchant.created_at is not None

    async def test_merchant_default_status_active(self, merchant: Merchant):
        assert merchant.status == MerchantStatus.ACTIVE

    async def test_merchant_persisted_and_queryable(self, db: AsyncSession, merchant: Merchant):
        result = await db.execute(
            sa.select(Merchant).where(Merchant.id == merchant.id)
        )
        fetched = result.scalar_one()
        assert fetched.name == merchant.name

    async def test_merchant_invalid_status_rejected(self, db: AsyncSession, merchant: Merchant):
        """Database CHECK constraint must reject invalid status values."""
        merchant.status = "unknown_status"
        db.add(merchant)
        with pytest.raises((IntegrityError, Exception)):
            await db.flush()

    async def test_duplicate_merchant_email_rejected(self, db: AsyncSession, merchant: Merchant):
        duplicate = Merchant(
            name="Other Co",
            email=merchant.email,  # same email
            status=MerchantStatus.ACTIVE,
        )
        db.add(duplicate)
        with pytest.raises(IntegrityError):
            await db.flush()


# ══════════════════════════════════════════════════════════════════════════════
# Policy Integration Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestPolicyIntegration:
    async def test_policy_created(self, policy: Policy):
        assert policy.id is not None
        assert isinstance(policy.id, uuid.UUID)

    async def test_policy_decimal_round_trip(self, db: AsyncSession, policy: Policy):
        """Decimal values must survive a DB round-trip without float conversion."""
        result = await db.execute(
            sa.select(Policy).where(Policy.id == policy.id)
        )
        fetched = result.scalar_one()
        assert isinstance(fetched.minimum_price, Decimal)
        assert fetched.minimum_price == Decimal("10500.00")
        assert isinstance(fetched.maximum_discount_percent, Decimal)
        assert fetched.maximum_discount_percent == Decimal("15.00")

    async def test_policy_negative_minimum_price_rejected(self, db: AsyncSession, merchant: Merchant):
        bad_policy = Policy(
            merchant_id=merchant.id,
            name="Bad Policy",
            minimum_price=Decimal("-100.00"),  # must be > 0
            maximum_discount_percent=Decimal("10.00"),
            maximum_autonomous_transaction=Decimal("500000.00"),
        )
        db.add(bad_policy)
        with pytest.raises((IntegrityError, Exception)):
            await db.flush()


# ══════════════════════════════════════════════════════════════════════════════
# Product Integration Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestProductIntegration:
    async def test_product_created(self, product: Product):
        assert product.id is not None
        assert product.price == Decimal("12000.00")

    async def test_product_price_is_decimal(self, db: AsyncSession, product: Product):
        result = await db.execute(sa.select(Product).where(Product.id == product.id))
        fetched = result.scalar_one()
        assert isinstance(fetched.price, Decimal)

    async def test_duplicate_sku_same_merchant_rejected(self, db: AsyncSession, merchant: Merchant, product: Product):
        """Same SKU for the same merchant is a constraint violation."""
        duplicate = Product(
            merchant_id=merchant.id,
            name="Another Monitor",
            sku=product.sku,  # same SKU, same merchant
            price=Decimal("15000.00"),
            currency="INR",
            inventory=100,
            status=ProductStatus.ACTIVE,
        )
        db.add(duplicate)
        with pytest.raises(IntegrityError):
            await db.flush()

    async def test_same_sku_different_merchant_allowed(self, db: AsyncSession, product: Product):
        """Same SKU for a DIFFERENT merchant is allowed."""
        other_merchant = Merchant(
            name="Other Merchant",
            email=f"other_{uuid.uuid4().hex[:8]}@test.nexora.ai",
            status=MerchantStatus.ACTIVE,
        )
        db.add(other_merchant)
        await db.flush()

        other_product = Product(
            merchant_id=other_merchant.id,
            name="Same Model Monitor",
            sku=product.sku,  # same SKU, DIFFERENT merchant
            price=Decimal("11000.00"),
            currency="INR",
            inventory=50,
            status=ProductStatus.ACTIVE,
        )
        db.add(other_product)
        # Should NOT raise — different merchant
        await db.flush()
        assert other_product.id is not None

    async def test_negative_inventory_rejected(self, db: AsyncSession, merchant: Merchant):
        """CHECK constraint must prevent negative inventory."""
        bad_product = Product(
            merchant_id=merchant.id,
            name="Bad Product",
            sku="BAD-001",
            price=Decimal("5000.00"),
            currency="INR",
            inventory=-1,  # must be >= 0
            status=ProductStatus.ACTIVE,
        )
        db.add(bad_product)
        with pytest.raises((IntegrityError, Exception)):
            await db.flush()

    async def test_zero_price_rejected(self, db: AsyncSession, merchant: Merchant):
        bad_product = Product(
            merchant_id=merchant.id,
            name="Free Product",
            sku="FREE-001",
            price=Decimal("0.00"),  # must be > 0
            currency="INR",
            inventory=10,
            status=ProductStatus.ACTIVE,
        )
        db.add(bad_product)
        with pytest.raises((IntegrityError, Exception)):
            await db.flush()


# ══════════════════════════════════════════════════════════════════════════════
# Negotiation Integration Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestNegotiationIntegration:
    async def test_negotiation_created(self, negotiation: Negotiation):
        assert negotiation.id is not None
        assert negotiation.state == NegotiationState.DISCOVER.value

    async def test_negotiation_invalid_state_rejected(self, db: AsyncSession, negotiation: Negotiation):
        negotiation.state = "llm_hallucinated_state"
        db.add(negotiation)
        with pytest.raises((IntegrityError, Exception)):
            await db.flush()

    async def test_negotiation_accepts_valid_states(self, db: AsyncSession, negotiation: Negotiation):
        for state in NegotiationState:
            if isinstance(state, NegotiationState):
                negotiation.state = state.value
                db.add(negotiation)
                await db.flush()


# ══════════════════════════════════════════════════════════════════════════════
# NegotiationMessage Integration Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestNegotiationMessageIntegration:
    async def test_message_created(self, db: AsyncSession, negotiation: Negotiation):
        msg = NegotiationMessage(
            negotiation_id=negotiation.id,
            sender_type=SenderType.BUYER_AGENT.value,
            sender_id=str(uuid.uuid4()),
            message_type=MessageType.REQUEST.value,
            content="I need 100 monitors",
            payload={"quantity": 100, "unit_price": "10800.00"},
            sequence_number=1,
        )
        db.add(msg)
        await db.flush()
        assert msg.id is not None

    async def test_duplicate_sequence_rejected(self, db: AsyncSession, negotiation: Negotiation):
        msg1 = NegotiationMessage(
            negotiation_id=negotiation.id,
            sender_type=SenderType.BUYER_AGENT.value,
            sender_id=str(uuid.uuid4()),
            message_type=MessageType.REQUEST.value,
            sequence_number=1,
        )
        msg2 = NegotiationMessage(
            negotiation_id=negotiation.id,
            sender_type=SenderType.MERCHANT_AGENT.value,
            sender_id=str(uuid.uuid4()),
            message_type=MessageType.OFFER.value,
            sequence_number=1,  # SAME sequence number — must be rejected
        )
        db.add(msg1)
        db.add(msg2)
        with pytest.raises(IntegrityError):
            await db.flush()

    async def test_same_sequence_different_negotiation_allowed(self, db: AsyncSession, negotiation: Negotiation, buyer: Buyer, merchant: Merchant, product: Product):
        """Sequence 1 in negotiation A does not conflict with sequence 1 in negotiation B."""
        other_negotiation = Negotiation(
            buyer_id=buyer.id,
            merchant_id=merchant.id,
            product_id=product.id,
            state=NegotiationState.DISCOVER.value,
        )
        db.add(other_negotiation)
        await db.flush()

        msg_a = NegotiationMessage(
            negotiation_id=negotiation.id,
            sender_type=SenderType.BUYER_AGENT.value,
            sender_id=str(uuid.uuid4()),
            message_type=MessageType.REQUEST.value,
            sequence_number=1,
        )
        msg_b = NegotiationMessage(
            negotiation_id=other_negotiation.id,
            sender_type=SenderType.BUYER_AGENT.value,
            sender_id=str(uuid.uuid4()),
            message_type=MessageType.REQUEST.value,
            sequence_number=1,  # Same sequence, different negotiation = OK
        )
        db.add(msg_a)
        db.add(msg_b)
        await db.flush()
        assert msg_a.id is not None
        assert msg_b.id is not None


# ══════════════════════════════════════════════════════════════════════════════
# Agreement Integration Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestAgreementIntegration:
    async def test_agreement_created(self, agreement: Agreement):
        assert agreement.id is not None
        assert agreement.status == AgreementStatus.PENDING_VALIDATION.value

    async def test_agreement_total_is_decimal(self, db: AsyncSession, agreement: Agreement):
        result = await db.execute(sa.select(Agreement).where(Agreement.id == agreement.id))
        fetched = result.scalar_one()
        assert isinstance(fetched.total_amount, Decimal)
        assert isinstance(fetched.unit_price, Decimal)
        assert fetched.total_amount == Decimal("1081920.00")
        assert fetched.unit_price == Decimal("10819.20")

    async def test_agreement_total_integrity(self, agreement: Agreement):
        """Verify total = unit_price * quantity using Decimal."""
        calculated = (agreement.unit_price * agreement.quantity).quantize(Decimal("0.01"))
        stored = agreement.total_amount.quantize(Decimal("0.01"))
        assert calculated == stored

    async def test_agreement_negotiation_id_unique(self, db: AsyncSession, negotiation: Negotiation, product: Product, merchant: Merchant, buyer: Buyer, agreement: Agreement):
        """Cannot create two agreements for the same negotiation."""
        duplicate = Agreement(
            negotiation_id=negotiation.id,  # SAME negotiation
            merchant_id=merchant.id,
            buyer_id=buyer.id,
            product_id=product.id,
            product_name=product.name,
            quantity=50,
            unit_price=Decimal("11000.00"),
            total_amount=Decimal("550000.00"),
            currency="INR",
            payment_terms="net30",
            delivery_days=7,
            warranty_months=12,
        )
        db.add(duplicate)
        with pytest.raises(IntegrityError):
            await db.flush()

    async def test_agreement_quantity_must_be_positive(self, db: AsyncSession, negotiation: Negotiation, product: Product, merchant: Merchant, buyer: Buyer):
        """Another negotiation fixture needed to avoid UNIQUE violation from shared negotiation."""
        other_negotiation = Negotiation(
            buyer_id=buyer.id,
            merchant_id=merchant.id,
            product_id=product.id,
            state=NegotiationState.ACCEPTED.value,
        )
        db.add(other_negotiation)
        await db.flush()

        bad_agreement = Agreement(
            negotiation_id=other_negotiation.id,
            merchant_id=merchant.id,
            buyer_id=buyer.id,
            product_id=product.id,
            product_name=product.name,
            quantity=0,  # must be > 0
            unit_price=Decimal("10000.00"),
            total_amount=Decimal("0.00"),
            currency="INR",
            payment_terms="upfront",
            delivery_days=5,
            warranty_months=12,
        )
        db.add(bad_agreement)
        with pytest.raises((IntegrityError, Exception)):
            await db.flush()


# ══════════════════════════════════════════════════════════════════════════════
# Payment Integration Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestPaymentIntegration:
    async def test_payment_created(self, db: AsyncSession, agreement: Agreement):
        p = Payment(
            agreement_id=agreement.id,
            razorpay_order_id=f"order_{uuid.uuid4().hex[:16]}",
            amount=agreement.total_amount,
            amount_paise=int(agreement.total_amount * 100),
            currency="INR",
            status=PaymentStatus.CREATED.value,
        )
        db.add(p)
        await db.flush()
        assert p.id is not None

    async def test_duplicate_razorpay_order_id_rejected(self, db: AsyncSession, agreement: Agreement):
        order_id = f"order_{uuid.uuid4().hex[:16]}"
        p1 = Payment(
            agreement_id=agreement.id,
            razorpay_order_id=order_id,
            amount=agreement.total_amount,
            currency="INR",
            status=PaymentStatus.CREATED.value,
        )
        db.add(p1)
        await db.flush()

        # Create another agreement to attach second payment to
        from app.models import Negotiation as Neg
        neg2 = Neg(
            buyer_id=agreement.buyer_id,
            merchant_id=agreement.merchant_id,
            product_id=agreement.product_id,
            state=NegotiationState.ACCEPTED.value,
        )
        db.add(neg2)
        await db.flush()

        agreement2 = Agreement(
            negotiation_id=neg2.id,
            merchant_id=agreement.merchant_id,
            buyer_id=agreement.buyer_id,
            product_id=agreement.product_id,
            product_name=agreement.product_name,
            quantity=10,
            unit_price=Decimal("10000.00"),
            total_amount=Decimal("100000.00"),
            currency="INR",
            payment_terms="upfront",
            delivery_days=3,
            warranty_months=6,
        )
        db.add(agreement2)
        await db.flush()

        p2 = Payment(
            agreement_id=agreement2.id,
            razorpay_order_id=order_id,  # DUPLICATE order ID — must be rejected
            amount=Decimal("100000.00"),
            currency="INR",
            status=PaymentStatus.CREATED.value,
        )
        db.add(p2)
        with pytest.raises(IntegrityError):
            await db.flush()

    async def test_payment_amount_is_decimal(self, db: AsyncSession, agreement: Agreement):
        p = Payment(
            agreement_id=agreement.id,
            razorpay_order_id=f"order_{uuid.uuid4().hex[:16]}",
            amount=agreement.total_amount,
            currency="INR",
            status=PaymentStatus.CREATED.value,
        )
        db.add(p)
        await db.flush()

        result = await db.execute(sa.select(Payment).where(Payment.id == p.id))
        fetched = result.scalar_one()
        assert isinstance(fetched.amount, Decimal)


# ══════════════════════════════════════════════════════════════════════════════
# Relationship Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestRelationships:
    async def test_merchant_has_policy(self, db: AsyncSession, merchant: Merchant, policy: Policy):
        result = await db.execute(
            sa.select(Merchant).where(Merchant.id == merchant.id)
        )
        fetched = result.scalar_one()
        # Explicit load to avoid lazy loading in async
        policies = await db.execute(
            sa.select(Policy).where(Policy.merchant_id == fetched.id)
        )
        assert policies.scalar_one().id == policy.id

    async def test_merchant_cascade_deletes_policy(self, db: AsyncSession, merchant: Merchant, policy: Policy):
        """Deleting a merchant should cascade-delete its policies."""
        policy_id = policy.id
        await db.delete(merchant)
        await db.flush()

        result = await db.execute(
            sa.select(Policy).where(Policy.id == policy_id)
        )
        assert result.scalar_one_or_none() is None

    async def test_merchant_cascade_deletes_product(self, db: AsyncSession, merchant: Merchant, product: Product):
        """Deleting a merchant should cascade-delete its products."""
        product_id = product.id
        await db.delete(merchant)
        await db.flush()

        result = await db.execute(
            sa.select(Product).where(Product.id == product_id)
        )
        assert result.scalar_one_or_none() is None

    async def test_negotiation_messages_cascade_delete(self, db: AsyncSession, negotiation: Negotiation):
        """Deleting a negotiation cascades to its messages."""
        msg = NegotiationMessage(
            negotiation_id=negotiation.id,
            sender_type=SenderType.SYSTEM.value,
            sender_id="system",
            message_type=MessageType.SYSTEM_EVENT.value,
            sequence_number=1,
        )
        db.add(msg)
        await db.flush()
        msg_id = msg.id

        await db.delete(negotiation)
        await db.flush()

        result = await db.execute(
            sa.select(NegotiationMessage).where(NegotiationMessage.id == msg_id)
        )
        assert result.scalar_one_or_none() is None
