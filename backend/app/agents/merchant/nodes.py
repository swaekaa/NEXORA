"""
NEXORA — Merchant Agent Nodes
"""
import uuid
from decimal import Decimal
from typing import cast
import time
import asyncio

from langchain_core.messages import AIMessage, SystemMessage

from app.llm import get_llm
from app.agents.merchant.prompts import get_prompt
from app.agents.merchant.schemas import (
    MerchantActionType,
    MerchantAgentAction,
    MerchantAgentState,
)


import logging

logger = logging.getLogger(__name__)

async def run_llm_node(state: MerchantAgentState) -> dict:
    """
    Invokes the LLM to get the MerchantAgentAction.
    """
    logger.info(f"MERCHANT_GRAPH_STARTED | negotiation_id={state['intent'].negotiation_id}")
    logger.info(f"MERCHANT_LLM_STARTED | negotiation_id={state['intent'].negotiation_id}")
    logger.info(f"merchant_agent_llm_started | run_id={state.get('run_id')}")
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
    
    action = None
    last_error = None
    
    for attempt in range(3):
        try:
            logger.info(f"merchant_agent_llm_calling_api | run_id={state.get('run_id')} | attempt={attempt+1}")
            action = cast(MerchantAgentAction, await llm.ainvoke(messages))
            logger.info(f"merchant_agent_llm_chose_action | action={action.action.value} | run_id={state.get('run_id')}")
            break
        except Exception as e:
            last_error = e
            logger.warning(f"merchant_agent_llm_attempt_failed | run_id={state.get('run_id')} | attempt={attempt+1} | error={e}")
            await asyncio.sleep(1)
            
    if action is None:
        if last_error:
            error_str = str(last_error).lower()
            if "timeout" in error_str or "deadline" in error_str or "504" in error_str:
                error_reason = "LLM_TIMEOUT"
            elif "404" in error_str or "not found" in error_str:
                error_reason = "LLM_MODEL_UNAVAILABLE"
            else:
                error_reason = f"LLM Error: {str(last_error)}"
        else:
            error_reason = "LLM repeatedly failed to return structured output."
            
        logger.error(f"MERCHANT_AGENT_FAILED | negotiation_id={state['intent'].negotiation_id} | exception_type=LLMError | exception_message={error_reason}")
        return {
            "status": "failed",
            "error_reason": error_reason
        }
        
    # Append the reasoning to the message history so LangGraph retains it
    new_msg = AIMessage(content=f"Action: {action.action.value}\nReason: {action.reason}")
    
    logger.info(f"MERCHANT_LLM_COMPLETED | negotiation_id={state['intent'].negotiation_id} | action={action.action.value}")
    logger.info(f"MERCHANT_ACTION_PARSED | negotiation_id={state['intent'].negotiation_id}")
    
    return {
        "current_action": action,
        "messages": [new_msg],
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
        
    if action.action == MerchantActionType.REJECT_PROPOSAL:
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
    
    logger.info(f"MERCHANT_RUNNER_PERSISTING_RESPONSE | negotiation_id={intent.negotiation_id}")
    
    if not action:
        logger.error(f"MERCHANT_AGENT_FAILED | negotiation_id={intent.negotiation_id} | exception_type=ActionError | exception_message=No action to submit")
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
        logger.info(f"MERCHANT_RUNNER_RESPONSE_PERSISTED | negotiation_id={intent.negotiation_id}")
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
        logger.info(f"MERCHANT_RUNNER_RESPONSE_PERSISTED | negotiation_id={intent.negotiation_id}")
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
        logger.info(f"MERCHANT_RUNNER_RESPONSE_PERSISTED | negotiation_id={intent.negotiation_id}")
        return {"status": "completed"}
        
    return {"status": "completed"}


async def request_approval_node(state: MerchantAgentState, config: RunnableConfig) -> dict:
    """
    Creates an ApprovalRequest for HUMAN_APPROVAL_REQUIRED policy decisions.
    Persists the agent's action first so the negotiation state advances and the frontend doesn't hang.
    """
    intent = state["intent"]
    session = config["configurable"]["session"]
    action = state["current_action"]
    
    if action and action.action == MerchantActionType.REJECT_PROPOSAL:
        await append_negotiation_message(
            session=session,
            negotiation_id=intent.negotiation_id,
            sender_type=SenderType.MERCHANT_AGENT,
            sender_id=str(intent.merchant_id),
            message_type=MessageType.REJECT,
            content=action.reason
        )
    elif action and action.action == MerchantActionType.ACCEPT_PROPOSAL:
        await append_negotiation_message(
            session=session,
            negotiation_id=intent.negotiation_id,
            sender_type=SenderType.MERCHANT_AGENT,
            sender_id=str(intent.merchant_id),
            message_type=MessageType.ACCEPT,
            content=action.reason
        )
        agreement = await create_agreement_from_negotiation(session, intent.negotiation_id)
        from app.models.agreement import AgreementStatus
        agreement.status = AgreementStatus.PENDING_APPROVAL.value
        session.add(agreement)
    elif action and action.action == MerchantActionType.COUNTER_PROPOSAL:
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

    await create_approval_request(
        session=session,
        merchant_id=intent.merchant_id,
        approval_type="POLICY_OVERRIDE",
        entity_id=intent.negotiation_id,
        requested_by="Merchant Agent",
        reason="Policy Engine flagged this proposal for human review."
    )
    
    logger.info(f"MERCHANT_RUNNER_RESPONSE_PERSISTED_WITH_APPROVAL | negotiation_id={intent.negotiation_id}")
    return {"status": "completed"}
