"""
NEXORA — Merchant Agent Nodes
"""
import uuid
from decimal import Decimal
from typing import cast

from langchain_core.messages import AIMessage, SystemMessage

from app.agents.merchant.config import get_llm
from app.agents.merchant.prompts import get_prompt
from app.agents.merchant.schemas import (
    MerchantActionType,
    MerchantAgentAction,
    MerchantAgentState,
)


def run_llm_node(state: MerchantAgentState) -> dict:
    """
    Invokes the LLM to get the MerchantAgentAction.
    """
    if state["status"] != "in_progress":
        return {}

    prompt = get_prompt()
    
    # Render the prompt with state data
    messages = prompt.format_messages(
        policy_minimum_price=state["intent"].policy_minimum_price,
        policy_maximum_autonomous_transaction=state["intent"].policy_maximum_autonomous_transaction,
        policy_maximum_discount_percent=state["intent"].policy_maximum_discount_percent,
        product_description=state["intent"].product_description,
        round_count=state["intent"].round_count,
        max_rounds=state["intent"].max_rounds,
        buyer_proposed_quantity=state["intent"].buyer_proposed_quantity,
        buyer_proposed_unit_price=state["intent"].buyer_proposed_unit_price,
        buyer_proposed_discount_percent=state["intent"].buyer_proposed_discount_percent,
        buyer_message=state["intent"].buyer_message or "None",
        messages=state["messages"]
    )
    
    llm = get_llm().with_structured_output(MerchantAgentAction)
    
    try:
        action = cast(MerchantAgentAction, llm.invoke(messages))
        
        # Append the reasoning to the message history so LangGraph retains it
        new_msg = AIMessage(content=f"Action: {action.action.value}\nReason: {action.reason}")
        
        return {
            "current_action": action,
            "messages": [new_msg],
        }
    except Exception as e:
        return {
            "status": "failed",
            "error_reason": f"LLM parsing error: {str(e)}"
        }


def validate_action_node(state: MerchantAgentState) -> dict:
    """
    Performs deterministic mathematical calculations for the chosen action.
    For ACCEPT_PROPOSAL, we validate the buyer's proposal.
    For COUNTER_PROPOSAL, we validate the merchant's counter.
    """
    action = state["current_action"]
    if not action:
        return {}
        
    if action.action == MerchantActionType.STOP or action.action == MerchantActionType.REJECT_PROPOSAL:
        return {"status": "completed"}
        
    if action.action == MerchantActionType.REQUEST_HUMAN_APPROVAL:
        return {"status": "awaiting_human_approval"}
        
    # Determine the values to validate based on the action
    if action.action == MerchantActionType.ACCEPT_PROPOSAL:
        # We must validate the BUYER's proposed values
        quantity = state["intent"].buyer_proposed_quantity
        try:
            unit_price = state["intent"].buyer_proposed_unit_price
        except Exception:
            return {"status": "failed", "error_reason": "Invalid buyer unit price format"}
    else:
        # COUNTER_PROPOSAL
        if not action.proposed_quantity or not action.proposed_unit_price:
            return {"status": "failed", "error_reason": "Counter proposal missing quantity or unit price"}
            
        quantity = action.proposed_quantity
        try:
            unit_price = Decimal(action.proposed_unit_price)
        except Exception:
            return {"status": "failed", "error_reason": "Invalid counter unit price format"}

    # Deterministic Total Calculation
    total_amount = unit_price * Decimal(quantity)
    
    return {
        "deterministic_total": total_amount
    }
