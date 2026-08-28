import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db
from app.services.negotiation_service import get_negotiation, get_negotiation_messages, get_negotiations_by_merchant

router = APIRouter(tags=["Negotiations"])

from pydantic import BaseModel, ConfigDict
from datetime import datetime

class NegotiationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    buyer_id: uuid.UUID
    merchant_id: uuid.UUID
    product_id: uuid.UUID
    state: str
    round_count: int
    max_rounds: int
    started_at: datetime
    expires_at: datetime | None
    ended_at: datetime | None
    created_at: datetime
    updated_at: datetime

class NegotiationMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    negotiation_id: uuid.UUID
    sender_id: str
    sender_type: str
    sequence_number: int
    message_type: str
    content: str | None = None
    payload: dict | None = None
    created_at: datetime

@router.get("/negotiations/{negotiation_id}", response_model=NegotiationResponse)
async def get_negotiation_by_id(
    negotiation_id: uuid.UUID,
    session: AsyncSession = Depends(get_db)
) -> Any:
    neg = await get_negotiation(session, negotiation_id)
    if not neg:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    return NegotiationResponse.model_validate(neg)

@router.get("/negotiations/{negotiation_id}/messages", response_model=list[NegotiationMessageResponse])
async def get_messages(
    negotiation_id: uuid.UUID,
    session: AsyncSession = Depends(get_db)
) -> Any:
    messages = await get_negotiation_messages(session, negotiation_id)
    return [NegotiationMessageResponse.model_validate(m) for m in messages]

@router.get("/merchants/{merchant_id}/negotiations", response_model=list[NegotiationResponse])
async def list_merchant_negotiations(
    merchant_id: uuid.UUID,
    session: AsyncSession = Depends(get_db)
) -> Any:
    negotiations = await get_negotiations_by_merchant(session, merchant_id)
    return [NegotiationResponse.model_validate(n) for n in negotiations]
