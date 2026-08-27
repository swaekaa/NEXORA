import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.runnables import RunnableConfig

from app.agents.buyer.graph import create_buyer_agent_graph
from app.agents.buyer.schemas import ActionType, BuyerAgentAction, BuyerIntent, BuyerAgentState


@pytest.fixture
def base_intent() -> BuyerIntent:
    return BuyerIntent(
        buyer_id=uuid.uuid4(),
        merchant_id=uuid.uuid4(),
        product_query="test monitor",
        quantity=5,
        maximum_budget=Decimal("50000.00"),
        preferred_currency="INR"
    )


@pytest.fixture
def policy_context(base_intent) -> dict:
    return {
        "merchant_id": base_intent.merchant_id,
        "policy_id": uuid.uuid4(),
        "minimum_price": Decimal("1000.00"),
        "maximum_discount_percent": Decimal("10.00"),
        "maximum_autonomous_transaction": Decimal("100000.00"),
        "human_approval_required": False
    }


@pytest.fixture
def base_state(base_intent) -> BuyerAgentState:
    product_id = uuid.uuid4()
    return {
        "run_id": str(uuid.uuid4()),
        "intent": base_intent,
        "step_count": 0,
        "status": "in_progress",
        "error_reason": None,
        "candidate_products": [{"id": product_id, "name": "Test Monitor", "price": "10000.00"}],
        "selected_product_id": product_id,
        "proposal_revisions": 0,
        "negotiation_round": 0,
        "current_action": None,
        "deterministic_total": None,
        "merchant_counter": None,
        "negotiation_status": None,
        "policy_decision": None,
        "policy_reasons": [],
        "negotiation_id": None,
        "messages": []
    }


@pytest.mark.asyncio
async def test_successful_allow_path(base_state, policy_context):
    """
    Path: VALIDATE -> POLICY ALLOW -> SUBMIT PROPOSAL (mocked)
    """
    graph = create_buyer_agent_graph()
    
    # Simulate LLM outputting PROPOSE_AGREEMENT
    base_state["current_action"] = BuyerAgentAction(
        action=ActionType.PROPOSE_AGREEMENT,
        proposed_unit_price="9000.00",
        proposed_discount_percent="0.00",
        reason="Good deal."
    )
    
    config = RunnableConfig(configurable={"session": MagicMock(), "policy_context": policy_context})
    
    # We just run the validation and policy nodes to test deterministic logic
    from app.agents.buyer.nodes import validate_proposal_node
    from app.agents.buyer.policy_node import policy_check_node
    
    v_res = await validate_proposal_node(base_state, config)
    base_state.update(v_res)
    
    # 5 * 9000 = 45000
    assert base_state["deterministic_total"] == Decimal("45000.00")
    
    p_res = await policy_check_node(base_state, config)
    assert p_res["policy_decision"] == "allow"


@pytest.mark.asyncio
async def test_policy_deny_budget(base_state, policy_context):
    """
    Path: LLM PROPOSE -> VALIDATE (Budget fail) -> DENY
    """
    base_state["current_action"] = BuyerAgentAction(
        action=ActionType.PROPOSE_AGREEMENT,
        proposed_unit_price="15000.00", # 5 * 15000 = 75000 > 50000 budget
        proposed_discount_percent="0.00",
        reason="Expensive."
    )
    
    config = RunnableConfig(configurable={"session": MagicMock(), "policy_context": policy_context})
    from app.agents.buyer.nodes import validate_proposal_node
    
    v_res = await validate_proposal_node(base_state, config)
    
    assert v_res["policy_decision"] == "DENY"
    assert "Budget exceeded" in v_res["policy_reasons"][0]
