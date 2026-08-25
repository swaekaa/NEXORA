"""
NEXORA — Buyer Agent Policy Integration
"""
from decimal import Decimal

from app.agents.buyer.schemas import BuyerAgentState, ActionType
from app.policies.engine import PolicyEngine
from app.policies.models import PolicyEvaluationContext, PolicyEvaluationRequest


from app.policies.enums import ActionType as PolicyActionType

def policy_check_node(state: BuyerAgentState, policy_context_data: dict) -> dict:
    """
    Evaluates the deterministic proposal against the Merchant Policy using the pure PolicyEngine.
    This strictly enforces the boundary between LangGraph and PolicyEngine.
    """
    if state.get("policy_decision") == "DENY":
        # Already failed validation (e.g. invalid format)
        return {}
        
    action = state["current_action"]
    
    # Construct request
    req = PolicyEvaluationRequest(
        action=PolicyActionType.CREATE_AGREEMENT,
        merchant_id=state["intent"].merchant_id,
        product_id=state["selected_product_id"],
        quantity=state["intent"].quantity,
        unit_price=Decimal(action.proposed_unit_price).quantize(Decimal("0.01")),
        discount_percent=Decimal(action.proposed_discount_percent).quantize(Decimal("0.01")),
        total_amount=state["deterministic_total"],
        currency=state["intent"].preferred_currency
    )
    
    # Construct context (injected from DB before graph starts)
    ctx = PolicyEvaluationContext(**policy_context_data)
    
    # Execute pure function
    engine = PolicyEngine()
    result = engine.evaluate(req, ctx)
    
    # Extract reasons if any
    reasons = [c.rule_name for c in result.checks if not c.passed]
    
    return {
        "policy_decision": result.decision.value,
        "policy_reasons": reasons
    }


def route_policy_decision(state: BuyerAgentState) -> str:
    """Conditional router based on policy outcome."""
    if state["status"] in ["failed", "completed"]:
        return "END"
        
    action = state["current_action"]
    if action.action == ActionType.STOP:
        return "END"
    elif action.action != ActionType.PROPOSE_AGREEMENT:
        return "run_llm"
        
    decision = state.get("policy_decision")
    
    if decision == "allow":
        return "create_negotiation"
    elif decision == "human_approval_required":
        return "await_human_approval"
    elif decision == "deny":
        return "proposal_recovery"
        
    return "END"


def proposal_recovery_node(state: BuyerAgentState) -> dict:
    """Handles the DENY case, limiting revisions."""
    revisions = state.get("proposal_revisions", 0) + 1
    if revisions > 3:
        return {"status": "failed", "error_reason": "MAX_PROPOSAL_REVISIONS_EXCEEDED"}
        
    return {"proposal_revisions": revisions}
