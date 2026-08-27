from typing import Literal

from langgraph.graph import END, StateGraph

from app.agents.merchant.nodes import (
    run_llm_node,
    validate_action_node,
    submit_decision_node,
    request_approval_node,
)
from app.agents.merchant.policy_node import (
    counter_offer_recovery_node,
    policy_check_node,
)
from app.agents.merchant.schemas import MerchantActionType, MerchantAgentState


def route_after_llm(state: MerchantAgentState) -> Literal["validate_action", "completed"]:
    action = state.get("current_action")
    if not action:
        return "completed" # Should not happen unless failed
    
    if action.action == MerchantActionType.STOP:
        return "completed"
        
    # REJECT_PROPOSAL goes to validate_action so it can be routed to policy_check/submit_decision
    return "validate_action"


def route_after_validation(state: MerchantAgentState) -> Literal["policy_check", "submit_decision", "failed"]:
    if state["status"] == "failed":
        return "failed"
    
    action = state.get("current_action")
    if action and action.action == MerchantActionType.REJECT_PROPOSAL:
        return "submit_decision"
        
    return "policy_check"


from app.policies.enums import PolicyDecision

def route_after_policy(state: MerchantAgentState) -> Literal["submit_decision", "request_approval", "recover"]:
    decision = state.get("policy_decision")
    
    if decision == PolicyDecision.ALLOW.value:
        return "submit_decision"
    elif decision == PolicyDecision.HUMAN_APPROVAL_REQUIRED.value:
        return "request_approval"
    else:
        return "recover"


def route_after_recovery(state: MerchantAgentState) -> Literal["run_llm", "failed"]:
    if state["status"] == "failed":
        return "failed"
    return "run_llm"


def build_merchant_agent_graph() -> StateGraph:
    """
    Builds and compiles the Merchant Agent state machine.
    """
    workflow = StateGraph(MerchantAgentState)
    
    # Add nodes
    workflow.add_node("run_llm", run_llm_node)
    workflow.add_node("validate_action", validate_action_node)
    workflow.add_node("policy_check", policy_check_node)
    workflow.add_node("submit_decision", submit_decision_node)
    workflow.add_node("request_approval", request_approval_node)
    workflow.add_node("recovery", counter_offer_recovery_node)
    
    # Set entry point
    workflow.set_entry_point("run_llm")
    
    # LLM -> Validate
    workflow.add_conditional_edges(
        "run_llm",
        route_after_llm,
        {
            "validate_action": "validate_action",
            "completed": END
        }
    )
    
    # Validate -> Policy Check / Submit
    workflow.add_conditional_edges(
        "validate_action",
        route_after_validation,
        {
            "policy_check": "policy_check",
            "submit_decision": "submit_decision",
            "failed": END
        }
    )
    
    # Policy Check -> Decision Routing
    workflow.add_conditional_edges(
        "policy_check",
        route_after_policy,
        {
            "submit_decision": "submit_decision",
            "request_approval": "request_approval",
            "recover": "recovery"
        }
    )
    
    # Recovery -> LLM
    workflow.add_conditional_edges(
        "recovery",
        route_after_recovery,
        {
            "run_llm": "run_llm",
            "failed": END
        }
    )
    
    # Terminal nodes
    workflow.add_edge("submit_decision", END)
    workflow.add_edge("request_approval", END)
    
    return workflow.compile()
