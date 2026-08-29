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
            round_count = neg.round_count
            
            from app.services.negotiation_service import get_negotiation_messages
            messages = await get_negotiation_messages(session, negotiation_id)
            
            if len(messages) > 0:
                latest_message = messages[-1]
                last_sender = latest_message.sender_type
                previous_latest_message_id = latest_message.id
            else:
                last_sender = None
                previous_latest_message_id = None
                
        # TERMINAL STATE CHECK (Requirement 7)
        if state in NegotiationState.TERMINAL_STATES:
            logger.info(f"NEGOTIATION_TERMINAL | negotiation_id={negotiation_id} | state={state} | round={round_count}")
            break
            
        from app.models.negotiation_message import SenderType
        
        # 2. Check whose turn it is (Requirement 3 & 6)
        if last_sender == SenderType.BUYER_AGENT.value:
            next_actor = SenderType.MERCHANT_AGENT.value
            logger.info(f"NEGOTIATION_TURN_STARTED | negotiation_id={negotiation_id} | turn={turn} | round={round_count} | latest_sender={last_sender} | next_actor={next_actor}")
            logger.info(f"AGENT_RUN_STARTED | negotiation_id={negotiation_id} | actor=MERCHANT_AGENT")
            
            async with AsyncSessionLocal() as session:
                try:
                    result = await run_merchant_agent(session, negotiation_id)
                    logger.info(f"AGENT_RUN_COMPLETED | negotiation_id={negotiation_id} | actor=MERCHANT_AGENT")
                except Exception as e:
                    logger.error(f"MERCHANT_AGENT_FAILED | negotiation_id={negotiation_id} | exception_type={type(e).__name__} | exception_message={str(e)}")
                    break
                
            if result.get("status") == "failed":
                logger.error(f"Merchant agent failed: {result.get('error_reason')}")
                # Mark as expired so the frontend doesn't hang forever
                async with AsyncSessionLocal() as session:
                    neg_to_expire = await get_negotiation(session, negotiation_id)
                    if neg_to_expire:
                        neg_to_expire.state = NegotiationState.EXPIRED.value
                        session.add(neg_to_expire)
                        await session.commit()
                break
                
            logger.info(f"POLICY_CHECK_COMPLETED | negotiation_id={negotiation_id} | decision={result.get('policy_decision')}")
                
            # DUPLICATE RUN PREVENTION (Requirement 5)
            async with AsyncSessionLocal() as session:
                msgs_after = await get_negotiation_messages(session, negotiation_id)
                new_latest_message_id = msgs_after[-1].id if msgs_after else None
                
                if new_latest_message_id == previous_latest_message_id:
                    logger.error(f"AGENT_NO_MESSAGE_PERSISTED | negotiation_id={negotiation_id} | actor=MERCHANT_AGENT")
                    # Mark as expired so the frontend doesn't hang forever
                    neg_to_expire = await get_negotiation(session, negotiation_id)
                    if neg_to_expire:
                        neg_to_expire.state = NegotiationState.EXPIRED.value
                        session.add(neg_to_expire)
                        await session.commit()
                    break
                    
                logger.info(f"MESSAGE_PERSISTED | negotiation_id={negotiation_id} | message_id={new_latest_message_id} | sender=MERCHANT_AGENT")
                logger.info(f"NEGOTIATION_TURN_COMPLETED | negotiation_id={negotiation_id} | next_actor=BUYER_AGENT")
                
        elif last_sender == SenderType.MERCHANT_AGENT.value:
            next_actor = SenderType.BUYER_AGENT.value
            logger.info(f"NEGOTIATION_TURN_STARTED | negotiation_id={negotiation_id} | turn={turn} | round={round_count} | latest_sender={last_sender} | next_actor={next_actor}")
            logger.info(f"AGENT_RUN_STARTED | negotiation_id={negotiation_id} | actor=BUYER_AGENT")
            
            # The Buyer Agent needs the negotiation ID inside the intent
            intent.negotiation_id = negotiation_id
            
            async with AsyncSessionLocal() as session:
                result = await run_buyer_agent(session, intent)
                logger.info(f"AGENT_RUN_COMPLETED | negotiation_id={negotiation_id} | actor=BUYER_AGENT")
                
            if result.get("status") == "failed":
                logger.error(f"Buyer agent failed: {result.get('error_reason')}")
                # Mark as expired so the frontend doesn't hang forever
                async with AsyncSessionLocal() as session:
                    neg_to_expire = await get_negotiation(session, negotiation_id)
                    if neg_to_expire:
                        neg_to_expire.state = NegotiationState.EXPIRED.value
                        session.add(neg_to_expire)
                        await session.commit()
                break
                
            # DUPLICATE RUN PREVENTION (Requirement 5)
            async with AsyncSessionLocal() as session:
                msgs_after = await get_negotiation_messages(session, negotiation_id)
                new_latest_message_id = msgs_after[-1].id if msgs_after else None
                
                if new_latest_message_id == previous_latest_message_id:
                    logger.error(f"AGENT_NO_MESSAGE_PERSISTED | negotiation_id={negotiation_id} | actor=BUYER_AGENT")
                    # Mark as expired so the frontend doesn't hang forever
                    neg_to_expire = await get_negotiation(session, negotiation_id)
                    if neg_to_expire:
                        neg_to_expire.state = NegotiationState.EXPIRED.value
                        session.add(neg_to_expire)
                        await session.commit()
                    break
                    
                logger.info(f"MESSAGE_PERSISTED | negotiation_id={negotiation_id} | message_id={new_latest_message_id} | sender=BUYER_AGENT")
                logger.info(f"NEGOTIATION_TURN_COMPLETED | negotiation_id={negotiation_id} | next_actor=MERCHANT_AGENT")
                    
                neg_after = await get_negotiation(session, negotiation_id)
                if neg_after and neg_after.round_count > round_count:
                    logger.info(f"NEGOTIATION_ROUND_COMPLETED | negotiation_id={negotiation_id} | completed_round={round_count}")
                
        else:
            logger.info(f"Negotiation {negotiation_id} has invalid last sender {last_sender}. Pausing orchestration.")
            break
            
        # Add a tiny sleep to allow DB connections and logs to flush
        await asyncio.sleep(1)
        
    else:
        # Executed if the loop completes without a break (MAX_TURNS reached)
        logger.warning(f"NEGOTIATION_MAX_TURNS_REACHED | negotiation_id={negotiation_id}")

    logger.info(f"Exited orchestration loop for negotiation {negotiation_id}")
