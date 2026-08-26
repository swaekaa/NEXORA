import uuid
import pytest
from decimal import Decimal

from app.models.agreement import AgreementStatus
from app.models.negotiation import NegotiationState
from app.schemas.negotiation import NegotiationMessagePayload
from app.services.negotiation_service import create_negotiation_with_proposal, append_negotiation_message
from app.models.negotiation_message import SenderType, MessageType
from app.services.agreement_service import (
    create_agreement_from_negotiation,
    validate_agreement,
    InvalidAgreementTransitionError
)
from app.policies.models import PolicyEvaluationContext
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
    
    return buyer_id, merchant_id, product_id

async def test_create_agreement_deterministic(db_session, setup_db_entities):
    buyer_id, merchant_id, product_id = setup_db_entities
    
    # Setup accepted negotiation
    payload = NegotiationMessagePayload(
        product_id=product_id,
        quantity=10,
        unit_price=Decimal("1500.00"),
        total_amount=Decimal("15000.00")
    )
    
    negotiation = await create_negotiation_with_proposal(
        session=db_session,
        buyer_id=buyer_id,
        merchant_id=merchant_id,
        product_id=product_id,
        payload=payload
    )
    
    await append_negotiation_message(
        session=db_session,
        negotiation_id=negotiation.id,
        sender_type=SenderType.MERCHANT_AGENT,
        sender_id=str(merchant_id),
        message_type=MessageType.ACCEPT,
        payload=payload
    )
    
    # Create agreement
    agreement = await create_agreement_from_negotiation(db_session, negotiation.id)
    
    assert agreement.quantity == 10
    assert agreement.unit_price == Decimal("1500.00")
    assert agreement.total_amount == Decimal("15000.00")
    assert agreement.status == AgreementStatus.PENDING_VALIDATION.value
    assert agreement.currency == "INR"


async def test_create_agreement_fails_on_non_accepted(db_session, setup_db_entities):
    buyer_id, merchant_id, product_id = setup_db_entities
    
    payload = NegotiationMessagePayload(
        product_id=product_id,
        quantity=10,
        unit_price=Decimal("1500.00"),
        total_amount=Decimal("15000.00")
    )
    
    negotiation = await create_negotiation_with_proposal(
        session=db_session,
        buyer_id=buyer_id,
        merchant_id=merchant_id,
        product_id=product_id,
        payload=payload
    )
    
    # State is OFFER, not ACCEPTED
    with pytest.raises(ValueError, match="must be in ACCEPTED state"):
        await create_agreement_from_negotiation(db_session, negotiation.id)


async def test_agreement_validation(db_session, setup_db_entities):
    buyer_id, merchant_id, product_id = setup_db_entities
    
    payload = NegotiationMessagePayload(
        product_id=product_id,
        quantity=10,
        unit_price=Decimal("1500.00"),
        total_amount=Decimal("15000.00")
    )
    
    negotiation = await create_negotiation_with_proposal(
        session=db_session,
        buyer_id=buyer_id,
        merchant_id=merchant_id,
        product_id=product_id,
        payload=payload
    )
    
    await append_negotiation_message(
        session=db_session,
        negotiation_id=negotiation.id,
        sender_type=SenderType.MERCHANT_AGENT,
        sender_id=str(merchant_id),
        message_type=MessageType.ACCEPT,
        payload=payload
    )
    
    agreement = await create_agreement_from_negotiation(db_session, negotiation.id)
    
    context = PolicyEvaluationContext(
        merchant_id=merchant_id,
        policy_id=uuid.uuid4(),
        minimum_price=Decimal("1000.00"),
        maximum_discount_percent=Decimal("10.0"),
        maximum_autonomous_transaction=Decimal("50000.00"),
        human_approval_required=False
    )
    
    validated = await validate_agreement(db_session, agreement.id, context)
    assert validated.status == AgreementStatus.VALIDATED.value


async def test_agreement_validation_human_approval(db_session, setup_db_entities):
    buyer_id, merchant_id, product_id = setup_db_entities
    
    payload = NegotiationMessagePayload(
        product_id=product_id,
        quantity=10,
        unit_price=Decimal("1500.00"),
        total_amount=Decimal("15000.00")
    )
    
    negotiation = await create_negotiation_with_proposal(
        session=db_session,
        buyer_id=buyer_id,
        merchant_id=merchant_id,
        product_id=product_id,
        payload=payload
    )
    
    await append_negotiation_message(
        session=db_session,
        negotiation_id=negotiation.id,
        sender_type=SenderType.MERCHANT_AGENT,
        sender_id=str(merchant_id),
        message_type=MessageType.ACCEPT,
        payload=payload
    )
    
    agreement = await create_agreement_from_negotiation(db_session, negotiation.id)
    
    # Set limit below total to trigger human approval
    context = PolicyEvaluationContext(
        merchant_id=merchant_id,
        policy_id=uuid.uuid4(),
        minimum_price=Decimal("1000.00"),
        maximum_discount_percent=Decimal("10.0"),
        maximum_autonomous_transaction=Decimal("10000.00"), # < 15000
        human_approval_required=False
    )
    
    validated = await validate_agreement(db_session, agreement.id, context)
    assert validated.status == AgreementStatus.PENDING_APPROVAL.value
