"""
Unit tests for the Merchant Agent.
Tests the orchestration, constraints, and policy integration without real LLMs.
"""
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from app.agents.merchant.graph import build_merchant_agent_graph
from app.agents.merchant.schemas import (
    MerchantActionType,
    MerchantAgentAction,
    MerchantAgentState,
    MerchantIntent,
)
from app.models.policy import Policy as MerchantPolicy
from app.policies.enums import PolicyDecision


@pytest.fixture
def mock_llm():
    with patch("app.agents.merchant.nodes.get_llm") as mock_get_llm:
        mock_model = MagicMock()
        mock_get_llm.return_value.with_structured_output.return_value = mock_model
        yield mock_model


@pytest.fixture
def base_intent():
    return MerchantIntent(
        negotiation_id=uuid.uuid4(),
        buyer_id=uuid.uuid4(),
        merchant_id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        buyer_proposed_quantity=100,
        buyer_proposed_unit_price=Decimal("9000.00"),
        buyer_proposed_discount_percent=Decimal("0.0"),
        policy_minimum_price=Decimal("10000.00"),
        policy_maximum_discount_percent=Decimal("5.0"),
        policy_maximum_autonomous_transaction=Decimal("5000000.00"),
        round_count=1,
        max_rounds=10,
        product_description="Test Product",
        buyer_message="Please accept"
    )


@pytest.fixture
def base_state(base_intent) -> MerchantAgentState:
    return {
        "run_id": "test_run",
        "intent": base_intent,
        "step_count": 0,
        "status": "in_progress",
        "error_reason": None,
        "proposal_revisions": 0,
        "current_action": None,
        "deterministic_total": None,
        "policy_decision": None,
        "policy_reasons": None,
        "messages": [],
    }


def test_merchant_accepts_valid_proposal(mock_llm, base_intent, base_state):
    # Setup intent so buyer's proposal is VALID
    base_intent.buyer_proposed_unit_price = Decimal("10500.00")
    
    # Mock LLM to ACCEPT
    mock_llm.invoke.return_value = MerchantAgentAction(
        action=MerchantActionType.ACCEPT_PROPOSAL,
        reason="Looks good"
    )
    
    graph = build_merchant_agent_graph()
    result = graph.invoke(base_state)
    
    assert result["current_action"].action == MerchantActionType.ACCEPT_PROPOSAL
    assert result["deterministic_total"] == Decimal("1050000.00")  # 10500 * 100
    assert result["policy_decision"] == PolicyDecision.ALLOW.value


def test_merchant_rejects_proposal(mock_llm, base_state):
    mock_llm.invoke.return_value = MerchantAgentAction(
        action=MerchantActionType.REJECT_PROPOSAL,
        reason="No thanks"
    )
    
    graph = build_merchant_agent_graph()
    result = graph.invoke(base_state)
    
    assert result["current_action"].action == MerchantActionType.REJECT_PROPOSAL
    assert result["policy_decision"] is None  # Should not reach policy check


def test_merchant_counter_offer_blocked_by_policy(mock_llm, base_state):
    # Mock LLM to Counter BELOW minimum price
    # The policy should DENY and trigger a recovery loop
    mock_llm.invoke.return_value = MerchantAgentAction(
        action=MerchantActionType.COUNTER_PROPOSAL,
        proposed_quantity=100,
        proposed_unit_price="9500.00",  # Min is 10000
        proposed_discount_percent="0.0",
        reason="Countering below minimum price"
    )
    
    graph = build_merchant_agent_graph()
    # Let's set recursion limit to prevent infinite loops if something goes wrong
    result = graph.invoke(base_state, config={"recursion_limit": 25})
    
    # After 3 failed revisions, it should hit the error
    assert result["status"] == "failed"
    assert result["error_reason"] == "Exceeded maximum counter-offer revisions due to policy violations."
    assert result["proposal_revisions"] == 3


def test_merchant_counter_offer_allowed_by_policy(mock_llm, base_state):
    # Mock LLM to Counter ABOVE minimum price
    mock_llm.invoke.return_value = MerchantAgentAction(
        action=MerchantActionType.COUNTER_PROPOSAL,
        proposed_quantity=100,
        proposed_unit_price="10500.00",
        proposed_discount_percent="0.0",
        reason="Valid counter"
    )
    
    graph = build_merchant_agent_graph()
    result = graph.invoke(base_state)
    
    assert result["current_action"].action == MerchantActionType.COUNTER_PROPOSAL
    assert result["policy_decision"] == PolicyDecision.ALLOW.value
    assert result["deterministic_total"] == Decimal("1050000.00")


def test_merchant_requires_human_approval(mock_llm, base_intent, base_state):
    # Make autonomous limit small
    base_intent.policy_maximum_autonomous_transaction = Decimal("5000.0")
    
    mock_llm.invoke.return_value = MerchantAgentAction(
        action=MerchantActionType.COUNTER_PROPOSAL,
        proposed_quantity=100,
        proposed_unit_price="10500.00",
        proposed_discount_percent="0.0",
        reason="Counter offer"
    )
    
    graph = build_merchant_agent_graph()
    result = graph.invoke(base_state)
    
    assert result["policy_decision"] == PolicyDecision.HUMAN_APPROVAL_REQUIRED.value
    assert result.get("status") != "failed" # Awaiting human approval
