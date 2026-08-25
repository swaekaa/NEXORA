"""
NEXORA — Negotiation Schemas
"""
import uuid
from decimal import Decimal
from pydantic import BaseModel, Field

class NegotiationMessagePayload(BaseModel):
    """
    Structured payload for negotiation messages.
    Stored in the JSONB `payload` column in the database.
    Prices are strings in the database to preserve Decimal, but Pydantic handles Decimal natively.
    """
    product_id: uuid.UUID
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0)
    discount_percent: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    total_amount: Decimal = Field(..., gt=0)
    currency: str = "INR"

class CreateNegotiationMessage(BaseModel):
    sender_type: str
    sender_id: str
    message_type: str
    content: str | None = None
    payload: NegotiationMessagePayload | None = None
