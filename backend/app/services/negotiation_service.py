"""
NEXORA — Negotiation Service

Handles persistence of negotiations and their message history.
Enforces the state machine, valid message types, round counting, and atomic persistence.
"""
import uuid
import json
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.negotiation import Negotiation, NegotiationState
from app.models.negotiation_message import NegotiationMessage, SenderType, MessageType
from app.schemas.negotiation import NegotiationMessagePayload
from app.services.audit_service import record_event, AuditEventType


class NegotiationTerminalError(ValueError):
    """Raised when trying to mutate a terminal negotiation."""
    pass


class InvalidTransitionError(ValueError):
    """Raised when an invalid state transition is attempted."""
    pass


# Helper to convert payload to json-safe dict (serializing Decimal to string)
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return super().default(obj)


async def get_negotiation(session: AsyncSession, negotiation_id: uuid.UUID) -> Negotiation | None:
    result = await session.execute(
        select(Negotiation).where(Negotiation.id == negotiation_id)
    )
    return result.scalar_one_or_none()


async def get_negotiation_messages(session: AsyncSession, negotiation_id: uuid.UUID) -> list[NegotiationMessage]:
    result = await session.execute(
        select(NegotiationMessage)
        .where(NegotiationMessage.negotiation_id == negotiation_id)
        .order_by(NegotiationMessage.sequence_number)
    )
    return list(result.scalars().all())


async def get_negotiations_by_merchant(session: AsyncSession, merchant_id: uuid.UUID) -> list[Negotiation]:
    result = await session.execute(
        select(Negotiation).where(Negotiation.merchant_id == merchant_id).order_by(Negotiation.created_at.desc())
    )
    return list(result.scalars().all())


async def create_negotiation_with_proposal(
    session: AsyncSession,
    buyer_id: uuid.UUID,
    merchant_id: uuid.UUID,
    product_id: uuid.UUID,
    payload: NegotiationMessagePayload,
    content: str = "Buyer Agent submitted a purchase proposal."
) -> Negotiation:
    """
    Creates a new negotiation in the OFFER state and persists the buyer's proposal as the first message.
    """
    negotiation = Negotiation(
        buyer_id=buyer_id,
        merchant_id=merchant_id,
        product_id=product_id,
        state=NegotiationState.OFFER.value,
        round_count=1, # Round 1 begins with the buyer's proposal
    )
    session.add(negotiation)
    await session.flush()

    # Convert payload to a json dict, converting Decimals/UUIDs to str
    payload_dict = json.loads(json.dumps(payload.model_dump(), cls=DecimalEncoder))

    message = NegotiationMessage(
        negotiation_id=negotiation.id,
        sender_id=str(buyer_id),
        sender_type=SenderType.BUYER_AGENT.value,
        sequence_number=1,
        message_type=MessageType.OFFER.value,
        content=content,
        payload=payload_dict
    )
    session.add(message)
    await session.commit()
    await session.refresh(negotiation)

    return negotiation


async def append_negotiation_message(
    session: AsyncSession,
    negotiation_id: uuid.UUID,
    sender_type: SenderType,
    sender_id: str,
    message_type: MessageType,
    content: str | None = None,
    payload: NegotiationMessagePayload | None = None
) -> NegotiationMessage:
    """
    Atomically appends a new message to a negotiation and updates the round count/state if necessary.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"MERCHANT_MESSAGE_APPEND_STARTED | negotiation_id={negotiation_id} | message_type={message_type.value}")

    negotiation = await get_negotiation(session, negotiation_id)
    if not negotiation:
        raise ValueError(f"Negotiation {negotiation_id} not found.")

    if negotiation.state in NegotiationState.TERMINAL_STATES:
        raise NegotiationTerminalError(f"Cannot append to negotiation {negotiation_id} in terminal state {negotiation.state}")

    # Determine next sequence number
    # We do a max query or just rely on length if we loaded them, but doing count is safer.
    result = await session.execute(
        select(sa.func.max(NegotiationMessage.sequence_number))
        .where(NegotiationMessage.negotiation_id == negotiation_id)
    )
    current_max = result.scalar() or 0
    next_seq = current_max + 1

    # Round Counting Logic:
    # Round represents one complete exchange (e.g. Buyer Proposal + Merchant Counter = Round 1)
    # When Buyer sends a new COUNTER_OFFER, the round_count increments.
    if sender_type == SenderType.BUYER_AGENT and message_type in (MessageType.COUNTER_OFFER, MessageType.OFFER):
        # The very first offer sets round_count = 1 upon creation.
        # If this is a subsequent counter from the buyer, we increment round.
        if next_seq > 1:
            negotiation.round_count += 1

    # State Transition Logic:
    if message_type == MessageType.ACCEPT:
        negotiation.state = NegotiationState.ACCEPTED.value
    elif message_type == MessageType.REJECT:
        negotiation.state = NegotiationState.REJECTED.value
    elif message_type == MessageType.COUNTER_OFFER:
        negotiation.state = NegotiationState.COUNTER_OFFER.value

    payload_dict = None
    if payload:
        payload_dict = json.loads(json.dumps(payload.model_dump(), cls=DecimalEncoder))

    message = NegotiationMessage(
        negotiation_id=negotiation.id,
        sender_id=sender_id,
        sender_type=sender_type.value,
        sequence_number=next_seq,
        message_type=message_type.value,
        content=content,
        payload=payload_dict
    )
    
    session.add(message)
    session.add(negotiation)
    
    if message_type == MessageType.ACCEPT:
        await record_event(
            session=session,
            event_type=AuditEventType.NEGOTIATION_ACCEPTED,
            actor_type=sender_type.value,
            actor_id=uuid.UUID(sender_id) if sender_id != "SYSTEM" else None,
            negotiation_id=negotiation.id,
            merchant_id=negotiation.merchant_id,
            metadata={"round": negotiation.round_count}
        )
    elif message_type == MessageType.REJECT:
        await record_event(
            session=session,
            event_type=AuditEventType.NEGOTIATION_REJECTED,
            actor_type=sender_type.value,
            actor_id=uuid.UUID(sender_id) if sender_id != "SYSTEM" else None,
            negotiation_id=negotiation.id,
            merchant_id=negotiation.merchant_id,
            metadata={"round": negotiation.round_count, "reason": content or "No reason provided"}
        )
        
    await session.commit()
    await session.refresh(message)
    
    logger.info(f"MERCHANT_MESSAGE_APPEND_COMPLETED | negotiation_id={negotiation_id} | message_id={message.id}")
    return message


async def expire_negotiation(session: AsyncSession, negotiation_id: uuid.UUID) -> Negotiation:
    negotiation = await get_negotiation(session, negotiation_id)
    if not negotiation:
        raise ValueError("Negotiation not found")
        
    if negotiation.state in NegotiationState.TERMINAL_STATES:
        raise NegotiationTerminalError("Already terminal")
        
    negotiation.state = NegotiationState.EXPIRED.value
    session.add(negotiation)
    await session.commit()
    await session.refresh(negotiation)
    return negotiation
