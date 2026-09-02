"""
NEXORA — Buyer Agent Runner

Provides a clean entry point for orchestrating the Buyer Agent LangGraph execution.
Safely encapsulates DB session management, tool dependencies, and policy context gathering.
"""
import uuid
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.runnables import RunnableConfig

from app.agents.buyer.graph import create_buyer_agent_graph
from app.agents.buyer.schemas import BuyerIntent, BuyerAgentState
from app.services.policy_service import list_policies
from app.services.audit_service import record_event, AuditEventType


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
        return final_state
    except Exception as e:
        logger.error(f"Buyer Agent Graph execution failed: {e}", exc_info=True)
        initial_state["status"] = "failed"
        initial_state["error_reason"] = f"Graph Crash: {str(e)}"
        return initial_state
