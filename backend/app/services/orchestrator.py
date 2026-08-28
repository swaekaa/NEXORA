"""
NEXORA — Negotiation Orchestrator

Automatically triggers the next agent in a multi-round negotiation
so the frontend does not need to explicitly call each agent.
"""
import uuid
import logging
import asyncio

from app.database.connection import AsyncSessionLocal
from app.agents.merchant.runner import run_merchant_agent
from app.agents.buyer.runner import run_buyer_agent
from app.agents.buyer.schemas import BuyerIntent
from app.models.negotiation import NegotiationState
from app.services.negotiation_service import get_negotiation

logger = logging.getLogger(__name__)

async def run_negotiation_loop(negotiation_id: uuid.UUID, intent: BuyerIntent):
    """
    Background loop that orchestrates a multi-turn negotiation.
    When one agent completes its turn, this triggers the other agent.
    Loops until the negotiation reaches a terminal state.
    """
    logger.info(f"Starting orchestration loop for negotiation {negotiation_id}")
    
    # Cap the maximum number of automatic back-and-forth rounds
    MAX_TURNS = 20
    
    for turn in range(MAX_TURNS):
        # 1. Fetch current negotiation state
        async with AsyncSessionLocal() as session:
            neg = await get_negotiation(session, negotiation_id)
            if not neg:
                logger.error(f"Negotiation {negotiation_id} not found.")
                break
                
            state = neg.state
            
        if state in NegotiationState.TERMINAL_STATES:
            logger.info(f"Negotiation {negotiation_id} reached terminal state {state}. Orchestration complete.")
            break
            
        # 2. Check whose turn it is
        if state == NegotiationState.OFFER.value:
            logger.info(f"[Turn {turn}] MERCHANT_AGENT_TRIGGERED")
            logger.info(f"MERCHANT_AGENT_TRIGGERING | negotiation_id={negotiation_id}")
            async with AsyncSessionLocal() as session:
                try:
                    result = await run_merchant_agent(session, negotiation_id)
                    logger.info(f"MERCHANT_AGENT_TRIGGER_RETURNED | negotiation_id={negotiation_id} | result_status={result.get('status')}")
                    logger.info(f"Merchant agent result: {result}")
                except Exception as e:
                    logger.error(f"MERCHANT_AGENT_FAILED | negotiation_id={negotiation_id} | exception_type={type(e).__name__} | exception_message={str(e)}")
                    break
                
            if result.get("status") == "failed":
                logger.error(f"Merchant agent failed: {result.get('error_reason')}")
                break
                
            async with AsyncSessionLocal() as session:
                neg_after = await get_negotiation(session, negotiation_id)
                if neg_after and neg_after.state == state:
                    logger.error(f"Agent stalled: Merchant Agent did not change state from {state}. Breaking loop.")
                    break
                
        elif state == NegotiationState.COUNTER_OFFER.value:
            logger.info(f"[Turn {turn}] BUYER_AGENT_RESUMED")
            # The Buyer Agent needs the negotiation ID inside the intent
            intent.negotiation_id = negotiation_id
            
            async with AsyncSessionLocal() as session:
                result = await run_buyer_agent(session, intent)
                
            if result.get("status") == "failed":
                logger.error(f"Buyer agent failed: {result.get('error_reason')}")
                break
                
            async with AsyncSessionLocal() as session:
                neg_after = await get_negotiation(session, negotiation_id)
                if neg_after and neg_after.state == state:
                    logger.error(f"Agent stalled: Buyer Agent did not change state from {state}. Breaking loop.")
                    break
                
        else:
            # States like DISCOVER, REQUEST aren't autonomous loops yet
            logger.info(f"Negotiation {negotiation_id} is in state {state}. Pausing orchestration.")
            break
            
        # Add a tiny sleep to allow DB connections and logs to flush
        await asyncio.sleep(1)

    logger.info(f"Exited orchestration loop for negotiation {negotiation_id}")
