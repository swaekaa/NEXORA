import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db
from app.services.agreement_service import get_agreement, get_agreements_by_merchant

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from decimal import Decimal

router = APIRouter(tags=["Agreements"])

class AgreementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    negotiation_id: uuid.UUID
    merchant_id: uuid.UUID
    buyer_id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    quantity: int
    unit_price: Decimal
    total_amount: Decimal
    currency: str
    status: str
    payment_terms: str
    delivery_days: int
    warranty_months: int
    policy_decision: str | None = None
    created_at: datetime
    updated_at: datetime

@router.get("/agreements/{agreement_id}", response_model=AgreementResponse)
async def get_agreement_by_id(
    agreement_id: uuid.UUID,
    session: AsyncSession = Depends(get_db)
) -> Any:
    agreement = await get_agreement(session, agreement_id)
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    return agreement

@router.get("/merchants/{merchant_id}/agreements", response_model=list[AgreementResponse])
async def list_merchant_agreements(
    merchant_id: uuid.UUID,
    session: AsyncSession = Depends(get_db)
) -> Any:
    agreements = await get_agreements_by_merchant(session, merchant_id)
    return agreements
