"""
NEXORA — Buyer Agent Runner

Provides a clean entry point for orchestrating the Buyer Agent LangGraph execution.
Safely encapsulates DB session management, tool dependencies, and policy context gathering.
"""
import uuid
import logging
from typing import Any
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.runnables import RunnableConfig

from app.agents.buyer.graph import create_buyer_agent_graph
from app.agents.buyer.schemas import BuyerIntent, BuyerAgentState
from app.services.policy_service import list_policies
from app.services.audit_service import record_event, AuditEventType
from app.models.negotiation import NegotiationState
from app.services.negotiation_service import get_negotiation


logger = logging.getLogger(__name__)


async def run_buyer_agent(session: AsyncSession, intent: BuyerIntent) -> BuyerAgentState:
    """
    Executes the buyer agent workflow to completion or failure.
    """
    # 1. Fetch active policy context for the merchant
    policies = await list_policies(session, intent.merchant_id)
    active_policy = next((p for p in policies if p.is_active), None)
    
    policy_context = {}
    if active_policy:
        policy_context = {
            "merchant_id": active_policy.merchant_id,
            "policy_id": active_policy.id,
            "minimum_price": active_policy.minimum_price,
            "maximum_discount_percent": active_policy.maximum_discount_percent,
            "maximum_autonomous_transaction": active_policy.maximum_autonomous_transaction,
            "human_approval_required": active_policy.human_approval_required
        }
        
    # 2. Configure the graph execution environment
    config: RunnableConfig = {
        "configurable": {
            "session": session,
            "policy_context": policy_context
        }
    }
    
    reservation_price = intent.reservation_unit_price
    if reservation_price is None:
        reservation_price = intent.maximum_budget / Decimal(intent.quantity)
        
    target_price = intent.target_unit_price
    if target_price is None:
        # Generic procurement heuristic: target a 20% margin below the reservation price
        # if the user hasn't provided a specific target.
        target_price = reservation_price * Decimal("0.80")
        
    # 3. Initialize state
    initial_state: BuyerAgentState = {
        "run_id": str(uuid.uuid4()),
        "intent": intent,
        "step_count": 0,
        "status": "in_progress",
        "error_reason": None,
        "candidate_products": [],
        "selected_product_id": None,
        "proposal_revisions": 0,
        "negotiation_round": 0,
        
        # New Negotiation State
        "target_unit_price": target_price,
        "reservation_unit_price": reservation_price,
        "previous_offer": None,
        "opponent_offer": None,
        "price_gap": None,
        "repeated_offer_count": 0,
        
        "strategy": None,
        "current_action": None,
        "deterministic_total": None,
        "merchant_counter": None,
        "negotiation_status": None,
        "policy_decision": None,
        "policy_reasons": None,
        "negotiation_id": intent.negotiation_id,
        "messages": []
    }
    
    # Log intent received
    await record_event(
        session=session,
        event_type=AuditEventType.NEGOTIATION_STARTED,
        actor_type="BUYER_AGENT",
        actor_id=intent.buyer_id,
        merchant_id=intent.merchant_id,
        metadata={
            "action": "INTENT_RECEIVED",
            "run_id": initial_state["run_id"],
            "product_query": intent.product_query,
            "quantity": intent.quantity,
            "maximum_budget": str(intent.maximum_budget),
        }
    )

    
    # Commit the transaction so the DB connection is returned to the pool
    # before we start the potentially long-running LangGraph execution.
    await session.commit()
    
    # 4. Compile and Run the Graph
    graph = create_buyer_agent_graph()
    
    try:
        final_state = await graph.ainvoke(initial_state, config=config)
        
        if final_state.get("status") == "failed":
            error_reason = final_state.get('error_reason', '')
            logger.error(f"Buyer agent graph failed: {error_reason}")

            # Only mark the negotiation as EXPIRED for genuine business failures.
            # Infrastructure/model errors (content filter, timeout) should NOT permanently
            # kill the negotiation state — the orchestrator will handle retry logic.
            is_infrastructure_error = error_reason in (
                "AGENT_MODEL_CONTENT_FILTER",
                "LLM_TIMEOUT",
                "LLM_MODEL_UNAVAILABLE",
            )

            if not is_infrastructure_error:
                negotiation = await get_negotiation(session, intent.negotiation_id)
                if negotiation and negotiation.state not in NegotiationState.TERMINAL_STATES:
                    negotiation.state = NegotiationState.EXPIRED.value
                    await session.commit()
            else:
                logger.warning(
                    f"Buyer model infrastructure error ({error_reason}) — "
                    f"negotiation state preserved for orchestrator retry."
                )

            await record_event(
                session=session,
                event_type=AuditEventType.NEGOTIATION_FAILED,
                actor_type="SYSTEM",
                actor_id=None,
                merchant_id=intent.merchant_id,
                negotiation_id=intent.negotiation_id,
                metadata={"error": error_reason, "source": "final_state", "infrastructure_error": is_infrastructure_error}
            )
            return final_state
        return final_state

    except Exception as e:
        logger.error(f"Buyer agent execution failed: {str(e)}", exc_info=True)
        from app.database.connection import AsyncSessionLocal
        
        # Use a fresh session because the original might be in PendingRollbackError state
        async with AsyncSessionLocal() as fresh_session:
            negotiation = await get_negotiation(fresh_session, intent.negotiation_id)
            if negotiation and negotiation.state not in NegotiationState.TERMINAL_STATES:
                negotiation.state = NegotiationState.EXPIRED.value
                await fresh_session.commit()
                
            await record_event(
                session=fresh_session,
                event_type=AuditEventType.NEGOTIATION_FAILED,
                actor_type="SYSTEM",
                actor_id=None,
                merchant_id=intent.merchant_id,
                negotiation_id=intent.negotiation_id,
                metadata={"error": str(e), "source": "uncaught_exception"}
            )
            
        initial_state["status"] = "failed"
        initial_state["error_reason"] = f"Graph Crash: {str(e)}"
        return initial_state
