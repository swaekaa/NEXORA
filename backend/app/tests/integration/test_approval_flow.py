import os
os.environ["ENVIRONMENT"] = "test"

import pytest
import pytest_asyncio
import uuid
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.merchant import Merchant
from app.models.buyer import Buyer
from app.models.product import Product
from app.models.negotiation import Negotiation, NegotiationState
from app.models.negotiation_message import SenderType, MessageType
from app.models.agreement import Agreement, AgreementStatus
from app.models.policy import Policy
from app.policies.models import PolicyEvaluationContext
from app.services.negotiation_service import append_negotiation_message
from app.services.agreement_service import create_agreement_from_negotiation, validate_agreement
from app.services.payment_service import initiate_payment, PaymentServiceError
from app.services.approval_service import create_approval_request, approve, reject, get_pending_approvals
from app.models.approval_request import ApprovalRequest, ApprovalStatus
from app.schemas.negotiation import NegotiationMessagePayload
from app.database.connection import get_db

pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture
async def db_session():
    async for session in get_db():
        yield session
        await session.rollback()



# Mock razorpay client
class MockRazorpayClient:
    def create_order(self, amount_paise, currency, receipt, notes):
        return {"id": f"order_{uuid.uuid4().hex[:14]}"}
    def fetch_orders_by_receipt(self, receipt):
        return []

@pytest_asyncio.fixture
async def mock_rzp():
    return MockRazorpayClient()

@pytest_asyncio.fixture
async def setup_entities(db_session: AsyncSession):
    merchant_id = uuid.uuid4()
    buyer_id = uuid.uuid4()
    merchant = Merchant(id=merchant_id, name="Test Merchant", email=f"merchant_{merchant_id}@test.com")
    db_session.add(merchant)
    buyer = Buyer(id=buyer_id, name="Test Buyer", email=f"buyer_{buyer_id}@test.com")
    db_session.add(buyer)
    await db_session.flush()

    product = Product(
        merchant_id=merchant.id,
        sku=f"sku_{uuid.uuid4()}",
        name="Test Product",
        description="Test",
        price=Decimal("15000.00"),
        inventory=1000
    )
    db_session.add(product)
    
    # Policy with 500k limit
    policy = Policy(
        merchant_id=merchant.id,
        name="Test Policy",
        minimum_price=Decimal("10000.00"),
        maximum_discount_percent=Decimal("20.00"),
        maximum_autonomous_transaction=Decimal("500000.00"),
        human_approval_required=False,
        is_active=True
    )
    db_session.add(policy)
    await db_session.commit()

    return {"merchant": merchant, "buyer": buyer, "product": product, "policy": policy}

async def create_accepted_negotiation(db_session: AsyncSession, setup, quantity: int, unit_price: Decimal):
    total = (unit_price * quantity).quantize(Decimal("0.01"))
    payload = NegotiationMessagePayload(
        product_id=str(setup["product"].id),
        quantity=quantity,
        unit_price=unit_price,
        discount_percent=Decimal("0"),
        total_amount=total,
        currency="INR"
    )

    # 1. Start negotiation (automatically sets state to OFFER)
    from app.services.negotiation_service import create_negotiation_with_proposal
    neg = await create_negotiation_with_proposal(
        session=db_session,
        buyer_id=setup["buyer"].id,
        merchant_id=setup["merchant"].id,
        product_id=setup["product"].id,
        payload=payload
    )
    
    # 2. Merchant accepts it (automatically sets state to ACCEPTED)
    await append_negotiation_message(
        session=db_session,
        negotiation_id=neg.id,
        sender_type=SenderType.MERCHANT_AGENT,
        sender_id=str(setup["merchant"].id),
        message_type=MessageType.ACCEPT,
        content="Deal accepted",
        payload=payload
    )
    
    await db_session.refresh(neg)
    return neg

@pytest.mark.asyncio
async def test_a_autonomous_transaction(db_session: AsyncSession, setup_entities, mock_rzp):
    """Test A: Transaction below limit (400k)"""
    neg = await create_accepted_negotiation(db_session, setup_entities, 20, Decimal("20000.00"))
    agreement = await create_agreement_from_negotiation(db_session, neg.id)
    
    assert agreement.status == AgreementStatus.VALIDATED.value
    
    # Payment should proceed
    payment = await initiate_payment(db_session, agreement.id, mock_rzp)
    assert payment is not None

@pytest.mark.asyncio
async def test_b_human_approval_transaction(db_session: AsyncSession, setup_entities, mock_rzp):
    """Test B: Transaction above limit (1.5M) -> PENDING"""
    neg = await create_accepted_negotiation(db_session, setup_entities, 100, Decimal("15000.00"))
    agreement = await create_agreement_from_negotiation(db_session, neg.id)
    
    assert agreement.status == AgreementStatus.PENDING_APPROVAL.value
    
    # Check approval request exists
    approvals = await get_pending_approvals(db_session, setup_entities["merchant"].id)
    assert len(approvals) == 1
    
    # Payment should block
    with pytest.raises(PaymentServiceError, match="A valid approved request is missing"):
        await initiate_payment(db_session, agreement.id, mock_rzp)

@pytest.mark.asyncio
async def test_c_approval(db_session: AsyncSession, setup_entities, mock_rzp):
    """Test C: Approve request -> Payment allowed"""
    neg = await create_accepted_negotiation(db_session, setup_entities, 100, Decimal("15000.00"))
    agreement = await create_agreement_from_negotiation(db_session, neg.id)
    
    approvals = await get_pending_approvals(db_session, setup_entities["merchant"].id)
    approval_id = approvals[0].id
    
    await approve(db_session, approval_id, setup_entities["merchant"].id, setup_entities["merchant"].id)
    
    from app.services.agreement_service import manually_approve_agreement
    await manually_approve_agreement(db_session, agreement.id)
    
    payment = await initiate_payment(db_session, agreement.id, mock_rzp)
    assert payment is not None

@pytest.mark.asyncio
async def test_d_rejection(db_session: AsyncSession, setup_entities, mock_rzp):
    """Test D: Reject request -> Payment blocked"""
    neg = await create_accepted_negotiation(db_session, setup_entities, 100, Decimal("15000.00"))
    agreement = await create_agreement_from_negotiation(db_session, neg.id)
    
    approvals = await get_pending_approvals(db_session, setup_entities["merchant"].id)
    await reject(db_session, approvals[0].id, setup_entities["merchant"].id, setup_entities["merchant"].id, "No")
    
    with pytest.raises(PaymentServiceError, match="A valid approved request is missing"):
        await initiate_payment(db_session, agreement.id, mock_rzp)

@pytest.mark.asyncio
async def test_e_missing_approval(db_session: AsyncSession, setup_entities, mock_rzp):
    """Test E: Missing approval -> Payment blocked"""
    neg = await create_accepted_negotiation(db_session, setup_entities, 100, Decimal("15000.00"))
    agreement = await create_agreement_from_negotiation(db_session, neg.id)
    
    # Delete the approval request using the service or ORM securely within the session
    from sqlalchemy import delete
    await db_session.execute(delete(ApprovalRequest).where(ApprovalRequest.agreement_id == agreement.id))
    await db_session.commit()
    
    with pytest.raises(PaymentServiceError, match="A valid approved request is missing"):
        await initiate_payment(db_session, agreement.id, mock_rzp)

@pytest.mark.asyncio
async def test_g_duplicate_validation(db_session: AsyncSession, setup_entities):
    """Test G: Duplicate validation yields ONE ApprovalRequest"""
    neg = await create_accepted_negotiation(db_session, setup_entities, 100, Decimal("15000.00"))
    agreement = await create_agreement_from_negotiation(db_session, neg.id)
    
    from app.policies.models import PolicyEvaluationContext
    ctx = PolicyEvaluationContext(
        merchant_id=setup_entities["merchant"].id,
        policy_id=setup_entities["policy"].id,
        minimum_price=setup_entities["policy"].minimum_price,
        maximum_discount_percent=setup_entities["policy"].maximum_discount_percent,
        maximum_autonomous_transaction=setup_entities["policy"].maximum_autonomous_transaction,
        human_approval_required=setup_entities["policy"].human_approval_required
    )
    
    # Try validating again (simulate retry)
    # Note: it will raise InvalidAgreementTransitionError because it's no longer PENDING_VALIDATION.
    # So we force it back to PENDING_VALIDATION for the test
    agreement.status = AgreementStatus.PENDING_VALIDATION.value
    await db_session.commit()
    await validate_agreement(db_session, agreement.id, ctx)
    
    # Count requests
    res = await db_session.execute(select(ApprovalRequest).where(ApprovalRequest.agreement_id == agreement.id))
    requests = res.scalars().all()
    assert len(requests) == 1

@pytest.mark.asyncio
async def test_h_policy_mutation_after_approval(db_session: AsyncSession, setup_entities, mock_rzp):
    """Test H: Policy mutation after approval -> Payment BLOCKED (CRITICAL SECURITY)"""
    neg = await create_accepted_negotiation(db_session, setup_entities, 100, Decimal("15000.00"))
    agreement = await create_agreement_from_negotiation(db_session, neg.id)
    
    approvals = await get_pending_approvals(db_session, setup_entities["merchant"].id)
    await approve(db_session, approvals[0].id, setup_entities["merchant"].id, setup_entities["merchant"].id)
    
    from app.services.agreement_service import manually_approve_agreement
    await manually_approve_agreement(db_session, agreement.id)
    
    # Merchant mutations policy!
    setup_entities["policy"].minimum_price = Decimal("20000.00") # Higher than 15000
    await db_session.commit()
    
    # Even though it's approved, final deterministic check should fail!
    with pytest.raises(PaymentServiceError, match="Policy DENY: Payment blocked by final deterministic policy check"):
        await initiate_payment(db_session, agreement.id, mock_rzp)
