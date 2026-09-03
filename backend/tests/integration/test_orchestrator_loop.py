import pytest
import uuid
from decimal import Decimal
from typing import cast
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.negotiation import Negotiation, NegotiationState
from app.models.negotiation_message import NegotiationMessage, MessageType, SenderType
from app.schemas.negotiation import NegotiationMessagePayload
from app.agents.buyer.schemas import BuyerIntent
from app.database.connection import get_db
from app.models.buyer import Buyer
from app.models.merchant import Merchant
from app.models.product import Product
from app.models.policy import Policy
import pytest_asyncio
import asyncio

pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture
async def db_session():
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
        description="A product for testing orchestration loop.",
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

class MockBuyerLLM:
    """Mock LLM to deterministically output PROPOSE_AGREEMENT or COUNTER_PROPOSAL."""
    def __init__(self, actions):
        self.actions = actions
        self.call_count = 0
        
    def with_structured_output(self, schema):
        return self
        
    async def ainvoke(self, messages):
        if self.call_count < len(self.actions):
            action = self.actions[self.call_count]
            self.call_count += 1
            return action
        raise ValueError("MockLLM exhausted")

class MockMerchantLLM:
    """Mock LLM to deterministically output COUNTER_PROPOSAL or ACCEPT_PROPOSAL."""
    def __init__(self, actions):
        self.actions = actions
        self.call_count = 0
        
    def with_structured_output(self, schema):
        return self
        
    async def ainvoke(self, messages):
        if self.call_count < len(self.actions):
            action = self.actions[self.call_count]
            self.call_count += 1
            return action
        raise ValueError("MockLLM exhausted")


async def test_orchestrator_loop_continuation(db_session: AsyncSession, setup_db_entities, monkeypatch):
    """
    Validates that the orchestrator loop correctly continues past Round 2.
    Buyer generates Opening Offer -> Merchant generates Counteroffer -> Buyer is invoked again.
    """
    from app.agents.buyer.schemas import BuyerAgentAction, ActionType
    from app.agents.merchant.schemas import MerchantAgentAction, MerchantActionType
    from app.agents.buyer import nodes as buyer_nodes
    from app.agents.merchant import nodes as merchant_nodes
    from app.services.orchestrator import run_negotiation_loop
    from app.services.negotiation_service import get_negotiation_messages

    buyer_id = setup_db_entities["buyer_id"]
    merchant_id = setup_db_entities["merchant_id"]
    product_id = setup_db_entities["product_id"]

    # Mock the Buyer LLM to first make an offer, then counter the merchant's counter.
    buyer_llm = MockBuyerLLM([
        BuyerAgentAction(action=ActionType.PROPOSE_AGREEMENT, proposed_unit_price="13500.00", product_id=str(product_id), reason="Opening offer"),
        BuyerAgentAction(action=ActionType.COUNTER_PROPOSAL, proposed_unit_price="13800.00", product_id=str(product_id), reason="Counter offer 1")
    ])
    
    # Mock the Merchant LLM to first counter, then accept.
    merchant_llm = MockMerchantLLM([
        MerchantAgentAction(action=MerchantActionType.COUNTER_PROPOSAL, proposed_unit_price="14500.00", proposed_quantity=10, reason="Counter offer 1"),
        MerchantAgentAction(action=MerchantActionType.ACCEPT_PROPOSAL, reason="Accepting buyer counter")
    ])

    monkeypatch.setattr(buyer_nodes, "get_llm", lambda: buyer_llm)
    monkeypatch.setattr(merchant_nodes, "get_llm", lambda: merchant_llm)

    intent = BuyerIntent(
        buyer_id=buyer_id,
        merchant_id=merchant_id,
        product_query="Dell 24 inch monitor",
        quantity=10,
        maximum_budget=Decimal("450000.00"),
        preferred_currency="INR"
    )

    from app.agents.buyer.runner import run_buyer_agent
    
    # 1. Start the negotiation (this mimics the API endpoint behavior)
    final_state = await run_buyer_agent(db_session, intent)
    assert final_state["status"] == "completed"
    negotiation_id = final_state["negotiation_id"]
    
    # Verify first message (Buyer Opening Offer) is saved
    messages = await get_negotiation_messages(db_session, negotiation_id)
    assert len(messages) == 1
    assert messages[0].sender_type == SenderType.BUYER_AGENT.value

    # 2. Run the orchestrator loop exactly as the background task does
    # The orchestrator will fetch messages, see Buyer is last sender, and invoke Merchant.
    # Then it will fetch messages, see Merchant is last sender, and invoke Buyer.
    # Then it will fetch messages, see Buyer is last sender, and invoke Merchant (Accepts).
    intent.negotiation_id = negotiation_id
    
    # We run the loop. Since it's an async loop that only breaks on terminal states,
    # it will run until the mocked Merchant accepts.
    await run_negotiation_loop(negotiation_id, intent)
    
    # 3. Assertions
    messages = await get_negotiation_messages(db_session, negotiation_id)
    
    # Total messages should be 4:
    # 1. Buyer Offer
    # 2. Merchant Counter
    # 3. Buyer Counter
    # 4. Merchant Accept
    assert len(messages) == 4, f"Expected 4 messages, got {len(messages)}"
    
    assert messages[0].sender_type == SenderType.BUYER_AGENT.value
    assert messages[1].sender_type == SenderType.MERCHANT_AGENT.value
    assert messages[2].sender_type == SenderType.BUYER_AGENT.value
    assert messages[3].sender_type == SenderType.MERCHANT_AGENT.value
    
    assert messages[3].message_type == MessageType.ACCEPT.value
