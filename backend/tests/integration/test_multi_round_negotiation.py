"""
Integration tests for Multi-Round Negotiation

Tests the deterministic bounds, counter-offer mechanisms, and agentic negotiation
where agents make genuine decisions without scripted round count enforcement.

Previously tested NEGOTIATION_DEMO_MIN_ROUNDS enforcement (now removed as it was
demo scripting, not agentic behavior). Tests now verify genuine agent freedom.
"""

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.buyer.schemas import BuyerIntent
from app.agents.buyer.runner import run_buyer_agent
from app.agents.merchant.runner import run_merchant_agent
from app.agents.merchant.schemas import MerchantAgentAction, MerchantActionType
from app.models.negotiation import NegotiationState, Negotiation
from app.models.negotiation_message import SenderType, MessageType
from app.models.buyer import Buyer
from app.models.merchant import Merchant
from app.models.product import Product
from app.database.connection import get_db
from app.config import settings

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
        price=Decimal("15000.00"),
        inventory=1000
    )
    db_session.add(product)
    
    policy = Policy(
        id=uuid.uuid4(),
        merchant_id=merchant_id,
        name="Test Policy",
        minimum_price=Decimal("10000.00"),
        maximum_discount_percent=Decimal("10.0"),
        maximum_autonomous_transaction=Decimal("2000000.00"),
        human_approval_required=False,
        is_active=True
    )
    db_session.add(policy)
    
    await db_session.flush()
    
    return {"buyer": buyer, "merchant": merchant, "product": product}


@pytest.mark.asyncio
@patch("app.agents.buyer.nodes.get_llm")
@patch("app.agents.merchant.nodes.get_llm")
async def test_early_acceptance_interception(
    mock_merchant_llm_getter,
    mock_buyer_llm_getter,
    db_session: AsyncSession,
    setup_db_entities: dict
):
    """
    Test 2: Merchant deterministic recovery if it accidentally accepts a lowball offer
    Test if the NEGOTIATION_DEMO_MIN_ROUNDS intercepts an early accept.
    """
    settings.NEGOTIATION_DEMO_MIN_ROUNDS = 3
    
    buyer_id = setup_db_entities["buyer"].id
    merchant_id = setup_db_entities["merchant"].id
    product = setup_db_entities["product"]
    
    # 1. Buyer offers 11,000 (Above merchant min of 10,000)
    buyer_intent = BuyerIntent(
        buyer_id=buyer_id,
        merchant_id=merchant_id,
        product_query="Buy 100",
        maximum_budget=Decimal("1500000.00"),
        quantity=100,
        preferred_currency="INR"
    )
    
    from app.agents.buyer.schemas import BuyerAgentAction, ActionType
    mock_buyer_llm = MagicMock()
    mock_buyer_llm.ainvoke = AsyncMock(return_value=BuyerAgentAction(
        action=ActionType.PROPOSE_AGREEMENT,
        product_id=str(product.id),
        proposed_unit_price="11000.00",
        reason="Offer 1"
    ))
    mock_buyer_llm_getter.return_value.with_structured_output.return_value = mock_buyer_llm
    
    buyer_state = await run_buyer_agent(db_session, buyer_intent)
    negotiation_id = buyer_state["negotiation_id"]
    
    # 2. Merchant mistakenly tries to ACCEPT_PROPOSAL on Round 1
    mock_merchant_llm = MagicMock()
    mock_merchant_llm.ainvoke = AsyncMock(return_value=MerchantAgentAction(
        action=MerchantActionType.ACCEPT_PROPOSAL,
        reason="Looks good, accepting early."
    ))
    mock_merchant_llm_getter.return_value.with_structured_output.return_value = mock_merchant_llm
    
    # Run merchant
    merchant_state = await run_merchant_agent(db_session, negotiation_id)
    
    # Assert it was intercepted and failed (or recovered)
    # The policy check will DENY, and counter_offer_recovery_node will increment revisions
    # If we run out of revisions, it fails.
    # The important part is that it did NOT result in an ACCEPTED DB state.
    from app.services.negotiation_service import get_negotiation
    db_session.expire_all()
    neg = await get_negotiation(db_session, negotiation_id)
    
    assert neg.state != NegotiationState.ACCEPTED.value
    
    # The merchant agent likely failed after 3 tries of trying to accept, returning failed status
    assert merchant_state["status"] == "failed"
    assert "Demo Strategy Active" in str(merchant_state)


@pytest.mark.asyncio
@patch("app.agents.buyer.nodes.get_llm")
@patch("app.agents.merchant.nodes.get_llm")
async def test_full_multi_round_flow(
    mock_merchant_llm_getter,
    mock_buyer_llm_getter,
    db_session: AsyncSession,
    setup_db_entities: dict
):
    """
    Test 1: Counteroffer flow (alternating messages, round count > 1)
    Test 3: Final acceptance to Agreement
    """
    settings.NEGOTIATION_DEMO_MIN_ROUNDS = 2
    
    buyer_id = setup_db_entities["buyer"].id
    merchant_id = setup_db_entities["merchant"].id
    product = setup_db_entities["product"]
    
    buyer_intent = BuyerIntent(
        buyer_id=buyer_id,
        merchant_id=merchant_id,
        product_query="Buy 100",
        maximum_budget=Decimal("1500000.00"),
        quantity=100,
        preferred_currency="INR"
    )
    
    from app.agents.buyer.schemas import BuyerAgentAction, ActionType
    mock_buyer_llm = MagicMock()
    mock_buyer_llm_getter.return_value.with_structured_output.return_value = mock_buyer_llm
    
    mock_merchant_llm = MagicMock()
    mock_merchant_llm_getter.return_value.with_structured_output.return_value = mock_merchant_llm
    
    # --- ROUND 1 ---
    
    # Message 1: Buyer Proposes 11,000
    mock_buyer_llm.ainvoke = AsyncMock(return_value=BuyerAgentAction(
        action=ActionType.PROPOSE_AGREEMENT,
        product_id=str(product.id),
        proposed_unit_price="11000.00",
        reason="Offer 1"
    ))
    buyer_state = await run_buyer_agent(db_session, buyer_intent)
    negotiation_id = buyer_state["negotiation_id"]
    
    # Message 2: Merchant Counters 14,000
    mock_merchant_llm.ainvoke = AsyncMock(return_value=MerchantAgentAction(
        action=MerchantActionType.COUNTER_PROPOSAL,
        proposed_unit_price="14000.00",
        proposed_quantity=100,
        reason="Counter 1"
    ))
    await run_merchant_agent(db_session, negotiation_id)
    
    # --- ROUND 2 ---
    
    buyer_intent.negotiation_id = negotiation_id
    
    # Message 3: Buyer Counters 12,000
    mock_buyer_llm.ainvoke = AsyncMock(return_value=BuyerAgentAction(
        action=ActionType.COUNTER_PROPOSAL,
        product_id=str(product.id),
        proposed_unit_price="12000.00",
        reason="Counter 2"
    ))
    await run_buyer_agent(db_session, buyer_intent)
    
    # Message 4: Merchant Counters 13,000
    mock_merchant_llm.ainvoke = AsyncMock(return_value=MerchantAgentAction(
        action=MerchantActionType.COUNTER_PROPOSAL,
        proposed_unit_price="13000.00",
        proposed_quantity=100,
        reason="Counter 3"
    ))
    await run_merchant_agent(db_session, negotiation_id)
    
    # --- ROUND 3 ---
    
    # Message 5: Buyer Counters 12,500
    mock_buyer_llm.ainvoke = AsyncMock(return_value=BuyerAgentAction(
        action=ActionType.COUNTER_PROPOSAL,
        product_id=str(product.id),
        proposed_unit_price="12500.00",
        reason="Counter 4"
    ))
    await run_buyer_agent(db_session, buyer_intent)
    
    # Message 6: Merchant Accepts
    mock_merchant_llm.ainvoke = AsyncMock(return_value=MerchantAgentAction(
        action=MerchantActionType.ACCEPT_PROPOSAL,
        reason="I accept 12500."
    ))
    await run_merchant_agent(db_session, negotiation_id)
    
    # --- VERIFY ---
    
    from app.services.negotiation_service import get_negotiation, get_negotiation_messages
    db_session.expire_all()
    neg = await get_negotiation(db_session, negotiation_id)
    
    assert neg.state == NegotiationState.ACCEPTED.value
    assert neg.round_count >= 3
    
    messages = await get_negotiation_messages(db_session, negotiation_id)
    assert len(messages) >= 6
    
    # Verify strict alternating sender sequence
    expected_senders = [
        SenderType.BUYER_AGENT.value,
        SenderType.MERCHANT_AGENT.value,
        SenderType.BUYER_AGENT.value,
        SenderType.MERCHANT_AGENT.value,
        SenderType.BUYER_AGENT.value,
        SenderType.MERCHANT_AGENT.value
    ]
    for i in range(6):
        assert messages[i].sender_type == expected_senders[i]
        
    # Verify no duplicate sequence numbers or message IDs
    msg_ids = set()
    seq_nums = set()
    for m in messages:
        assert m.id not in msg_ids
        assert m.sequence_number not in seq_nums
        msg_ids.add(m.id)
        seq_nums.add(m.sequence_number)
    
    from app.models.agreement import Agreement
    result = await db_session.execute(select(Agreement).where(Agreement.negotiation_id == negotiation_id))
    agreement = result.scalar_one_or_none()
    
    assert agreement is not None
    assert agreement.unit_price == Decimal("12500.00")

def test_sender_type_enum_values():
    """
    Test 15: Regression test for the string enum bug.
    Verifies that the stored DB values exactly match the string literals
    we expect in the orchestrator, and that the orchestrator does not use uppercase.
    """
    assert SenderType.BUYER_AGENT.value == "buyer_agent"
    assert SenderType.MERCHANT_AGENT.value == "merchant_agent"
    
    # Prove that comparing to uppercase literal would fail
    assert SenderType.BUYER_AGENT.value != "BUYER_AGENT"
    assert SenderType.MERCHANT_AGENT.value != "MERCHANT_AGENT"

@pytest.mark.asyncio
@patch("app.services.orchestrator.run_buyer_agent")
@patch("app.services.orchestrator.run_merchant_agent")
@patch("app.services.orchestrator.get_negotiation")
@patch("app.services.negotiation_service.get_negotiation_messages")
async def test_orchestrator_continues_on_same_state(
    mock_get_messages,
    mock_get_neg,
    mock_merchant,
    mock_buyer,
):
    """
    Test 14: Regression test for the original bug (state mutation as progress).
    If the state remains COUNTER_OFFER, but a new message is persisted,
    the orchestrator MUST NOT break loop due to "stalled".
    """
    from app.services.orchestrator import run_negotiation_loop
    from app.models.negotiation import Negotiation
    from app.models.negotiation_message import NegotiationMessage
    
    neg_id = uuid.uuid4()
    
    # Mock negotiation state
    mock_neg = MagicMock(spec=Negotiation)
    mock_neg.state = NegotiationState.COUNTER_OFFER.value
    mock_neg.round_count = 1
    
    # Mock message sequence 1: Initial state before agent runs
    msg1 = MagicMock(spec=NegotiationMessage)
    msg1.id = uuid.uuid4()
    msg1.sender_type = SenderType.MERCHANT_AGENT.value
    
    # Mock message sequence 2: State after agent runs (Buyer adds a message)
    msg2 = MagicMock(spec=NegotiationMessage)
    msg2.id = uuid.uuid4()
    msg2.sender_type = SenderType.BUYER_AGENT.value
    
    # We will simulate exactly one loop iteration before simulating a terminal state
    # First call: turn 0 start
    # Second call: turn 0 after agent
    # Third call: turn 1 start (will be terminal to stop loop)
    mock_get_messages.side_effect = [
        [msg1],          # Before Buyer runs
        [msg1, msg2],    # After Buyer runs
        [msg1, msg2]     # Start of next turn
    ]
    
    mock_neg_terminal = MagicMock(spec=Negotiation)
    mock_neg_terminal.state = NegotiationState.ACCEPTED.value
    mock_neg_terminal.round_count = 1
    
    mock_get_neg.side_effect = [
        mock_neg,          # turn 0 start
        mock_neg,          # turn 0 after Buyer (state is STILL COUNTER_OFFER!)
        mock_neg_terminal  # turn 1 start (terminal, breaks loop)
    ]
    
    mock_buyer.return_value = {"status": "completed"}
    
    intent = BuyerIntent(
        buyer_id=uuid.uuid4(),
        merchant_id=uuid.uuid4(),
        product_query="Buy",
        maximum_budget=Decimal("100"),
        quantity=1,
        preferred_currency="INR"
    )
    
    # Run the loop
    await run_negotiation_loop(neg_id, intent)
    
    # The Buyer should have been called exactly once
    assert mock_buyer.call_count == 1
    # The loop should have gracefully exited when the state became terminal on turn 1,
    # proving it did NOT crash/break on turn 0 when the state didn't mutate.

