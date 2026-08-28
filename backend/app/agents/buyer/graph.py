"""
NEXORA — Buyer Agent Graph

Orchestrates the LLM, deterministic boundaries, and policy validation.
Evolved for Phase 10 to support multi-round negotiations and real DB access.
"""
from langgraph.graph import END, StateGraph

from app.agents.buyer.nodes import (
    execute_action_node, 
    run_llm_node, 
    validate_proposal_node,
    submit_proposal_node,
    read_negotiation_state_node
)
from app.agents.buyer.policy_node import policy_check_node, proposal_recovery_node, route_policy_decision
from app.agents.buyer.schemas import BuyerAgentState


def create_buyer_agent_graph() -> StateGraph:
    """
    Builds the LangGraph state machine.
    We rely on RunnableConfig (injected by runner) for DB sessions and context.
    """
    workflow = StateGraph(BuyerAgentState)
    
    # ── Nodes ──
    workflow.add_node("read_negotiation_state", read_negotiation_state_node)
    workflow.add_node("run_llm", run_llm_node)
    workflow.add_node("execute_action", execute_action_node)
    workflow.add_node("validate_proposal", validate_proposal_node)
    workflow.add_node("policy_check", policy_check_node)
    workflow.add_node("submit_proposal", submit_proposal_node)
    workflow.add_node("proposal_recovery", proposal_recovery_node)
    
    # Terminal / External Nodes
    def await_human_approval(state: BuyerAgentState):
        return {"status": "awaiting_human_approval"}
    workflow.add_node("await_human_approval", await_human_approval)
    
    # ── Edges ──
    # Always read the latest DB state before making a decision
    workflow.set_entry_point("read_negotiation_state")
    workflow.add_edge("read_negotiation_state", "run_llm")
    
    workflow.add_edge("run_llm", "execute_action")
    
    # After action execution, we check what it did
    def route_after_action(state: BuyerAgentState):
        if state["status"] in ["completed", "failed"]:
            return "END"
            
        action = state["current_action"]
        if action.action in ["PROPOSE_AGREEMENT", "COUNTER_PROPOSAL", "ACCEPT_COUNTER"]:
            return "validate_proposal"
            
        # Otherwise, go back to LLM to take next action (like searching)
        return "run_llm"
        
    workflow.add_conditional_edges(
        "execute_action",
        route_after_action,
        {
            "END": END,
            "validate_proposal": "validate_proposal",
            "submit_proposal": "submit_proposal",
            "run_llm": "run_llm"
        }
    )
    
    workflow.add_edge("validate_proposal", "policy_check")
    
    workflow.add_conditional_edges(
        "policy_check",
        route_policy_decision,
        {
            "submit_proposal": "submit_proposal",
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
    
    workflow.add_edge("submit_proposal", END)
    workflow.add_edge("await_human_approval", END)
    
    return workflow.compile()
