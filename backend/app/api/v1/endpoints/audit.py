from typing import Any
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.services import audit_service

router = APIRouter()


class AuditEventResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    actor_type: str
    actor_id: uuid.UUID | None
    agreement_id: uuid.UUID | None
    negotiation_id: uuid.UUID | None
    merchant_id: uuid.UUID | None
    metadata_: dict[str, Any] | None
    created_at: Any

    class Config:
        from_attributes = True
        populate_by_name = True


@router.get("/merchants/{merchant_id}/audit", response_model=list[AuditEventResponse])
async def get_merchant_audit(
    merchant_id: uuid.UUID,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db)
) -> Any:
    """Gets the audit trail for a merchant."""
    events = await audit_service.get_merchant_audit(session, merchant_id, limit, offset)
    # Map metadata_ back to metadata if needed, but Pydantic handles it with populate_by_name if configured.
    # However we can just return events because the ORM has metadata_
    return events


@router.get("/merchants/{merchant_id}/agreements/{agreement_id}/audit", response_model=list[AuditEventResponse])
async def get_agreement_audit(
    merchant_id: uuid.UUID,
    agreement_id: uuid.UUID,
    session: AsyncSession = Depends(get_db)
) -> Any:
    """Gets the audit trail for a specific agreement."""
    events = await audit_service.get_agreement_audit(session, agreement_id, merchant_id)
    return events
