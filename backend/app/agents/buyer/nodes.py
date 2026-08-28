"""
NEXORA — Buyer Agent Nodes

Deterministic functions that execute the LangGraph state machine.
Enforces the "LLMs PROPOSE. DETERMINISTIC SYSTEMS DECIDE." principle.
"""
import uuid
import time
import asyncio
import logging
from decimal import Decimal, InvalidOperation
from typing import Any

logger = logging.getLogger(__name__)

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from app.llm import get_llm
from app.agents.buyer.prompts import SYSTEM_INSTRUCTION
from app.agents.buyer.schemas import ActionType, BuyerAgentAction, BuyerAgentState
from app.agents.buyer.constraints import BuyerConstraintEngine
from app.agents.buyer.tools import search_products
from app.services.negotiation_service import (
    create_negotiation_with_proposal,
    append_negotiation_message,
    get_negotiation,
    get_negotiation_messages
)
from app.models.negotiation_message import SenderType, MessageType
from app.schemas.negotiation import NegotiationMessagePayload
from app.services.audit_service import record_event, AuditEventType


def format_state_for_llm(state: BuyerAgentState) -> list:
    """Format the runtime state into messages for the LLM."""
    intent = state["intent"]
    
    # Safely format product catalog for context
    catalog_text = "Available Products:\n"
    if not state["candidate_products"]:
        if state.get("step_count", 0) > 0:
            catalog_text += "No products were found matching your query! You MUST take the STOP action since there is nothing to buy.\n"
        else:
            catalog_text += "No products discovered yet. Take SEARCH_PRODUCTS action to search the catalog.\n"
    else:
        catalog_text += "CRITICAL INSTRUCTION: Products HAVE been found! You MUST now take the SELECT_PRODUCT action to choose one of the IDs below.\n"
        for p in state["candidate_products"]:
            catalog_text += f"- ID: {p.get('id')} | Name: {p.get('name')} | Price: {p.get('price')} | SKU: {p.get('sku')} | Desc: {p.get('description')}\n"
    
    # Format policy/constraint feedback if any
    policy_status = state.get("policy_decision") or "NONE"
    policy_reasons = state.get("policy_reasons") or []
    reasons_text = ", ".join(policy_reasons) if policy_reasons else "NONE"
    
    # Format negotiation history
    merchant_feedback = ""
    if state.get("merchant_counter"):
        mc = state["merchant_counter"]
        merchant_feedback = (
            f"--- MERCHANT COUNTEROFFER RECEIVED ---\n"
            f"Merchant Price: {mc.get('unit_price')}\n"
            f"Merchant Total: {mc.get('total_amount')}\n"
            f"Merchant Message: {mc.get('content', 'No additional message')}\n"
            f"--------------------------------------\n\n"
        )
    
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
        f"Negotiation Status: {state.get('negotiation_status', 'Not Started')}\n"
        f"Negotiation Round: {state.get('negotiation_round', 0)}\n"
        f"---------------------\n\n"
        f"{merchant_feedback}"
        f"--- DETERMINISTIC FEEDBACK ---\n"
        f"Status: {policy_status}\n"
        f"Reasons: {reasons_text}\n"
        f"-----------------------\n\n"
        f"{catalog_text}\n\n"
        f"Action: What will you do next? (Must respond with valid JSON matching BuyerAgentAction)"
    )
    
    msgs = [SystemMessage(content=SYSTEM_INSTRUCTION)]
    # Append conversation history so the LLM remembers its past actions
    msgs.extend(state.get("messages", []))
    # Always append the current state as the FINAL HumanMessage to ensure valid Gemini turn order
    msgs.append(HumanMessage(content=human_msg))
    
    return msgs


async def run_llm_node(state: BuyerAgentState, config: RunnableConfig) -> dict:
    """Invokes the LLM to get the next BuyerAgentAction."""
    if state["step_count"] >= 15:
        return {"status": "failed", "error_reason": "MAX_AGENT_STEPS_EXCEEDED"}
    
    # We are about to make a slow network call. Let's commit any pending transactions.
    session = config["configurable"]["session"]
    await session.commit()
        
    messages = format_state_for_llm(state)
    llm = get_llm().with_structured_output(BuyerAgentAction)
    
    action = None
    
    logger.info(f"buyer_agent_llm_started | run_id={state.get('run_id')} | message_count={len(messages)}")
    start_time = time.time()
    
    last_error = None
    
    for attempt in range(3):
        attempt_start = time.time()
        try:
            action = await llm.ainvoke(messages)
            attempt_elapsed = time.time() - attempt_start
            
            logger.info(f"buyer_agent_llm_attempt_finished | run_id={state.get('run_id')} | attempt={attempt+1} | duration={attempt_elapsed:.2f}s")
            
            if action is not None:
                logger.info(f"buyer_agent_llm_chose_action | run_id={state.get('run_id')} | action={action.action} | product_id={action.product_id}")
                break
            
            # If the model fails to use the tool, add a strong reminder
            messages.append(HumanMessage(content="You failed to output the structured JSON. You MUST respond ONLY by calling the provided tool schema for BuyerAgentAction."))
        except Exception as e:
            last_error = e
            attempt_elapsed = time.time() - attempt_start
            logger.warning(f"buyer_agent_llm_attempt_failed | run_id={state.get('run_id')} | attempt={attempt+1} | duration={attempt_elapsed:.2f}s | error={e}")
            await asyncio.sleep(1) # Backoff before retry
        
    total_elapsed = time.time() - start_time
    logger.info(f"buyer_agent_llm_completed | run_id={state.get('run_id')} | total_duration={total_elapsed:.2f}s")
        
    if action is None:
        if last_error:
            logger.error(f"buyer_agent_llm_failed | run_id={state.get('run_id')} | total_duration={total_elapsed:.2f}s | error={last_error}")
            error_str = str(last_error).lower()
            if "timeout" in error_str or "deadline" in error_str or "504" in error_str:
                error_reason = "LLM_TIMEOUT"
            elif "404" in error_str or "not found" in error_str or "unavailable" in error_str:
                error_reason = "LLM_MODEL_UNAVAILABLE"
            else:
                error_reason = f"LLM Error: {str(last_error)}"
            return {"status": "failed", "error_reason": error_reason}
            
        return {"status": "failed", "error_reason": "LLM repeatedly failed to return structured output."}
        
    import json
    from langchain_core.messages import AIMessage
    
    # Save the chosen action to history so the LLM remembers it next time
    ai_msg = AIMessage(content=f"I took action: {action.action.value} with args: {json.dumps(action.model_dump())}")
    
    return {
        "current_action": action,
        "step_count": state["step_count"] + 1,
        "policy_decision": None,  # Reset feedback on new action
        "policy_reasons": [],
        "messages": [ai_msg]
    }


async def execute_action_node(state: BuyerAgentState, config: RunnableConfig) -> dict:
    """Executes the action chosen by the LLM."""
    if state.get("status") == "failed":
        return {}  # Do not overwrite the error reason from the previous node
        
    action = state.get("current_action")
    if not action:
        return {"status": "failed", "error_reason": "No action provided"}
        
    if action.action == ActionType.STOP:
        return {"status": "completed"}
        
    elif action.action == ActionType.SEARCH_PRODUCTS:
        logger.info(f"execute_action | run_id={state.get('run_id')} | action=SEARCH_PRODUCTS")
        
        # Deterministic loop prevention: do not allow searching again if products are already found
        if state.get("candidate_products"):
            logger.warning(f"execute_action | run_id={state.get('run_id')} | Redundant SEARCH_PRODUCTS intercepted.")
            return {
                "policy_decision": "DENY", 
                "policy_reasons": ["You already discovered products. You MUST choose one using the SELECT_PRODUCT action."]
            }
            
        # Actually hit the database via the tool (which uses ProductService)
        query = action.search_query or state["intent"].product_query
        try:
            # We call the async tool directly passing the config
            results = await search_products.ainvoke(
                {"merchant_id": str(state["intent"].merchant_id), "query": query},
                config=config
            )
            from langchain_core.messages import HumanMessage
            tool_msg = HumanMessage(content=f"Search executed. Found {len(results)} products.")
            return {"candidate_products": results, "messages": [tool_msg]}
        except Exception as e:
            return {"policy_decision": "deny", "policy_reasons": [f"Search failed: {str(e)}"]}
        
    elif action.action == ActionType.SELECT_PRODUCT:
        logger.info(f"execute_action | run_id={state.get('run_id')} | action=SELECT_PRODUCT | id={action.product_id}")
        if not action.product_id:
            return {"policy_decision": "deny", "policy_reasons": ["product_id is required for SELECT_PRODUCT"]}
        
        found = any(str(p.get("id")) == str(action.product_id) for p in state["candidate_products"])
        if not found:
            return {"policy_decision": "deny", "policy_reasons": ["Invalid product_id selected. Discovered products do not contain this ID."]}
            
        # Log selection via audit service
        session = config["configurable"]["session"]
        await record_event(
            session=session,
            event_type="PRODUCT_SELECTED", 
            actor_type="BUYER_AGENT",
            actor_id=str(state["intent"].buyer_id),
            merchant_id=state["intent"].merchant_id,
            metadata={"product_selected": str(action.product_id)}
        )
        # Commit immediately so the transaction doesn't stay open if graph loops back to run_llm
        await session.commit()
        return {"selected_product_id": action.product_id}
        
    elif action.action in (ActionType.PROPOSE_AGREEMENT, ActionType.COUNTER_PROPOSAL):
        return {} # Next node validates the proposal
        
    elif action.action == ActionType.ACCEPT_COUNTER:
        return {} # Will route to submit_proposal to accept
        
    return {"status": "failed", "error_reason": "Unknown Action"}


async def validate_proposal_node(state: BuyerAgentState, config: RunnableConfig) -> dict:
    """Deterministically parses and calculates the proposal totals against Buyer constraints."""
    action = state["current_action"]
    intent = state["intent"]
    
    # ---------------------------------------------------------
    # DEMO NEGOTIATION STRATEGY: Enforce minimum rounds
    # ---------------------------------------------------------
    from app.config import settings
    logger.error(f"DEBUG_BUYER: action={action.action}, current_round={state.get('negotiation_round', 1)}, MIN_ROUNDS={settings.NEGOTIATION_DEMO_MIN_ROUNDS}")
    if action.action == ActionType.ACCEPT_COUNTER:
        current_round = state.get("negotiation_round", 1)
        if current_round < settings.NEGOTIATION_DEMO_MIN_ROUNDS:
            logger.error("DEBUG_BUYER: DENYING ACCEPT_COUNTER due to demo strategy")
            return {
                "policy_decision": "DENY",
                "policy_reasons": [
                    f"Demo Strategy Active: You attempted to ACCEPT_COUNTER on round {current_round}. "
                    f"The minimum required rounds is {settings.NEGOTIATION_DEMO_MIN_ROUNDS}. "
                    "You MUST generate a COUNTER_PROPOSAL instead to continue the negotiation."
                ]
            }
        logger.error("DEBUG_BUYER: ALLOWING ACCEPT_COUNTER")
        return {} # Safe to pass through, no numeric validation needed for accepting
        
    try:
        if action.proposed_unit_price is None:
            raise ValueError("Unit price is required.")
            
        unit_price = Decimal(action.proposed_unit_price).quantize(Decimal("0.01"))
        discount = Decimal(action.proposed_discount_percent or "0").quantize(Decimal("0.01"))
        qty = Decimal(intent.quantity)
        
        # DETERMINISTIC TOTAL CALCULATION (Ignore whatever total the LLM might have thought)
        total = (unit_price * qty).quantize(Decimal("0.01"))
        
        # 1. Evaluate Buyer Constraints
        constraint_engine = BuyerConstraintEngine()
        result = constraint_engine.evaluate_proposal(intent, unit_price, qty)
        
        logger.error(f"DEBUG_BUYER: Constraint result={result.passed}, reasons={result.reasons}, total={total}, budget={intent.maximum_budget}")
        
        if not result.passed:
            logger.error(f"DEBUG_BUYER: DENYING due to constraints: {result.reasons}")
            return {
                "policy_decision": "DENY", 
                "policy_reasons": result.reasons
            }
            
    except (InvalidOperation, ValueError, TypeError) as e:
        return {
            "policy_decision": "DENY", 
            "policy_reasons": [f"Deterministic validation failed: Invalid numeric formats. {str(e)}"]
        }
            
    return {"deterministic_total": total}


from app.services.agreement_service import create_agreement_from_negotiation

async def submit_proposal_node(state: BuyerAgentState, config: RunnableConfig) -> dict:
    """Submits the validated proposal to the NegotiationService."""
    action = state["current_action"]
    intent = state["intent"]
    session = config["configurable"]["session"]
    
    try:
        if action.action == ActionType.PROPOSE_AGREEMENT and not state["negotiation_id"]:
            payload = NegotiationMessagePayload(
                product_id=state.get("selected_product_id") or action.product_id,
                quantity=intent.quantity,
                unit_price=Decimal(action.proposed_unit_price),
                discount_percent=Decimal(action.proposed_discount_percent or "0"),
                total_amount=state["deterministic_total"],
                currency=intent.preferred_currency
            )
            # Initial offer
            negotiation = await create_negotiation_with_proposal(
                session=session,
                buyer_id=intent.buyer_id,
                merchant_id=intent.merchant_id,
                product_id=state.get("selected_product_id") or action.product_id,
                payload=payload,
                content=action.reason
            )
            return {
                "negotiation_id": negotiation.id,
                "negotiation_status": "OFFER",
                "negotiation_round": 1,
                "status": "completed"
            }
        
        elif action.action == ActionType.COUNTER_PROPOSAL and state["negotiation_id"]:
            payload = NegotiationMessagePayload(
                product_id=state["selected_product_id"],
                quantity=intent.quantity,
                unit_price=Decimal(action.proposed_unit_price),
                discount_percent=Decimal(action.proposed_discount_percent or "0"),
                total_amount=state["deterministic_total"],
                currency=intent.preferred_currency
            )
            # Counter offer
            await append_negotiation_message(
                session=session,
                negotiation_id=state["negotiation_id"],
                sender_type=SenderType.BUYER_AGENT,
                sender_id=str(intent.buyer_id),
                message_type=MessageType.COUNTER_OFFER,
                content=action.reason,
                payload=payload
            )
            return {"negotiation_status": "COUNTER_OFFER", "status": "completed"}
            
        elif action.action == ActionType.ACCEPT_COUNTER and state["negotiation_id"]:
            # Accept merchant's counter
            await append_negotiation_message(
                session=session,
                negotiation_id=state["negotiation_id"],
                sender_type=SenderType.BUYER_AGENT,
                sender_id=str(intent.buyer_id),
                message_type=MessageType.ACCEPT,
                content="Buyer accepts the terms."
            )
            
            # Handoff to Agreement Service
            await create_agreement_from_negotiation(session, state["negotiation_id"])
            
            return {"negotiation_status": "ACCEPTED", "status": "completed"}
            
    except Exception as e:
        return {"status": "failed", "error_reason": f"Failed to submit proposal to DB: {str(e)}"}
        
    return {"status": "failed", "error_reason": "Invalid negotiation state for submission."}


async def read_negotiation_state_node(state: BuyerAgentState, config: RunnableConfig) -> dict:
    """Reads the latest message from the Merchant."""
    session = config["configurable"]["session"]
    negotiation_id = state.get("negotiation_id")
    if not negotiation_id:
        return {}
        
    try:
        messages = await get_negotiation_messages(session, negotiation_id)
        if not messages:
            return {}
            
        latest = messages[-1]
        
        # We need the product ID for any subsequent counter-offers/accepts
        from app.services.negotiation_service import get_negotiation
        neg = await get_negotiation(session, negotiation_id)
        product_id = neg.product_id if neg else None
        
        # If the latest is from the merchant, put it in state for the LLM
        if latest.sender_type == SenderType.MERCHANT_AGENT.value:
            return {
                "selected_product_id": product_id,
                "merchant_counter": latest.payload,
                "negotiation_status": latest.message_type,
                "negotiation_round": neg.round_count if neg else 0
            }
            
        return {"selected_product_id": product_id}
    except Exception as e:
        return {"status": "failed", "error_reason": f"Failed to read negotiation: {str(e)}"}
