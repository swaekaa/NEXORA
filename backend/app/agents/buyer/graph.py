"""
NEXORA — Buyer Agent Graph

Orchestrates the LLM, deterministic boundaries, and policy validation.
"""
from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.buyer.nodes import execute_action_node, run_llm_node, validate_proposal_node
from app.agents.buyer.policy_node import policy_check_node, proposal_recovery_node, route_policy_decision
from app.agents.buyer.schemas import BuyerAgentState


def create_buyer_agent_graph(policy_context_data: dict) -> StateGraph:
    """
    Builds the LangGraph state machine.
    We inject the policy_context_data so it doesn't need to fetch it internally.
    """
    workflow = StateGraph(BuyerAgentState)
    
    # ── Nodes ──
    workflow.add_node("run_llm", run_llm_node)
    workflow.add_node("execute_action", execute_action_node)
    workflow.add_node("validate_proposal", validate_proposal_node)
    
    # Curry the policy node with the context
    def bound_policy_check(state: BuyerAgentState):
        return policy_check_node(state, policy_context_data)
        
    workflow.add_node("policy_check", bound_policy_check)
    workflow.add_node("proposal_recovery", proposal_recovery_node)
    
    # Terminal / External Nodes (Just update state for now)
    def await_human_approval(state: BuyerAgentState):
        return {"status": "awaiting_human_approval"}
    workflow.add_node("await_human_approval", await_human_approval)
    
    def create_negotiation_node(state: BuyerAgentState):
        # The actual DB creation is handled by the calling service that executes the graph,
        # so this node just marks completion.
        return {"status": "completed"}
    workflow.add_node("create_negotiation", create_negotiation_node)
    
    # ── Edges ──
    workflow.set_entry_point("run_llm")
    
    workflow.add_edge("run_llm", "execute_action")
    
    # After action execution, we check what it did
    def route_after_action(state: BuyerAgentState):
        if state["status"] in ["completed", "failed"]:
            return "END"
        action = state["current_action"]
        if action.action == "PROPOSE_AGREEMENT":
            return "validate_proposal"
        # Otherwise, go back to LLM to take next action
        return "run_llm"
        
    workflow.add_conditional_edges(
        "execute_action",
        route_after_action,
        {
            "END": END,
            "validate_proposal": "validate_proposal",
            "run_llm": "run_llm"
        }
    )
    
    workflow.add_edge("validate_proposal", "policy_check")
    
    workflow.add_conditional_edges(
        "policy_check",
        route_policy_decision,
        {
            "create_negotiation": "create_negotiation",
            "await_human_approval": "await_human_approval",
            "proposal_recovery": "proposal_recovery",
            "run_llm": "run_llm",
            "END": END
        }
    )
    
    workflow.add_conditional_edges(
        "proposal_recovery",
        lambda s: "END" if s["status"] == "failed" else "run_llm",
        {
            "END": END,
            "run_llm": "run_llm"
        }
    )
    
    workflow.add_edge("create_negotiation", END)
    workflow.add_edge("await_human_approval", END)
    
    return workflow.compile()
