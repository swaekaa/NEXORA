"""
NEXORA — Approval Service

Handles human authorization requests.
Enforces that human approval can never bypass deterministic DENY decisions,
and never directly calls Razorpay.
"""
from __future__ import annotations

import uuid
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import InvalidStateTransitionError, ResourceNotFoundError
from app.models.agreement import Agreement
from app.models.approval_request import ApprovalRequest, ApprovalStatus
from app.services.audit_service import record_event, AuditEventType


async def create_approval_request(
    session: AsyncSession,
    agreement: Agreement,
    policy_decision: str,
    reason: str,
) -> ApprovalRequest:
    """
    Creates an approval request for an agreement.
    This must ONLY be called internally when PolicyEngine returns HUMAN_APPROVAL_REQUIRED.
    """
    # Check if ANY one already exists (idempotency)
    result = await session.execute(
        sa.select(ApprovalRequest).where(
            ApprovalRequest.agreement_id == agreement.id
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing
        
    approval = ApprovalRequest(
        agreement_id=agreement.id,
        merchant_id=agreement.merchant_id,
        status=ApprovalStatus.PENDING,
        policy_decision=policy_decision,
        reason=reason,
    )
    session.add(approval)
    
    await record_event(
        session=session,
        event_type=AuditEventType.HUMAN_APPROVAL_REQUESTED,
        actor_type="SYSTEM",
        agreement_id=agreement.id,
        merchant_id=agreement.merchant_id,
        metadata={"reason": reason}
    )
    
    await session.flush()
    return approval


async def get_approval(
    session: AsyncSession,
    approval_id: uuid.UUID,
    merchant_id: uuid.UUID,
) -> ApprovalRequest:
    """Gets an approval request, enforcing merchant isolation."""
    result = await session.execute(
        sa.select(ApprovalRequest).where(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.merchant_id == merchant_id
        )
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise ResourceNotFoundError(f"Approval request {approval_id} not found.")
    return approval


async def get_pending_approvals(
    session: AsyncSession,
    merchant_id: uuid.UUID,
) -> list[ApprovalRequest]:
    """Gets all pending approvals for a merchant."""
    result = await session.execute(
        sa.select(ApprovalRequest).where(
            ApprovalRequest.merchant_id == merchant_id,
            ApprovalRequest.status == ApprovalStatus.PENDING
        ).order_by(ApprovalRequest.created_at.asc())
    )
    return list(result.scalars().all())


async def approve(
    session: AsyncSession,
    approval_id: uuid.UUID,
    merchant_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> ApprovalRequest:
    """
    Marks an approval request as APPROVED.
    Does NOT execute payment. Payment execution must happen subsequently.
    """
    approval = await get_approval(session, approval_id, merchant_id)
    
    if approval.status != ApprovalStatus.PENDING:
        raise InvalidStateTransitionError(f"Cannot approve request in state {approval.status}")
        
    # Verify agreement still exists
    result = await session.execute(
        sa.select(Agreement).where(Agreement.id == approval.agreement_id)
    )
    agreement = result.scalar_one_or_none()
    if not agreement:
        raise InvalidStateTransitionError("Agreement no longer exists.")
        
    approval.status = ApprovalStatus.APPROVED
    
    await record_event(
        session=session,
        event_type=AuditEventType.HUMAN_APPROVED,
        actor_type="HUMAN_USER",
        actor_id=actor_id,
        agreement_id=approval.agreement_id,
        merchant_id=merchant_id,
        metadata={"approval_id": str(approval.id)}
    )
    
    await session.flush()
    return approval


async def reject(
    session: AsyncSession,
    approval_id: uuid.UUID,
    merchant_id: uuid.UUID,
    actor_id: uuid.UUID,
    reason: str,
) -> ApprovalRequest:
    """
    Marks an approval request as REJECTED.
    """
    approval = await get_approval(session, approval_id, merchant_id)
    
    if approval.status != ApprovalStatus.PENDING:
        raise InvalidStateTransitionError(f"Cannot reject request in state {approval.status}")
        
    approval.status = ApprovalStatus.REJECTED
    approval.resolution_reason = reason
    
    await record_event(
        session=session,
        event_type=AuditEventType.HUMAN_REJECTED,
        actor_type="HUMAN_USER",
        actor_id=actor_id,
        agreement_id=approval.agreement_id,
        merchant_id=merchant_id,
        metadata={"approval_id": str(approval.id), "reason": reason}
    )
    
    await session.flush()
    return approval
