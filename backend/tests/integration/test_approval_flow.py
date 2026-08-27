import uuid
import pytest
from decimal import Decimal

from app.services import agreement_service, approval_service, payment_service, policy_service
from app.policies.models import PolicyEvaluationContext
from app.models.approval_request import ApprovalStatus
from app.models.agreement import AgreementStatus
from app.schemas.policy import PolicyCreate

from app.models.merchant import Merchant
from app.models.buyer import Buyer
from app.models.product import Product
from app.models.negotiation import Negotiation
from app.models.negotiation_message import NegotiationMessage
from app.database.connection import get_db

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def db_session():
    async for session in get_db():
        yield session
        await session.rollback()


@pytest.fixture
async def setup_test_negotiation(db_session):
    merchant_id = uuid.uuid4()
    buyer_id = uuid.uuid4()
    product_id = uuid.uuid4()
    negotiation_id = uuid.uuid4()

    merchant = Merchant(id=merchant_id, name="M", email=f"m_{merchant_id}@test.com", status="active")
    buyer = Buyer(id=buyer_id, name="B", email=f"b_{buyer_id}@test.com", status="active")
    product = Product(
        id=product_id, merchant_id=merchant_id, sku=f"SKU-{product_id}",
        name="P", description="D", price=Decimal("100"), inventory=100, status="active"
    )
    negotiation = Negotiation(
        id=negotiation_id, merchant_id=merchant_id, buyer_id=buyer_id,
        product_id=product_id, state="accepted", round_count=1
    )
    msg = NegotiationMessage(
        id=uuid.uuid4(),
        negotiation_id=negotiation_id,
        sender_type="buyer_agent",
        sender_id=str(buyer_id),
        message_type="offer",
        sequence_number=1,
        payload={
            "quantity": 10,
            "unit_price": 100.0,
            "total_amount": 1000.0,
            "currency": "INR",
            "payment_terms": "upfront",
            "delivery_days": 7,
            "warranty_months": 12
        }
    )

    db_session.add_all([merchant, buyer, product, negotiation, msg])
    await db_session.commit()

    return merchant, buyer, product, negotiation


@pytest.fixture
def fake_razorpay():
    class FakeRZP:
        def create_order(self, *args, **kwargs):
            return {"id": f"order_{uuid.uuid4()}"}
        def fetch_orders_by_receipt(self, receipt):
            return []
    return FakeRZP()


async def _create_strict_policy(db_session, merchant_id: uuid.UUID, policy_name: str) -> uuid.UUID:
    """Helper: create a policy with very low autonomous limit to force HUMAN_APPROVAL_REQUIRED."""
    policy = await policy_service.create_policy(
        db_session, merchant_id, PolicyCreate(
            name=policy_name,
            minimum_price=Decimal("10.0"),
            maximum_discount_percent=Decimal("5.0"),
            maximum_autonomous_transaction=Decimal("1.0"),  # 1 INR limit -> 1000 INR order needs approval
            human_approval_required=False,
            is_active=True,
            max_negotiation_rounds=10,
            max_delivery_days=30,
            min_warranty_months=0
        )
    )
    return policy.id


async def _build_context(merchant_id: uuid.UUID, policy_id: uuid.UUID) -> PolicyEvaluationContext:
    return PolicyEvaluationContext(
        merchant_id=merchant_id,
        policy_id=policy_id,
        minimum_price=Decimal("10.0"),
        maximum_discount_percent=Decimal("5.0"),
        maximum_autonomous_transaction=Decimal("1.0"),
        human_approval_required=False
    )


async def test_human_approval_success_flow(db_session, setup_test_negotiation, fake_razorpay):
    """
    Full happy path:
    1. Policy requires human approval for large transactions.
    2. Agreement is created and validated → PENDING_APPROVAL.
    3. Payment is blocked while approval is pending.
    4. Human approves.
    5. Payment succeeds after approval.
    """
    merchant, buyer, product, negotiation = setup_test_negotiation

    policy_id = await _create_strict_policy(db_session, merchant.id, "Strict Policy")

    # 1. Create Agreement from negotiation message
    agreement = await agreement_service.create_agreement_from_negotiation(db_session, negotiation.id)

    # 2. Validate against policy → should become PENDING_APPROVAL (1000 INR > 1 INR limit)
    context = await _build_context(merchant.id, policy_id)
    agreement = await agreement_service.validate_agreement(db_session, agreement.id, context)
    assert agreement.status == AgreementStatus.PENDING_APPROVAL.value

    # 3. Approval request should exist
    approvals = await approval_service.get_pending_approvals(db_session, merchant.id)
    assert len(approvals) == 1
    approval = approvals[0]

    # 4. Payment blocked while pending
    with pytest.raises(payment_service.PaymentServiceError, match="HUMAN_APPROVAL_REQUIRED"):
        await payment_service.initiate_payment(db_session, agreement.id, fake_razorpay)

    # 5. Human approves
    await approval_service.approve(db_session, approval.id, merchant.id, merchant.id)

    # Mark agreement APPROVED
    agreement.status = AgreementStatus.APPROVED.value
    db_session.add(agreement)
    await db_session.commit()

    # 6. Payment should now succeed
    payment = await payment_service.initiate_payment(db_session, agreement.id, fake_razorpay)
    assert payment is not None


async def test_policy_change_blocks_approved_agreement(db_session, setup_test_negotiation, fake_razorpay):
    """
    CRITICAL FAILURE TEST: "LLMs PROPOSE. DETERMINISTIC SYSTEMS DECIDE."
    If a merchant policy changes to DENY after human approval, payment must still be blocked.
    Human approval cannot override a DENY policy decision at payment time.
    """
    merchant, buyer, product, negotiation = setup_test_negotiation

    # 1. Policy initially requires approval (but allows the price)
    policy_id = await _create_strict_policy(db_session, merchant.id, "Initial Policy")

    agreement = await agreement_service.create_agreement_from_negotiation(db_session, negotiation.id)

    context = await _build_context(merchant.id, policy_id)
    agreement = await agreement_service.validate_agreement(db_session, agreement.id, context)
    assert agreement.status == AgreementStatus.PENDING_APPROVAL.value

    # 2. Human approves
    approvals = await approval_service.get_pending_approvals(db_session, merchant.id)
    approval = approvals[0]
    await approval_service.approve(db_session, approval.id, merchant.id, merchant.id)
    agreement.status = AgreementStatus.APPROVED.value
    db_session.add(agreement)
    await db_session.commit()

    # 3. Merchant raises minimum price above the agreed unit price (minimum 500 > unit_price 100)
    await policy_service.create_policy(
        db_session, merchant.id, PolicyCreate(
            name="New Strict",
            minimum_price=Decimal("500.0"),
            maximum_discount_percent=Decimal("5.0"),
            maximum_autonomous_transaction=Decimal("1.0"),
            human_approval_required=False,
            is_active=True,
            max_negotiation_rounds=10,
            max_delivery_days=30,
            min_warranty_months=0
        )
    )

    # 4. Payment must be blocked — DENY overrides prior human approval
    with pytest.raises(payment_service.PaymentServiceError, match="Policy DENY"):
        await payment_service.initiate_payment(db_session, agreement.id, fake_razorpay)
