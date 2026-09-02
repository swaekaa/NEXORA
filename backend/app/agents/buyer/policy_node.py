"""
NEXORA — Buyer Agent Policy Integration
"""
from decimal import Decimal

from langchain_core.runnables import RunnableConfig

from app.agents.buyer.schemas import BuyerAgentState, ActionType
from app.policies.engine import PolicyEngine
from app.policies.models import PolicyEvaluationContext, PolicyEvaluationRequest


from app.policies.enums import ActionType as PolicyActionType

async def policy_check_node(state: BuyerAgentState, config: RunnableConfig) -> dict:
    """
    Evaluates the deterministic proposal.
    In Phase 14 (Multi-Round Demo), the Buyer Agent no longer uses the Merchant's PolicyEngine
    to evaluate its outbound proposals. Doing so prematurely blocked lowball offers.
    Instead, it relies entirely on the BuyerConstraintEngine (evaluated in validate_proposal_node).
    """
    if state.get("policy_decision") == "DENY":
        # Already failed buyer constraints in validate_proposal_node
        return {}
        
    action = state["current_action"]
    
    # If the BuyerConstraintEngine allowed it (or wasn't triggered), we allow it.
    return {
        "policy_decision": "allow",
        "policy_reasons": []
    }


def route_policy_decision(state: BuyerAgentState) -> str:
    """Conditional router based on policy outcome."""
    if state.get("status") in ["failed", "completed"]:
        return "END"
        
    action = state["current_action"]
    if action.action in (ActionType.STOP, ActionType.REJECT_NEGOTIATION):
        return "END"
    elif action.action not in (ActionType.PROPOSE_AGREEMENT, ActionType.COUNTER_PROPOSAL, ActionType.ACCEPT_COUNTER):
        return "run_llm"
        
    decision = state.get("policy_decision")
    if decision:
        decision = decision.lower()
    
    if decision in ["allow", "human_approval_required"]:
        return "submit_proposal"
    elif decision == "deny":
        return "proposal_recovery"
        
    return "END"



def proposal_recovery_node(state: BuyerAgentState, config: RunnableConfig) -> dict:
    """Handles the DENY case, limiting revisions."""
    revisions = state.get("proposal_revisions", 0) + 1
    if revisions > 3:
        return {"status": "failed", "error_reason": "MAX_PROPOSAL_REVISIONS_EXCEEDED"}
        
    return {"proposal_revisions": revisions}
