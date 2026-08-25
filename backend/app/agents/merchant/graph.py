"""
NEXORA — Merchant Agent Graph
"""
from typing import Literal

from langgraph.graph import END, StateGraph

from app.agents.merchant.nodes import run_llm_node, validate_action_node
from app.agents.merchant.policy_node import (
    counter_offer_recovery_node,
    policy_check_node,
    route_policy_decision,
)
from app.agents.merchant.schemas import MerchantActionType, MerchantAgentState


def route_after_llm(state: MerchantAgentState) -> Literal["validate_action", "completed"]:
    action = state.get("current_action")
    if not action:
        return "completed" # Should not happen unless failed
    
    if action.action in (MerchantActionType.STOP, MerchantActionType.REJECT_PROPOSAL):
        return "completed"
        
    return "validate_action"


def route_after_validation(state: MerchantAgentState) -> Literal["policy_check", "completed", "failed"]:
    if state["status"] == "failed":
        return "failed"
    if state["status"] == "completed":
        return "completed"
    if state["status"] == "awaiting_human_approval":
        return "completed"
        
    return "policy_check"


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
    
    # Validate -> Policy Check
    workflow.add_conditional_edges(
        "validate_action",
        route_after_validation,
        {
            "policy_check": "policy_check",
            "completed": END,
            "failed": END
        }
    )
    
    # Policy Check -> Decision Routing
    workflow.add_conditional_edges(
        "policy_check",
        route_policy_decision,
        {
            "completed": END,
            "awaiting_human_approval": END,
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
    
    return workflow.compile()
