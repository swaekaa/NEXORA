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


from langchain_core.runnables import RunnableConfig
from app.services.negotiation_service import append_negotiation_message
from app.models.negotiation_message import SenderType, MessageType
from app.schemas.negotiation import NegotiationMessagePayload
from app.services.agreement_service import create_agreement_from_negotiation

# Phase 12 Placeholder
async def create_approval_request(*args, **kwargs):
    pass

async def submit_decision_node(state: MerchantAgentState, config: RunnableConfig) -> dict:
    """
    Persists the final ALLOWED decision (ACCEPT, COUNTER, REJECT) to the NegotiationService.
    If ACCEPT, triggers Agreement creation.
    """
    action = state["current_action"]
    intent = state["intent"]
    session = config["configurable"]["session"]
    
    if not action:
        return {"status": "failed", "error_reason": "No action to submit"}
        
    if action.action == MerchantActionType.REJECT_PROPOSAL:
        await append_negotiation_message(
            session=session,
            negotiation_id=intent.negotiation_id,
            sender_type=SenderType.MERCHANT_AGENT,
            sender_id=str(intent.merchant_id),
            message_type=MessageType.REJECT,
            content=action.reason
        )
        return {"status": "completed"}
        
    elif action.action == MerchantActionType.ACCEPT_PROPOSAL:
        await append_negotiation_message(
            session=session,
            negotiation_id=intent.negotiation_id,
            sender_type=SenderType.MERCHANT_AGENT,
            sender_id=str(intent.merchant_id),
            message_type=MessageType.ACCEPT,
            content=action.reason
        )
        await create_agreement_from_negotiation(session, intent.negotiation_id)
        return {"status": "completed"}
        
    elif action.action == MerchantActionType.COUNTER_PROPOSAL:
        payload = NegotiationMessagePayload(
            product_id=intent.product_id,
            quantity=action.proposed_quantity, # type: ignore
            unit_price=Decimal(action.proposed_unit_price), # type: ignore
            discount_percent=Decimal(action.proposed_discount_percent or "0"),
            total_amount=state["deterministic_total"], # type: ignore
            currency=intent.currency
        )
        await append_negotiation_message(
            session=session,
            negotiation_id=intent.negotiation_id,
            sender_type=SenderType.MERCHANT_AGENT,
            sender_id=str(intent.merchant_id),
            message_type=MessageType.COUNTER_OFFER,
            content=action.reason,
            payload=payload
        )
        return {"status": "completed"}
        
    return {"status": "completed"}


async def request_approval_node(state: MerchantAgentState, config: RunnableConfig) -> dict:
    """
    Creates an ApprovalRequest for HUMAN_APPROVAL_REQUIRED policy decisions.
    Ends the agent's execution.
    """
    intent = state["intent"]
    session = config["configurable"]["session"]
    
    await create_approval_request(
        session=session,
        merchant_id=intent.merchant_id,
        approval_type="POLICY_OVERRIDE",
        entity_id=intent.negotiation_id,
        requested_by="Merchant Agent",
        reason="Policy Engine flagged this proposal for human review."
    )
    return {"status": "completed"}
