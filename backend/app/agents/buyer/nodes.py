"""
NEXORA — Buyer Agent Nodes

The deterministic functions that execute the LangGraph state machine.
"""
from decimal import Decimal, InvalidOperation

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.buyer.config import get_llm
from app.agents.buyer.prompts import SYSTEM_INSTRUCTION
from app.agents.buyer.schemas import ActionType, BuyerAgentAction, BuyerAgentState
from app.policies.engine import PolicyEngine
from app.policies.models import PolicyEvaluationContext, PolicyEvaluationRequest


def format_state_for_llm(state: BuyerAgentState) -> list:
    """Format the runtime state into messages for the LLM."""
    intent = state["intent"]
    
    # Safely format product catalog for context
    catalog_text = "Available Products:\n"
    if not state["candidate_products"]:
        catalog_text += "No products discovered yet. Use search_products tool."
    else:
        for p in state["candidate_products"]:
            catalog_text += f"- ID: {p.get('id')} | Name: {p.get('name')} | Price: {p.get('price')} | SKU: {p.get('sku')} | Desc: {p.get('description')}\n"
    
    # Format policy feedback if any
    policy_status = state.get("policy_decision") or "NONE"
    policy_reasons = state.get("policy_reasons") or []
    reasons_text = ", ".join(policy_reasons) if policy_reasons else "NONE"
    
    human_msg = (
        f"--- BUYER INTENT ---\n"
        f"Budget: {intent.maximum_budget} {intent.preferred_currency}\n"
        f"Quantity: {intent.quantity}\n"
        f"Query: {intent.product_query}\n"
        f"Requirements: {intent.requirements}\n"
        f"Preferences: {intent.preferences}\n"
        f"--------------------\n\n"
        f"--- CURRENT STATE ---\n"
        f"Selected Product ID: {state.get('selected_product_id')}\n"
        f"---------------------\n\n"
        f"--- POLICY FEEDBACK ---\n"
        f"Status: {policy_status}\n"
        f"Reasons: {reasons_text}\n"
        f"-----------------------\n\n"
        f"{catalog_text}\n\n"
        f"Action: What will you do next? (Must respond with valid JSON matching BuyerAgentAction)"
    )
    
    return [
        SystemMessage(content=SYSTEM_INSTRUCTION),
        HumanMessage(content=human_msg)
    ]


def run_llm_node(state: BuyerAgentState) -> dict:
    """Invokes the LLM to get the next BuyerAgentAction."""
    # Check max steps
    if state["step_count"] >= 10:
        return {"status": "failed", "error_reason": "MAX_AGENT_STEPS_EXCEEDED"}
        
    messages = format_state_for_llm(state)
    llm = get_llm().with_structured_output(BuyerAgentAction)
    
    try:
        action: BuyerAgentAction = llm.invoke(messages)
    except Exception as e:
        return {"status": "failed", "error_reason": f"LLM Error: {str(e)}"}
        
    return {
        "current_action": action,
        "step_count": state["step_count"] + 1,
        "policy_decision": None,  # Reset feedback on new action
        "policy_reasons": []
    }


def execute_action_node(state: BuyerAgentState) -> dict:
    """Executes the action chosen by the LLM (Deterministic logic)."""
    action = state["current_action"]
    if not action:
        return {"status": "failed", "error_reason": "No action provided"}
        
    if action.action == ActionType.STOP:
        return {"status": "completed"}
        
    elif action.action == ActionType.SEARCH_PRODUCTS:
        # We don't actually run a DB query here in Phase 5 because products are injected 
        # into the state at initialization by the API endpoint, keeping DB out of graph.
        # But we could filter the list.
        return {} # Just progress state
        
    elif action.action == ActionType.SELECT_PRODUCT:
        if not action.product_id:
            return {"policy_decision": "DENY", "policy_reasons": ["product_id is required for SELECT_PRODUCT"]}
        
        # Verify product exists in candidates
        found = any(str(p.get("id")) == str(action.product_id) for p in state["candidate_products"])
        if not found:
            return {"policy_decision": "DENY", "policy_reasons": ["Invalid product_id selected"]}
            
        return {"selected_product_id": action.product_id}
        
    elif action.action == ActionType.PROPOSE_AGREEMENT:
        return {} # Next node validates the proposal
        
    return {"status": "failed", "error_reason": "Unknown Action"}


def validate_proposal_node(state: BuyerAgentState) -> dict:
    """Deterministically parses and calculates the proposal totals."""
    action = state["current_action"]
    
    try:
        if action.proposed_unit_price is None or action.proposed_discount_percent is None:
            raise ValueError("Unit price and discount are required.")
            
        unit_price = Decimal(action.proposed_unit_price).quantize(Decimal("0.01"))
        discount = Decimal(action.proposed_discount_percent).quantize(Decimal("0.01"))
        qty = Decimal(state["intent"].quantity)
        
        # DETERMINISTIC TOTAL CALCULATION
        # The LLM is NEVER trusted to do this math.
        # This MUST exactly match Phase 4 PolicyEngine AGREEMENT_TOTAL_INTEGRITY:
        # total_amount = unit_price * quantity (discount is evaluated separately).
        total = (unit_price * qty).quantize(Decimal("0.01"))
        
    except (InvalidOperation, ValueError, TypeError) as e:
        return {
            "policy_decision": "DENY", 
            "policy_reasons": [f"Deterministic validation failed: Invalid numeric formats. {str(e)}"]
        }
        
    return {"deterministic_total": total}
