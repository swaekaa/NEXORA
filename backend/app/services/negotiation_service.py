"""
NEXORA — Negotiation Service

Handles persistence of negotiations and their message history.
"""
import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.negotiation import Negotiation, NegotiationState
from app.models.negotiation_message import NegotiationMessage


async def create_negotiation_with_proposal(
    session: AsyncSession,
    buyer_id: uuid.UUID,
    merchant_id: uuid.UUID,
    product_id: uuid.UUID,
    quantity: int,
    unit_price: Decimal,
    discount_percent: Decimal,
    total_amount: Decimal,
) -> Negotiation:
    """
    Creates a new negotiation in the OFFER state and persists the buyer's proposal as the first message.
    """
    negotiation = Negotiation(
        buyer_id=buyer_id,
        merchant_id=merchant_id,
        product_id=product_id,
        state=NegotiationState.OFFER.value,
        round_count=1,
    )
    session.add(negotiation)
    await session.flush()

    message = NegotiationMessage(
        negotiation_id=negotiation.id,
        sender_id=buyer_id,
        sender_type="buyer",
        sequence_number=1,
        message_type="PROPOSAL",
        content="Buyer Agent submitted a purchase proposal.",
        proposed_quantity=quantity,
        proposed_unit_price=unit_price,
        proposed_discount_percent=discount_percent,
        proposed_total=total_amount,
    )
    session.add(message)
    await session.commit()
    await session.refresh(negotiation)

    return negotiation
