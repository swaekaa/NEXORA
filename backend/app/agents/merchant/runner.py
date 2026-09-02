"""
NEXORA — Merchant Agent Runner

Orchestrates the Merchant Agent.
Loads context from NegotiationService and ProductService.
"""
import uuid
import logging
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.runnables import RunnableConfig

from app.agents.merchant.graph import build_merchant_agent_graph
from app.agents.merchant.schemas import MerchantIntent, MerchantAgentState
from app.services.negotiation_service import get_negotiation, get_negotiation_messages
from app.services.policy_service import list_policies
from app.services.product_service import get_product
from app.models.negotiation import NegotiationState
from app.models.negotiation_message import MessageType, SenderType

logger = logging.getLogger(__name__)

async def run_merchant_agent(session: AsyncSession, negotiation_id: uuid.UUID) -> MerchantAgentState | dict:
    """
    Executes the merchant agent workflow for a given negotiation.
    """
    import time
    logger.info(f"MERCHANT_RUNNER_ENTERED | negotiation_id={negotiation_id}")
    logger.info(f"MERCHANT_RUNNER_LOADING_NEGOTIATION | negotiation_id={negotiation_id}")
    # 1. Load Negotiation
    negotiation = await get_negotiation(session, negotiation_id)
    if not negotiation:
        return {"status": "failed", "error_reason": "Negotiation not found"}
        
    if negotiation.state in NegotiationState.TERMINAL_STATES:
        logger.error(f"MERCHANT_AGENT_FAILED | negotiation_id={negotiation_id} | exception_type=StateError | exception_message=Terminal state {negotiation.state}")
        return {"status": "failed", "error_reason": f"Negotiation is in terminal state: {negotiation.state}"}
        
    logger.info(f"MERCHANT_RUNNER_NEGOTIATION_LOADED | negotiation_id={negotiation_id}")
    logger.info(f"MERCHANT_RUNNER_LOADING_MESSAGES | negotiation_id={negotiation_id}")
    # 2. Load Messages
    messages = await get_negotiation_messages(session, negotiation_id)
    if not messages:
        logger.error(f"MERCHANT_AGENT_FAILED | negotiation_id={negotiation_id} | exception_type=MessageError | exception_message=No messages")
        return {"status": "failed", "error_reason": "No messages in negotiation"}
        
    logger.info(f"MERCHANT_RUNNER_MESSAGES_LOADED | negotiation_id={negotiation_id} | message_count={len(messages)}")
    latest_message = messages[-1]
    
    # Merchant Agent only runs when it's the Buyer's turn that just finished
    if latest_message.sender_type != SenderType.BUYER_AGENT.value:
        return {"status": "completed", "error_reason": "Not the Merchant's turn"}
        
    if latest_message.message_type not in (MessageType.OFFER.value, MessageType.COUNTER_OFFER.value):
        return {"status": "completed", "error_reason": "Nothing to evaluate (Buyer did not make an offer)"}
        
    payload = latest_message.payload
    if not payload:
        return {"status": "failed", "error_reason": "Buyer message missing payload"}
        
    # 3. Load Product & Policy
    product = await get_product(session, negotiation.merchant_id, negotiation.product_id)
    if not product:
        return {"status": "failed", "error_reason": "Product not found"}
        
    policies = await list_policies(session, negotiation.merchant_id)
    active_policy = next((p for p in policies if p.is_active), None)
    if not active_policy:
        return {"status": "failed", "error_reason": "No active policy found for merchant"}
        
    # 4. Construct full negotiation history for context
    history_for_intent = []
    for msg in messages:
        history_for_intent.append({
            "sequence": msg.sequence_number,
            "sender": msg.sender_type,
            "message_type": msg.message_type,
            "content": msg.content or "",
            "unit_price": msg.payload.get("unit_price") if msg.payload else None,
            "quantity": msg.payload.get("quantity") if msg.payload else None,
            "total_amount": msg.payload.get("total_amount") if msg.payload else None,
        })
    
    # 5. Construct Intent
    intent = MerchantIntent(
        negotiation_id=negotiation_id,
        buyer_id=negotiation.buyer_id,
        merchant_id=negotiation.merchant_id,
        product_id=negotiation.product_id,
        
        buyer_proposed_quantity=payload.get("quantity", 0),
        buyer_proposed_unit_price=Decimal(payload.get("unit_price", "0")),
        buyer_proposed_discount_percent=Decimal(payload.get("discount_percent", "0")),
        
        policy_id=active_policy.id,
        policy_minimum_price=active_policy.minimum_price,
        policy_maximum_discount_percent=active_policy.maximum_discount_percent,
        policy_maximum_autonomous_transaction=active_policy.maximum_autonomous_transaction,
        policy_requires_human_approval=active_policy.human_approval_required,
        
        currency="INR", # Hardcoded for now
        
        round_count=negotiation.round_count,
        max_rounds=negotiation.max_rounds,
        
        product_description=f"{product.name} - {product.description} (SKU: {product.sku})",
        buyer_message=latest_message.content,
        negotiation_history=history_for_intent
    )
    
    # 5. Configure Graph Environment
    config: RunnableConfig = {
        "configurable": {
            "session": session,
        }
    }
    
    initial_state: MerchantAgentState = {
        "run_id": str(uuid.uuid4()),
        "intent": intent,
        "step_count": 0,
        "status": "in_progress",
        "error_reason": None,
        "proposal_revisions": 0,
        
        # Structured Negotiation State
        "previous_counteroffer": None,
        "buyer_offer": None,
        "price_gap": None,
        "repeated_offer_count": 0,
        "negotiation_status": None,
        "strategy": None,
        
        "current_action": None,
        "deterministic_total": None,
        "policy_decision": None,
        "policy_reasons": None,
        "messages": []
    }
    
    graph = build_merchant_agent_graph()
    
    # Commit the transaction to release the DB connection before long-running graph
    await session.commit()
    
    logger.info(f"MERCHANT_RUNNER_INVOKING_GRAPH | negotiation_id={negotiation_id}")
    start_time = time.time()
    try:
        final_state = await graph.ainvoke(initial_state, config=config)
        duration = time.time() - start_time
        logger.info(f"MERCHANT_RUNNER_GRAPH_RETURNED | negotiation_id={negotiation_id} | duration={duration:.2f}s")
        logger.info(f"MERCHANT_RUNNER_EXITED | negotiation_id={negotiation_id}")
        return final_state
    except Exception as e:
        logger.error(f"Merchant agent execution failed: {str(e)}", exc_info=True)
        from app.database.connection import AsyncSessionLocal
        from app.services.audit_service import record_event
        from app.schemas.audit import AuditEventType
        
        async with AsyncSessionLocal() as fresh_session:
            negotiation = await get_negotiation(fresh_session, negotiation_id)
            if negotiation and negotiation.state not in NegotiationState.TERMINAL_STATES:
                negotiation.state = NegotiationState.EXPIRED.value
                await fresh_session.commit()
                
            await record_event(
                session=fresh_session,
                event_type=AuditEventType.NEGOTIATION_FAILED,
                actor_type="SYSTEM",
                actor_id=None,
                merchant_id=negotiation.merchant_id if negotiation else None,
                negotiation_id=negotiation_id,
                metadata={"error": str(e), "source": "uncaught_exception"}
            )
            
        initial_state["status"] = "failed"
        initial_state["error_reason"] = f"Graph Crash: {str(e)}"
        return initial_state
