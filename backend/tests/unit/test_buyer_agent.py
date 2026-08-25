import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

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
        "selected_product_id": None,
        "proposal_revisions": 0,
        "current_action": None,
        "deterministic_total": None,
        "policy_decision": None,
        "policy_reasons": [],
        "negotiation_id": None,
        "messages": []
    }


def test_successful_allow_path(base_state, policy_context):
    """
    Path: LLM PROPOSE -> VALIDATE -> POLICY ALLOW -> END
    """
    graph = create_buyer_agent_graph(policy_context)
    
    mock_action = BuyerAgentAction(
        action=ActionType.PROPOSE_AGREEMENT,
        product_id=base_state["candidate_products"][0]["id"],
        proposed_unit_price="10000.00",
        proposed_discount_percent="5.00",
        reason="Good price"
    )
    
    # We mock get_llm to return a fake that outputs mock_action
    with patch("app.agents.buyer.nodes.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_with_structured = MagicMock()
        mock_with_structured.invoke.return_value = mock_action
        mock_llm.with_structured_output.return_value = mock_with_structured
        mock_get_llm.return_value = mock_llm
        
        # We need the state to already have the product selected for policy to work
        base_state["selected_product_id"] = mock_action.product_id
        
        result = graph.invoke(base_state)
        
        assert result["status"] == "completed"
        assert result["policy_decision"] == "allow"
        assert result["deterministic_total"] == Decimal("50000.00") # 10000 * 5


def test_deny_recovery_limit(base_state, policy_context):
    """
    Path: LLM PROPOSE -> POLICY DENY -> REVISE (x3) -> FAILED
    """
    graph = create_buyer_agent_graph(policy_context)
    
    # Propose price below minimum
    mock_action = BuyerAgentAction(
        action=ActionType.PROPOSE_AGREEMENT,
        product_id=base_state["candidate_products"][0]["id"],
        proposed_unit_price="500.00",  # Below min 1000
        proposed_discount_percent="0.00",
        reason="Too cheap"
    )
    
    with patch("app.agents.buyer.nodes.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_with_structured = MagicMock()
        mock_with_structured.invoke.return_value = mock_action
        mock_llm.with_structured_output.return_value = mock_with_structured
        mock_get_llm.return_value = mock_llm
        
        base_state["selected_product_id"] = mock_action.product_id
        
        result = graph.invoke(base_state)
        
        # After 4 iterations, it hits the limit
        assert result["status"] == "failed"
        assert result["error_reason"] == "MAX_PROPOSAL_REVISIONS_EXCEEDED"
        assert result["policy_decision"] == "deny"


def test_human_approval_pause(base_state, policy_context):
    """
    Path: LLM PROPOSE -> POLICY HUMAN_APPROVAL_REQUIRED -> PAUSE
    """
    # Override context to force approval
    policy_context["human_approval_required"] = True
    graph = create_buyer_agent_graph(policy_context)
    
    mock_action = BuyerAgentAction(
        action=ActionType.PROPOSE_AGREEMENT,
        product_id=base_state["candidate_products"][0]["id"],
        proposed_unit_price="10000.00",
        proposed_discount_percent="0.00",
        reason="Valid"
    )
    
    with patch("app.agents.buyer.nodes.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_with_structured = MagicMock()
        mock_with_structured.invoke.return_value = mock_action
        mock_llm.with_structured_output.return_value = mock_with_structured
        mock_get_llm.return_value = mock_llm
        
        base_state["selected_product_id"] = mock_action.product_id
        
        result = graph.invoke(base_state)
        
        assert result["status"] == "awaiting_human_approval"
        assert result["policy_decision"] == "human_approval_required"


def test_deterministic_math_enforced(base_state, policy_context):
    """
    Ensure that LLM cannot hallucinate bad math.
    """
    graph = create_buyer_agent_graph(policy_context)
    
    # We pass bad strings. The determinism will calculate it strictly.
    mock_action = BuyerAgentAction(
        action=ActionType.PROPOSE_AGREEMENT,
        product_id=base_state["candidate_products"][0]["id"],
        proposed_unit_price="1000.00",
        proposed_discount_percent="0.00",
        reason="Math test"
    )
    
    with patch("app.agents.buyer.nodes.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_with_structured = MagicMock()
        mock_with_structured.invoke.return_value = mock_action
        mock_llm.with_structured_output.return_value = mock_with_structured
        mock_get_llm.return_value = mock_llm
        
        base_state["selected_product_id"] = mock_action.product_id
        
        result = graph.invoke(base_state)
        
        # 1000 * 5 qty = 5000
        assert result["deterministic_total"] == Decimal("5000.00")
        assert result["policy_decision"] == "allow"
