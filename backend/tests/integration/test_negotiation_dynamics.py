import pytest
import uuid
from decimal import Decimal
from typing import cast
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.negotiation import Negotiation, NegotiationState
from app.models.negotiation_message import NegotiationMessage, MessageType, SenderType
from app.schemas.negotiation import NegotiationMessagePayload
from app.agents.buyer.schemas import BuyerIntent, BuyerAgentState, ActionType, BuyerAgentAction
from app.agents.merchant.schemas import MerchantIntent, MerchantAgentState, MerchantActionType, MerchantAgentAction
from app.agents.buyer.runner import run_buyer_agent
from app.agents.merchant.runner import run_merchant_agent
from app.database.connection import get_db
from app.models.buyer import Buyer
from app.models.merchant import Merchant
from app.models.product import Product
from app.models.policy import Policy
import pytest_asyncio

# Use existing pytest fixtures for db session
pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture
async def db_session():
    # Setup real DB session for integration test
    async for session in get_db():
        yield session
        await session.rollback()

@pytest_asyncio.fixture
async def setup_db_entities(db_session: AsyncSession):
    buyer_id = uuid.uuid4()
    merchant_id = uuid.uuid4()
    product_id = uuid.uuid4()
    policy_id = uuid.uuid4()
    
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
        price=Decimal("15000.00"),
        inventory=1000
    )
    
    policy = Policy(
        id=policy_id,
        merchant_id=merchant_id,
        is_active=True,
        minimum_price=Decimal("10000"),
        maximum_discount_percent=Decimal("20.00"),
        maximum_autonomous_transaction=Decimal("500000"),
        human_approval_required=False
    )
    
    db_session.add(product)
    db_session.add(policy)
    await db_session.commit()
    
    return {
        "buyer_id": buyer_id,
        "merchant_id": merchant_id,
        "product_id": product_id,
        "policy_id": policy_id,
        "product_price": product.price
    }


async def test_negotiation_deadlock_recovery(db_session: AsyncSession, setup_db_entities):
    """
    Simulates the exact loop the user experienced:
    Buyer: 11000
    Merchant: 14000
    Buyer: 13000
    Merchant: 13500
    Buyer: 12500
    Merchant: 13200
    
    Verifies that the deadlock detector intervenes and prevents an infinite loop,
    eventually resulting in a terminal state.
    """
    
    from app.services.negotiation_service import create_negotiation_with_proposal, append_negotiation_message
    
    buyer_id = setup_db_entities["buyer_id"]
    merchant_id = setup_db_entities["merchant_id"]
    product_id = setup_db_entities["product_id"]
    
    payload_buyer_1 = NegotiationMessagePayload(
        product_id=product_id,
        quantity=10,
        unit_price=Decimal("11000"),
        discount_percent=Decimal("0"),
        total_amount=Decimal("110000"),
        currency="INR"
    )
    
    negotiation = await create_negotiation_with_proposal(
        session=db_session,
        buyer_id=buyer_id,
        merchant_id=merchant_id,
        product_id=product_id,
        payload=payload_buyer_1,
        content="I propose 11000."
    )
    
    payload_merchant_1 = NegotiationMessagePayload(
        product_id=product_id,
        quantity=10,
        unit_price=Decimal("14000"),
        discount_percent=Decimal("0"),
        total_amount=Decimal("140000"),
        currency="INR"
    )
    await append_negotiation_message(db_session, negotiation.id, SenderType.MERCHANT_AGENT, str(merchant_id), MessageType.COUNTER_OFFER, "I counter with 14000.", payload_merchant_1)
    
    payload_buyer_2 = NegotiationMessagePayload(
        product_id=product_id,
        quantity=10,
        unit_price=Decimal("13000"),
        discount_percent=Decimal("0"),
        total_amount=Decimal("130000"),
        currency="INR"
    )
    await append_negotiation_message(db_session, negotiation.id, SenderType.BUYER_AGENT, str(buyer_id), MessageType.COUNTER_OFFER, "I counter with 13000.", payload_buyer_2)
    
    payload_merchant_2 = NegotiationMessagePayload(
        product_id=product_id,
        quantity=10,
        unit_price=Decimal("13500"),
        discount_percent=Decimal("0"),
        total_amount=Decimal("135000"),
        currency="INR"
    )
    await append_negotiation_message(db_session, negotiation.id, SenderType.MERCHANT_AGENT, str(merchant_id), MessageType.COUNTER_OFFER, "I counter with 13500.", payload_merchant_2)
    
    payload_buyer_3 = NegotiationMessagePayload(
        product_id=product_id,
        quantity=10,
        unit_price=Decimal("12500"),
        discount_percent=Decimal("0"),
        total_amount=Decimal("125000"),
        currency="INR"
    )
    await append_negotiation_message(db_session, negotiation.id, SenderType.BUYER_AGENT, str(buyer_id), MessageType.COUNTER_OFFER, "I counter with 12500.", payload_buyer_3)
    
    payload_merchant_3 = NegotiationMessagePayload(
        product_id=product_id,
        quantity=10,
        unit_price=Decimal("13200"),
        discount_percent=Decimal("0"),
        total_amount=Decimal("132000"),
        currency="INR"
    )
    await append_negotiation_message(db_session, negotiation.id, SenderType.MERCHANT_AGENT, str(merchant_id), MessageType.COUNTER_OFFER, "I counter with 13200.", payload_merchant_3)
    
    # Run the agents in a loop. They should not get trapped in an infinite loop.
    intent = BuyerIntent(
        buyer_id=buyer_id,
        merchant_id=merchant_id,
        negotiation_id=negotiation.id,
        product_query="Monitor",
        quantity=10,
        maximum_budget=Decimal("450000"),
        target_unit_price=Decimal("12000"),
        reservation_unit_price=Decimal("13000")
    )
    
    max_loops = 10
    loop_count = 0
    terminal_reached = False
    
    while loop_count < max_loops:
        loop_count += 1
        
        # Buyer Turn
        await run_buyer_agent(db_session, intent)
        
        await db_session.refresh(negotiation)
        if negotiation.state in NegotiationState.TERMINAL_STATES:
            terminal_reached = True
            break
            
        # Merchant Turn
        await run_merchant_agent(db_session, negotiation.id)
        
        await db_session.refresh(negotiation)
        if negotiation.state in NegotiationState.TERMINAL_STATES:
            terminal_reached = True
            break
            
    assert terminal_reached, "The negotiation entered an infinite loop and failed to reach a terminal state."
