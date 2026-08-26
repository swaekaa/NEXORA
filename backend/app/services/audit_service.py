"""
NEXORA — Audit Service

Provides an append-only interface to write structured business events.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

from app.models.audit_event import AuditEvent


class AuditEventType:
    """Standardized event types for the audit trail."""
    # Negotiation / Agreement
    NEGOTIATION_ACCEPTED = "NEGOTIATION_ACCEPTED"
    NEGOTIATION_REJECTED = "NEGOTIATION_REJECTED"
    AGREEMENT_CREATED = "AGREEMENT_CREATED"
    AGREEMENT_VALIDATED = "AGREEMENT_VALIDATED"
    AGREEMENT_VALIDATION_FAILED = "AGREEMENT_VALIDATION_FAILED"
    
    # Policy / Approval
    POLICY_CHECK = "POLICY_CHECK"
    HUMAN_APPROVAL_REQUESTED = "HUMAN_APPROVAL_REQUESTED"
    HUMAN_APPROVED = "HUMAN_APPROVED"
    HUMAN_REJECTED = "HUMAN_REJECTED"
    
    # Payment
    PAYMENT_INITIATED = "PAYMENT_INITIATED"
    PAYMENT_CAPTURED = "PAYMENT_CAPTURED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_BLOCKED = "PAYMENT_BLOCKED"
    
    # Inventory
    INVENTORY_RESERVED = "INVENTORY_RESERVED"
    INVENTORY_COMMITTED = "INVENTORY_COMMITTED"
    INVENTORY_RELEASED = "INVENTORY_RELEASED"
    INVENTORY_EXPIRED = "INVENTORY_EXPIRED"
    FULFILLMENT_COMPLETED = "FULFILLMENT_COMPLETED"


async def record_event(
    session: AsyncSession,
    event_type: str,
    actor_type: str,
    metadata: dict[str, Any],
    actor_id: uuid.UUID | None = None,
    agreement_id: uuid.UUID | None = None,
    negotiation_id: uuid.UUID | None = None,
    merchant_id: uuid.UUID | None = None,
) -> AuditEvent:
    """
    Records an append-only audit event in the current transaction.
    
    This function intentionally does NOT commit the session. It must be called
    within an existing transaction so the business state change and the audit
    event are atomically committed together.
    """
    event = AuditEvent(
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        agreement_id=agreement_id,
        negotiation_id=negotiation_id,
        merchant_id=merchant_id,
        metadata_=metadata,
    )
    session.add(event)
    # Flush to ensure the event is written to the DB transaction and gets an ID,
    # but do NOT commit. The caller commits.
    await session.flush()
    return event


async def get_agreement_audit(
    session: AsyncSession,
    agreement_id: uuid.UUID,
    merchant_id: uuid.UUID,
) -> list[AuditEvent]:
    """
    Fetches the audit trail for a specific agreement, enforcing merchant ownership.
    Ordered chronologically.
    """
    result = await session.execute(
        sa.select(AuditEvent)
        .where(
            AuditEvent.agreement_id == agreement_id,
            AuditEvent.merchant_id == merchant_id
        )
        .order_by(AuditEvent.created_at.asc())
    )
    return list(result.scalars().all())


async def get_merchant_audit(
    session: AsyncSession,
    merchant_id: uuid.UUID,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditEvent]:
    """
    Fetches the audit trail for a merchant.
    Ordered reverse-chronologically (newest first).
    """
    result = await session.execute(
        sa.select(AuditEvent)
        .where(AuditEvent.merchant_id == merchant_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())
