from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.services import approval_service
from app.exceptions import ResourceNotFoundError, InvalidStateTransitionError

router = APIRouter()


class RejectionRequest(BaseModel):
    reason: str


class ApprovalResponse(BaseModel):
    id: uuid.UUID
    agreement_id: uuid.UUID
    merchant_id: uuid.UUID
    status: str
    policy_decision: str
    reason: str
    resolution_reason: str | None
    requested_at: Any
    resolved_at: Any | None
    created_at: Any
    updated_at: Any

    class Config:
        from_attributes = True


@router.get("/{merchant_id}/approvals", response_model=list[ApprovalResponse])
async def get_pending_approvals(
    merchant_id: uuid.UUID,
    session: AsyncSession = Depends(get_db)
) -> Any:
    """Gets all pending approvals for a merchant."""
    approvals = await approval_service.get_pending_approvals(session, merchant_id)
    return approvals


@router.get("/{merchant_id}/approvals/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    merchant_id: uuid.UUID,
    approval_id: uuid.UUID,
    session: AsyncSession = Depends(get_db)
) -> Any:
    """Gets a specific approval request."""
    try:
        approval = await approval_service.get_approval(session, approval_id, merchant_id)
        return approval
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{merchant_id}/approvals/{approval_id}/approve", response_model=ApprovalResponse)
async def approve_request(
    merchant_id: uuid.UUID,
    approval_id: uuid.UUID,
    # In a real app, actor_id comes from auth token. We simulate it for MVP.
    actor_id: uuid.UUID = None,
    session: AsyncSession = Depends(get_db)
) -> Any:
    """Approves a request (does not initiate payment)."""
    try:
        if not actor_id:
            # Default fallback for testing if none provided
            actor_id = merchant_id
        approval = await approval_service.approve(session, approval_id, merchant_id, actor_id)
        return approval
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{merchant_id}/approvals/{approval_id}/reject", response_model=ApprovalResponse)
async def reject_request(
    merchant_id: uuid.UUID,
    approval_id: uuid.UUID,
    payload: RejectionRequest,
    # In a real app, actor_id comes from auth token.
    actor_id: uuid.UUID = None,
    session: AsyncSession = Depends(get_db)
) -> Any:
    """Rejects a request."""
    try:
        if not actor_id:
            actor_id = merchant_id
        approval = await approval_service.reject(session, approval_id, merchant_id, actor_id, payload.reason)
        return approval
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))
