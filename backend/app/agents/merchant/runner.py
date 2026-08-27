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
    # 1. Load Negotiation
    negotiation = await get_negotiation(session, negotiation_id)
    if not negotiation:
        return {"status": "failed", "error_reason": "Negotiation not found"}
        
    if negotiation.state in NegotiationState.TERMINAL_STATES:
        return {"status": "failed", "error_reason": f"Negotiation is in terminal state: {negotiation.state}"}
        
    # 2. Load Messages
    messages = await get_negotiation_messages(session, negotiation_id)
    if not messages:
        return {"status": "failed", "error_reason": "No messages in negotiation"}
        
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
        
    # 4. Construct Intent
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
        max_rounds=10, # Configurable threshold
        
        product_description=f"{product.name} - {product.description} (SKU: {product.sku})",
        buyer_message=latest_message.content
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
        "current_action": None,
        "deterministic_total": None,
        "policy_decision": None,
        "policy_reasons": None,
        "messages": []
    }
    
    graph = build_merchant_agent_graph()
    
    try:
        final_state = await graph.ainvoke(initial_state, config=config)
        return final_state
    except Exception as e:
        logger.error(f"Merchant Agent Graph execution failed: {e}", exc_info=True)
        initial_state["status"] = "failed"
        initial_state["error_reason"] = f"Graph Crash: {str(e)}"
        return initial_state
