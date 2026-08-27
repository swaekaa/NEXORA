"""
Integration tests for the Multi-Agent Negotiation Protocol (Phase 11).
Tests the interaction between Buyer Agent and Merchant Agent.
"""
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.buyer.schemas import BuyerIntent
from app.agents.buyer.runner import run_buyer_agent
from app.agents.merchant.runner import run_merchant_agent
from app.agents.merchant.schemas import MerchantAgentAction, MerchantActionType
from app.models.negotiation import NegotiationState
from app.models.buyer import Buyer
from app.models.merchant import Merchant
from app.models.product import Product
from app.database.connection import get_db

@pytest.fixture
async def db_session():
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
    
    from app.models.policy import Policy
    
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
    
    policy = Policy(
        id=uuid.uuid4(),
        merchant_id=merchant_id,
        name="Test Policy",
        minimum_price=Decimal("800.00"),
        maximum_discount_percent=Decimal("15.0"),
        maximum_autonomous_transaction=Decimal("200000.00"),
        human_approval_required=False,
        is_active=True
    )
    db_session.add(policy)
    
    await db_session.flush()
    
    return {"buyer": buyer, "merchant": merchant, "product": product}
@pytest.mark.asyncio
@patch("app.agents.buyer.nodes.get_llm")
@patch("app.agents.merchant.nodes.get_llm")
async def test_full_multi_agent_negotiation_loop(
    mock_merchant_llm_getter,
    mock_buyer_llm_getter,
    db_session: AsyncSession,
    setup_db_entities: dict
):
    """
    Simulates a full end-to-end negotiation protocol.
    Buyer Proposes -> Merchant Counters -> Buyer Accepts -> Agreement Created.
    """
    buyer_id = setup_db_entities["buyer"].id
    merchant_id = setup_db_entities["merchant"].id
    
    # --- 1. BUYER AGENT RUN ---
    buyer_intent = BuyerIntent(
        buyer_id=buyer_id,
        merchant_id=merchant_id,
        product_query="Buy 100 widgets for a maximum of 1000 INR each.",
        maximum_budget=Decimal("100000.00"),
        quantity=100,
        preferred_currency="INR"
    )
    
    # Mock Buyer LLM (must be AsyncMock so `await llm.ainvoke(...)` works)
    from app.agents.buyer.schemas import BuyerAgentAction, ActionType
    mock_buyer_llm = MagicMock()
    mock_buyer_llm.ainvoke = AsyncMock(return_value=BuyerAgentAction(
        action=ActionType.PROPOSE_AGREEMENT,
        product_id=str(setup_db_entities["product"].id),
        proposed_unit_price="900.00",
        reason="I'd like to offer 900 each for 100 units."
    ))
    mock_buyer_llm_getter.return_value.with_structured_output.return_value = mock_buyer_llm
    
    buyer_state = await run_buyer_agent(db_session, buyer_intent)
    assert buyer_state["status"] == "completed", f"Buyer Agent failed: {buyer_state.get('error_reason')}"
    
    negotiation_id = buyer_state["negotiation_id"]
    assert negotiation_id is not None
    
    # Verify DB State
    from app.services.negotiation_service import get_negotiation, get_negotiation_messages
    neg = await get_negotiation(db_session, negotiation_id)
    assert neg.state == NegotiationState.OFFER.value
    
    messages = await get_negotiation_messages(db_session, negotiation_id)
    assert len(messages) == 1
    from app.models.negotiation_message import SenderType
    assert messages[0].sender_type == SenderType.BUYER_AGENT.value
    
    
    # --- 2. MERCHANT AGENT RUN ---
    mock_merchant_llm = MagicMock()
    mock_merchant_llm_getter.return_value.with_structured_output.return_value = mock_merchant_llm
    
    # Setup Merchant Action (Counter Offer)
    mock_merchant_llm.invoke.return_value = MerchantAgentAction(
        action=MerchantActionType.COUNTER_PROPOSAL,
        proposed_quantity=100,
        proposed_unit_price="950.00",
        reason="My minimum is 950."
    )
    
    merchant_state = await run_merchant_agent(db_session, negotiation_id)
    assert merchant_state["status"] == "completed"
    assert merchant_state["policy_decision"] == "allow"
    
    # Verify DB State
    db_session.expire_all()
    neg = await get_negotiation(db_session, negotiation_id)
    assert neg.state == NegotiationState.COUNTER_OFFER.value
    
    messages = await get_negotiation_messages(db_session, negotiation_id)
    assert len(messages) == 2
    assert messages[-1].sender_type == SenderType.MERCHANT_AGENT.value
    
    
    # --- 3. BUYER AGENT RUN (Accept Counter) ---
    # Buyer evaluates counter offer and accepts
    mock_buyer_llm.ainvoke = AsyncMock(return_value=BuyerAgentAction(
        action=ActionType.ACCEPT_COUNTER,
        reason="I accept the counter offer."
    ))
    
    buyer_intent.negotiation_id = negotiation_id
    buyer_state_2 = await run_buyer_agent(db_session, buyer_intent)
    assert buyer_state_2["status"] == "completed", f"Buyer Agent failed: {buyer_state_2.get('error_reason')}"
    
    # Verify DB State
    db_session.expire_all()
    neg = await get_negotiation(db_session, negotiation_id)
    assert neg.state == NegotiationState.ACCEPTED.value
    
    # Verify Agreement is created
    from sqlalchemy import select
    from app.models.agreement import Agreement
    result = await db_session.execute(select(Agreement).where(Agreement.negotiation_id == negotiation_id))
    agreement = result.scalar_one_or_none()
    assert agreement is not None
    assert agreement.unit_price == Decimal("950.00")
    assert agreement.quantity == 100
    assert agreement.total_amount == Decimal("95000.00")
