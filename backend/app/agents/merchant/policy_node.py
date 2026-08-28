"""
NEXORA — Merchant Agent Policy Node
"""
import uuid
from decimal import Decimal
from typing import Literal

from langchain_core.messages import SystemMessage

from app.agents.merchant.schemas import MerchantActionType, MerchantAgentState
from app.policies.engine import PolicyEngine
from app.policies.models import PolicyEvaluationRequest, PolicyEvaluationContext
from app.policies.enums import PolicyDecision, ActionType


def policy_check_node(state: MerchantAgentState) -> dict:
    """
    Evaluates the proposal/counter-offer using the deterministic Policy Engine.
    """
    action = state["current_action"]
    if not action or action.action not in (MerchantActionType.ACCEPT_PROPOSAL, MerchantActionType.COUNTER_PROPOSAL):
        return {}

    intent = state["intent"]
    
    if action.action == MerchantActionType.ACCEPT_PROPOSAL:
        unit_price = intent.buyer_proposed_unit_price
        quantity = intent.buyer_proposed_quantity
        discount = intent.buyer_proposed_discount_percent
    else:
        unit_price = Decimal(action.proposed_unit_price) # type: ignore
        quantity = action.proposed_quantity # type: ignore
        discount = Decimal(action.proposed_discount_percent or "0.0")

    total_amount = state["deterministic_total"]
    assert total_amount is not None

    request = PolicyEvaluationRequest(
        action=ActionType.CREATE_AGREEMENT,
        merchant_id=intent.merchant_id,
        product_id=intent.product_id,
        unit_price=unit_price,
        quantity=quantity,
        total_amount=total_amount,
        currency="INR",
        discount_percent=discount
    )
    
    context = PolicyEvaluationContext(
        merchant_id=intent.merchant_id,
        policy_id=intent.policy_id,
        minimum_price=intent.policy_minimum_price,
        maximum_discount_percent=intent.policy_maximum_discount_percent,
        maximum_autonomous_transaction=intent.policy_maximum_autonomous_transaction,
        human_approval_required=intent.policy_requires_human_approval
    )
    
    engine = PolicyEngine()
    result = engine.evaluate(request, context)
    
    decision = result.decision.value
    reasons = [c.reason for c in result.failed_checks] if result.failed_checks else []
    
    # ---------------------------------------------------------
    # DEMO NEGOTIATION STRATEGY: Enforce minimum rounds
    # ---------------------------------------------------------
    from app.config import settings
    
    if action.action == MerchantActionType.ACCEPT_PROPOSAL and decision == PolicyDecision.ALLOW.value:
        if intent.round_count < settings.NEGOTIATION_DEMO_MIN_ROUNDS:
            decision = PolicyDecision.DENY.value
            reasons.append(
                f"Demo Strategy Active: You attempted to ACCEPT_PROPOSAL on round {intent.round_count}. "
                f"The minimum required rounds is {settings.NEGOTIATION_DEMO_MIN_ROUNDS}. "
                "You MUST generate a COUNTER_PROPOSAL instead to continue the negotiation, even if the current offer is acceptable."
            )
    
    return {
        "policy_decision": decision,
        "policy_reasons": reasons
    }


def counter_offer_recovery_node(state: MerchantAgentState) -> dict:
    """
    Handles DENY decisions. If revisions are under limit, feed feedback back to the LLM.
    Otherwise, fail the run.
    """
    revisions = state.get("proposal_revisions", 0)
    
    if revisions >= 3:
        return {
            "status": "failed",
            "error_reason": "Exceeded maximum counter-offer revisions due to policy violations."
        }
        
    reasons = state.get("policy_reasons", [])
    feedback = f"Your last action was DENIED by the Policy Engine for the following reasons:\n" + "\n".join(reasons)
    feedback += "\nYou MUST revise your counter-offer to comply with the merchant's policy, or REJECT the proposal."
    
    from langchain_core.messages import HumanMessage
    msg = HumanMessage(content=feedback)
    
    return {
        "proposal_revisions": revisions + 1,
        "messages": [msg],
        "policy_decision": None,
        "policy_reasons": None
    }
