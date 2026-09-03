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
    
    # Guard against infinite loops
    if state.get("step_count", 0) >= 15:
        logger.error(f"MERCHANT_AGENT_FAILED | negotiation_id={state['intent'].negotiation_id} | exception_type=StepLimitExceeded")
        return {"status": "failed", "error_reason": "MAX_AGENT_STEPS_EXCEEDED"}

    prompt = get_prompt()
    
    # Extract history and Deadlock Status
    intent = state["intent"]
    history_text = "No previous messages.\n"
    buyer_offers = []
    merchant_offers = []
    
    if intent.negotiation_history:
        lines = []
        for msg in intent.negotiation_history:
            sender = msg.get("sender", "unknown")
            msg_type = msg.get("message_type", "")
            content = msg.get("content", "")
            price = msg.get("unit_price")
            qty = msg.get("quantity")
            price_text = f" | Price: {price}" if price else ""
            qty_text = f" | Qty: {qty}" if qty else ""
            lines.append(f"  [{msg.get('sequence')}] {sender} ({msg_type}){price_text}{qty_text}: {content}")
            
            if msg_type in ("OFFER", "COUNTER_OFFER"):
                if sender == "BUYER_AGENT":
                    buyer_offers.append(msg)
                elif sender == "MERCHANT_AGENT":
                    merchant_offers.append(msg)
                    
        history_text = "\n".join(lines) + "\n"
        
    prev_offer = Decimal(merchant_offers[-1].get("unit_price")) if merchant_offers else None
    buyer_offer = Decimal(buyer_offers[-1].get("unit_price")) if buyer_offers else None
    price_gap = abs(prev_offer - buyer_offer) if prev_offer and buyer_offer else None
    
    repeated = 0
    if prev_offer:
        for m in reversed(merchant_offers):
            if Decimal(m.get("unit_price")) == prev_offer:
                repeated += 1
            else:
                break
                
    status_label = "PROGRESSING"
    if intent.round_count >= 3:
        if repeated >= 2:
            status_label = "DEADLOCKED"
        elif price_gap is not None and len(buyer_offers) >= 2 and len(merchant_offers) >= 2:
            prev_gap = abs(Decimal(merchant_offers[-2].get("unit_price")) - Decimal(buyer_offers[-2].get("unit_price")))
            if prev_gap > 0 and (prev_gap - price_gap) / prev_gap < Decimal("0.05"):
                status_label = "STALLED"
                if intent.round_count >= 6:
                    status_label = "DEADLOCKED"
                    
    state["previous_counteroffer"] = prev_offer
    state["buyer_offer"] = buyer_offer
    state["price_gap"] = price_gap
    state["repeated_offer_count"] = repeated
    state["negotiation_status"] = status_label
    
    # Render the prompt with state data
    messages = prompt.format_messages(
        policy_minimum_price=intent.policy_minimum_price,
        policy_maximum_autonomous_transaction=intent.policy_maximum_autonomous_transaction,
        policy_maximum_discount_percent=intent.policy_maximum_discount_percent,
        product_description=intent.product_description,
        round_count=intent.round_count,
        max_rounds=intent.max_rounds,
        buyer_proposed_quantity=intent.buyer_proposed_quantity,
        buyer_proposed_unit_price=intent.buyer_proposed_unit_price,
        buyer_proposed_discount_percent=intent.buyer_proposed_discount_percent,
        buyer_message=intent.buyer_message or "None",
        negotiation_history=history_text,
        negotiation_status=status_label,
        previous_counteroffer=prev_offer or "None",
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
        "step_count": state.get("step_count", 0) + 1,
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
            
        # Deadlock / Loop Validation
        prev_offer = state.get("previous_counteroffer")
        if prev_offer is not None:
            if unit_price == prev_offer:
                logger.warning(f"validate_action_node | run_id={state.get('run_id')} | OFFER_UNCHANGED: {unit_price}")
                return {
                    "policy_decision": "DENY",
                    "policy_reasons": [f"OFFER_UNCHANGED: Your counteroffer ({unit_price}) is exactly the same as your previous offer. You must change your offer or choose a different action."]
                }
            if unit_price > prev_offer:
                logger.warning(f"validate_action_node | run_id={state.get('run_id')} | OFFER_NOT_IMPROVED: {unit_price} > {prev_offer}")
                return {
                    "policy_decision": "DENY",
                    "policy_reasons": [f"OFFER_NOT_IMPROVED: Your counteroffer ({unit_price}) is HIGHER than your previous offer ({prev_offer}). As a merchant, you cannot increase your offer backwards. You must decrease your offer or choose a different action."]
                }
                
    if action.action == MerchantActionType.CHANGE_STRATEGY:
        return {
            "strategy": action.reason,
            "policy_decision": "DENY",
            "policy_reasons": ["Strategy changed. Please provide your next action based on this new strategy."]
        }
    
    if action.action == MerchantActionType.ABANDON_NEGOTIATION:
        action.action = MerchantActionType.REJECT_PROPOSAL # Map to rejection in the DB

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

# Removed mock create_approval_request, handled in agreement_service
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
        clean_price = str(action.proposed_unit_price).replace(',', '').replace(' ', '').replace('INR', '').replace('$', '')
        clean_discount = str(action.proposed_discount_percent or "0").replace('%', '').replace(' ', '')
        payload = NegotiationMessagePayload(
            product_id=intent.product_id,
            quantity=action.proposed_quantity, # type: ignore
            unit_price=Decimal(clean_price).quantize(Decimal("0.01")), # type: ignore
            discount_percent=Decimal(clean_discount),
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

    logger.info(f"MERCHANT_RUNNER_RESPONSE_PERSISTED_WITH_APPROVAL | negotiation_id={intent.negotiation_id}")
    return {"status": "completed"}
