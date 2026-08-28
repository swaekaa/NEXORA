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
    Evaluates the deterministic proposal against the Merchant Policy using the pure PolicyEngine.
    """
    if state.get("policy_decision") == "deny":
        # Already failed buyer constraints
        return {}
        
    action = state["current_action"]
    
    # Construct request
    product_id = state.get("selected_product_id") or getattr(action, "product_id", None)
    req = PolicyEvaluationRequest(
        action=PolicyActionType.CREATE_AGREEMENT,
        merchant_id=state["intent"].merchant_id,
        product_id=product_id,
        quantity=state["intent"].quantity,
        unit_price=Decimal(action.proposed_unit_price).quantize(Decimal("0.01")),
        discount_percent=Decimal(action.proposed_discount_percent or "0").quantize(Decimal("0.01")),
        total_amount=state["deterministic_total"],
        currency=state["intent"].preferred_currency
    )
    
    # Construct context from config (injected by runner)
    policy_context_data = config["configurable"].get("policy_context")
    if not policy_context_data:
        # Fallback if no policy context is provided
        return {"policy_decision": "allow", "policy_reasons": []}
        
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
    elif action.action not in (ActionType.PROPOSE_AGREEMENT, ActionType.COUNTER_PROPOSAL):
        return "run_llm"
        
    decision = state.get("policy_decision")
    
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
