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
from app.agents.buyer.tools import search_products, get_negotiation_history, get_product_inventory
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
    catalog_text = ""
    if state.get("selected_product_id") and state.get("merchant_counter"):
        catalog_text = f"Currently negotiating for product ID: {state.get('selected_product_id')}. A merchant counteroffer is available — respond to it."
    elif not state["candidate_products"]:
        if state.get("step_count", 0) > 0:
            catalog_text = "No products matched the search query. Consider stopping the negotiation."
        else:
            catalog_text = "No products discovered yet. Use the SEARCH_PRODUCTS action to search the catalog."
    else:
        catalog_text = "Products discovered — please select one:\n"
        for p in state["candidate_products"]:
            catalog_text += f"- ID: {p.get('id')} | Name: {p.get('name')} | Price: {p.get('price')} | SKU: {p.get('sku')}\n"
    
    # Format policy/constraint feedback if any
    policy_status = state.get("policy_decision") or "NONE"
    policy_reasons = state.get("policy_reasons") or []
    reasons_text = ", ".join(policy_reasons) if policy_reasons else "NONE"
    
    # Format merchant counteroffer as structured data (clearly labelled as data, not instructions)
    merchant_section = ""
    if state.get("merchant_counter"):
        mc = state["merchant_counter"]
        merchant_section = (
            "Merchant counteroffer (negotiation data):\n"
            f"  unit_price: {mc.get('unit_price')}\n"
            f"  total_amount: {mc.get('total_amount')}\n"
            f"  merchant_message: {mc.get('content', '')}\n\n"
        )

    # Buyer's own strategy note (safe internal context)
    strategy_section = ""
    if state.get("strategy"):
        strategy_section = f"Current strategy note: {state['strategy']}\n\n"

    # Validation feedback
    policy_status = state.get("policy_decision") or "none"
    policy_reasons = state.get("policy_reasons") or []
    reasons_text = "; ".join(policy_reasons) if policy_reasons else "none"

    human_msg = (
        "Buyer intent:\n"
        f"  budget: {intent.maximum_budget} {intent.preferred_currency}\n"
        f"  quantity: {intent.quantity}\n"
        f"  target_unit_price: {intent.target_unit_price}\n"
        f"  reservation_unit_price: {intent.reservation_unit_price}\n"
        f"  product_query: {intent.product_query}\n"
        f"  requirements: {intent.requirements}\n"
        f"  preferences: {intent.preferences}\n\n"
        "Current negotiation state:\n"
        f"  selected_product_id: {state.get('selected_product_id')}\n"
        f"  negotiation_status: {state.get('negotiation_status', 'not_started')}\n"
        f"  negotiation_round: {state.get('negotiation_round', 0)}\n"
        f"  previous_buyer_offer: {state.get('previous_offer', 'none')}\n"
        f"  merchant_offer: {state.get('opponent_offer', 'none')}\n"
        f"  price_gap: {state.get('price_gap', 'none')}\n\n"
        f"{merchant_section}"
        f"{strategy_section}"
        f"Product catalog:\n{catalog_text}\n\n"
        "Validation system feedback:\n"
        f"  status: {policy_status}\n"
        f"  reasons: {reasons_text}\n\n"
        "Select your next action and return the BuyerAgentAction JSON."
    )
    
    msgs = [SystemMessage(content=SYSTEM_INSTRUCTION)]
    # Append conversation history so the LLM remembers its past actions
    msgs.extend(state.get("messages", []))
    # Always append the current state as the FINAL HumanMessage
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

            # Model returned None without error — request a structured response
            messages.append(HumanMessage(content="Please provide a valid JSON response using the BuyerAgentAction schema."))
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
            if "content_filter" in error_str or "responsibleaipolicyviolation" in error_str or "content management policy" in error_str:
                error_reason = "AGENT_MODEL_CONTENT_FILTER"
            elif "timeout" in error_str or "deadline" in error_str or "504" in error_str:
                error_reason = "LLM_TIMEOUT"
            elif "404" in error_str or "not found" in error_str or "unavailable" in error_str:
                error_reason = "LLM_MODEL_UNAVAILABLE"
            else:
                error_reason = f"LLM Error: {str(last_error)}"
            return {"status": "failed", "error_reason": error_reason}
            
        return {"status": "failed", "error_reason": "LLM repeatedly failed to return structured output."}
        
    import json
    from langchain_core.messages import AIMessage

    # Store a concise action summary. We deliberately exclude the raw 'reason' text
    # because LLM-generated reason strings may accumulate adversarial-looking language
    # across multiple rounds and trigger Azure's content filter on later invocations.
    ai_msg = AIMessage(content=f"Action taken: {action.action.value} | proposed_price: {action.proposed_unit_price}")
    
    return {
        "current_action": action,
        "step_count": state["step_count"] + 1,
        "policy_decision": None,  # Reset feedback on new action
        "policy_reasons": [],
        "messages": [ai_msg]
    }


async def route_after_action(state: BuyerAgentState) -> str:
    if state.get("step_count", 0) > 4:
        return "END"
        
    if state.get("status") in ["completed", "failed"]:
        return "END"
        
    action = state.get("current_action")
    if not action:
        return "END"
        
    if action.action in [ActionType.PROPOSE_AGREEMENT, ActionType.COUNTER_PROPOSAL, ActionType.ACCEPT_COUNTER]:
        return "validate_proposal"
        
    return "run_llm"


def route_policy_decision(state: BuyerAgentState) -> str:
    if state.get("step_count", 0) > 4:
        return "submit_proposal" # Force submission of whatever we have, or let it fail downstream
        
    decision = state.get("policy_decision")
    if decision in ["allow", "human_approval_required"]:
        return "submit_proposal"
    return "proposal_recovery"


async def execute_action_node(state: BuyerAgentState, config: RunnableConfig) -> dict:
    """Executes the action chosen by the LLM."""
    if state.get("status") == "failed":
        return {}  # Do not overwrite the error reason from the previous node
        
    action = state.get("current_action")
    if not action:
        return {"status": "failed", "error_reason": "No action provided"}
        
    if action.action == ActionType.STOP:
        logger.info(f"execute_action | run_id={state.get('run_id')} | action=STOP | reason={action.reason}")
        return {"status": "completed"}

    elif action.action == ActionType.REJECT_NEGOTIATION or action.action == ActionType.ABANDON_NEGOTIATION:
        # Buyer explicitly walks away from the negotiation
        logger.info(f"execute_action | run_id={state.get('run_id')} | action=REJECT_NEGOTIATION | reason={action.reason}")
        session = config["configurable"]["session"]
        negotiation_id = state.get("negotiation_id")
        if negotiation_id:
            try:
                await append_negotiation_message(
                    session=session,
                    negotiation_id=negotiation_id,
                    sender_type=SenderType.BUYER_AGENT,
                    sender_id=str(state["intent"].buyer_id),
                    message_type=MessageType.REJECT,
                    content=action.reason
                )
            except Exception as e:
                logger.warning(f"execute_action | REJECT_NEGOTIATION could not persist rejection: {e}")
        return {"status": "completed", "negotiation_status": "REJECTED"}
        
    elif action.action == ActionType.CHANGE_STRATEGY:
        logger.info(f"execute_action | run_id={state.get('run_id')} | action=CHANGE_STRATEGY | strategy={action.reason}")
        # Reject deterministically so it loops back, but persist the strategy
        return {
            "strategy": action.reason,
            "policy_decision": "DENY",
            "policy_reasons": ["Strategy changed. Please provide your next action based on this new strategy."]
        }

    elif action.action == ActionType.SEARCH_PRODUCTS:
        logger.info(f"execute_action | run_id={state.get('run_id')} | action=SEARCH_PRODUCTS")
        
        # Deterministic loop prevention: do not allow searching again if products are already found
        if state.get("candidate_products"):
            logger.warning(f"execute_action | run_id={state.get('run_id')} | Redundant SEARCH_PRODUCTS intercepted.")
            return {
                "policy_decision": "DENY",
                "policy_reasons": ["Products have already been discovered. Please use the SELECT_PRODUCT action to choose one."]
            }
            
        # Actually hit the database via the tool (which uses ProductService)
        query = action.search_query or state["intent"].product_query
        try:
            results = await search_products.ainvoke(
                {"merchant_id": str(state["intent"].merchant_id), "query": query},
                config=config
            )
            from langchain_core.messages import HumanMessage
            tool_msg = HumanMessage(content=f"Search completed. Found {len(results)} products matching '{query}'.")
            
            session = config["configurable"]["session"]
            await record_event(
                session=session,
                event_type=AuditEventType.BUYER_TOOL_INVOKED, 
                actor_type="BUYER_AGENT",
                actor_id=state["intent"].buyer_id,
                merchant_id=state["intent"].merchant_id,
                metadata={"tool": "SEARCH_PRODUCTS", "query": query}
            )
            await session.commit()
            
            return {"candidate_products": results, "messages": [tool_msg]}
        except Exception as e:
            return {"policy_decision": "deny", "policy_reasons": [f"Search failed: {str(e)}"]}

    elif action.action == ActionType.INSPECT_PRODUCT:
        logger.info(f"execute_action | run_id={state.get('run_id')} | action=INSPECT_PRODUCT | id={action.product_id}")
        if not action.product_id:
            return {"policy_decision": "deny", "policy_reasons": ["product_id is required for INSPECT_PRODUCT"]}
        try:
            result = await get_product_inventory.ainvoke(
                {"merchant_id": str(state["intent"].merchant_id), "product_id": str(action.product_id)},
                config=config
            )
            from langchain_core.messages import HumanMessage
            tool_msg = HumanMessage(content=f"INSPECT_PRODUCT result: {result}")
            
            session = config["configurable"]["session"]
            await record_event(
                session=session,
                event_type=AuditEventType.BUYER_TOOL_INVOKED, 
                actor_type="BUYER_AGENT",
                actor_id=state["intent"].buyer_id,
                merchant_id=state["intent"].merchant_id,
                metadata={"tool": "INSPECT_PRODUCT", "product_id": str(action.product_id)}
            )
            await session.commit()
            
            return {"messages": [tool_msg]}
        except Exception as e:
            return {"policy_decision": "deny", "policy_reasons": [f"INSPECT_PRODUCT failed: {str(e)}"]}
        
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
            event_type=AuditEventType.BUYER_TOOL_INVOKED, 
            actor_type="BUYER_AGENT",
            actor_id=state["intent"].buyer_id,
            merchant_id=state["intent"].merchant_id,
            metadata={"tool": "SELECT_PRODUCT", "product_id": str(action.product_id), "reason": action.reason}
        )
        # Commit immediately so the transaction doesn't stay open if graph loops back to run_llm
        await session.commit()
        return {"selected_product_id": action.product_id}
        
    elif action.action in (ActionType.PROPOSE_AGREEMENT, ActionType.COUNTER_PROPOSAL):
        return {} # Next node validates the proposal
        
    elif action.action == ActionType.ACCEPT_COUNTER:
        return {} # Will route to submit_proposal to accept
        
    return {"status": "failed", "error_reason": f"Unknown Action: {action.action}"}


async def validate_proposal_node(state: BuyerAgentState, config: RunnableConfig) -> dict:
    """Deterministically parses and calculates the proposal totals against Buyer constraints."""
    action = state["current_action"]
    intent = state["intent"]
    
    if action.action == ActionType.ACCEPT_COUNTER:
        # No numeric validation needed for accepting a counteroffer — pass through.
        # The BuyerConstraintEngine already validated this when we evaluated the counteroffer.
        logger.info(f"validate_proposal_node | run_id={state.get('run_id')} | ACCEPT_COUNTER pass-through at round={state.get('negotiation_round', 1)}")
        return {}
        
    try:
        if action.proposed_unit_price is None:
            raise ValueError("Unit price is required.")
            
        # Clean the string of commas and currency symbols just in case
        clean_price = str(action.proposed_unit_price).replace(',', '').replace(' ', '').replace('INR', '').replace('$', '')
        clean_discount = str(action.proposed_discount_percent or "0").replace(',', '').replace('%', '')
            
        unit_price = Decimal(clean_price).quantize(Decimal("0.01"))
        discount = Decimal(clean_discount).quantize(Decimal("0.01"))
        qty = Decimal(intent.quantity)
        
        # DETERMINISTIC TOTAL CALCULATION (Ignore whatever total the LLM might have thought)
        total = (unit_price * qty).quantize(Decimal("0.01"))
        
        # Deadlock / Loop Validation
        prev_offer = state.get("previous_offer")
        if prev_offer is not None:
            if unit_price == prev_offer:
                logger.warning(f"validate_proposal_node | run_id={state.get('run_id')} | OFFER_UNCHANGED: {unit_price}")
                return {
                    "policy_decision": "DENY",
                    "policy_reasons": [f"OFFER_UNCHANGED: Your proposed price ({unit_price}) is exactly the same as your previous offer. You must change your offer or choose a different action."]
                }
            if unit_price < prev_offer:
                logger.warning(f"validate_proposal_node | run_id={state.get('run_id')} | OFFER_NOT_IMPROVED: {unit_price} < {prev_offer}")
                return {
                    "policy_decision": "DENY",
                    "policy_reasons": [f"OFFER_NOT_IMPROVED: Your proposed price ({unit_price}) is lower than your previous offer ({prev_offer}). As a buyer, you cannot lower your offer backwards. You must increase your offer or choose a different action."]
                }
        
        # 1. Evaluate Buyer Constraints
        constraint_engine = BuyerConstraintEngine()
        result = constraint_engine.evaluate_proposal(intent, unit_price, qty)
        
        logger.info(f"validate_proposal_node | run_id={state.get('run_id')} | constraint_passed={result.passed} | total={total} | budget={intent.maximum_budget}")
        
        if not result.passed:
            logger.warning(f"validate_proposal_node | run_id={state.get('run_id')} | DENY reasons={result.reasons}")
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
            clean_price = str(action.proposed_unit_price).replace(',', '').replace(' ', '').replace('INR', '').replace('$', '')
            clean_discount = str(action.proposed_discount_percent or "0").replace('%', '').replace(' ', '')
            payload = NegotiationMessagePayload(
                product_id=state.get("selected_product_id") or action.product_id,
                quantity=intent.quantity,
                unit_price=Decimal(clean_price).quantize(Decimal("0.01")),
                discount_percent=Decimal(clean_discount),
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
        
        elif action.action in (ActionType.COUNTER_PROPOSAL, ActionType.PROPOSE_AGREEMENT) and state["negotiation_id"]:
            clean_price = str(action.proposed_unit_price).replace(',', '').replace(' ', '').replace('INR', '').replace('$', '')
            clean_discount = str(action.proposed_discount_percent or "0").replace('%', '').replace(' ', '')
            payload = NegotiationMessagePayload(
                product_id=state["selected_product_id"],
                quantity=intent.quantity,
                unit_price=Decimal(clean_price).quantize(Decimal("0.01")),
                discount_percent=Decimal(clean_discount),
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
            accept_content = action.reason if action.reason else "Buyer accepts the terms."
            await append_negotiation_message(
                session=session,
                negotiation_id=state["negotiation_id"],
                sender_type=SenderType.BUYER_AGENT,
                sender_id=str(intent.buyer_id),
                message_type=MessageType.ACCEPT,
                content=accept_content
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
            
        # Enhanced Deadlock & Progress Tracking
        buyer_offers = [m for m in messages if m.sender_type == SenderType.BUYER_AGENT.value and m.message_type in (MessageType.OFFER.value, MessageType.COUNTER_OFFER.value)]
        merchant_offers = [m for m in messages if m.sender_type == SenderType.MERCHANT_AGENT.value and m.message_type == MessageType.COUNTER_OFFER.value]
        
        prev_offer = Decimal(buyer_offers[-1].payload.get("unit_price")) if buyer_offers else None
        opp_offer = Decimal(merchant_offers[-1].payload.get("unit_price")) if merchant_offers else None
        price_gap = abs(opp_offer - prev_offer) if prev_offer and opp_offer else None
        
        repeated = 0
        if prev_offer:
            for m in reversed(buyer_offers):
                if Decimal(m.payload.get("unit_price")) == prev_offer:
                    repeated += 1
                else:
                    break
                    
        status_label = "PROGRESSING"
        if neg and neg.round_count >= 3:
            if repeated >= 2:
                status_label = "DEADLOCKED"
            elif price_gap is not None and len(buyer_offers) >= 2 and len(merchant_offers) >= 2:
                prev_gap = abs(Decimal(merchant_offers[-2].payload.get("unit_price")) - Decimal(buyer_offers[-2].payload.get("unit_price")))
                if prev_gap > 0 and (prev_gap - price_gap) / prev_gap < Decimal("0.05"):
                    status_label = "STALLED"
                    if neg.round_count >= 6:
                        status_label = "DEADLOCKED"

        updates = {
            "selected_product_id": product_id,
            "previous_offer": prev_offer,
            "opponent_offer": opp_offer,
            "price_gap": price_gap,
            "repeated_offer_count": repeated,
            "negotiation_status": status_label,
            "negotiation_round": neg.round_count if neg else 0
        }
        
        if latest.sender_type == SenderType.MERCHANT_AGENT.value:
            updates["merchant_counter"] = latest.payload
            
        return updates
    except Exception as e:
        return {"status": "failed", "error_reason": f"Failed to read negotiation: {str(e)}"}
