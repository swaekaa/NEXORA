"""
NEXORA — Approval Request ORM Model

Tracks human approval requests required when the PolicyEngine returns HUMAN_APPROVAL_REQUIRED.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, uuid_pk, timestamp_col, utcnow


class ApprovalStatus:
    """Strict state machine for approval requests."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

    ALL = {PENDING, APPROVED, REJECTED}
    TERMINAL = {APPROVED, REJECTED}


class ApprovalRequest(Base):
    """
    Tracks a human approval request.
    Tied uniquely to one Agreement.
    """
    __tablename__ = "approval_requests"

    id: Mapped[uuid.UUID] = uuid_pk()
    
    # 1:1 relationship with agreement
    agreement_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), 
        sa.ForeignKey("agreements.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    
    # Merchant ownership for SQL-level isolation
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), 
        sa.ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        sa.String, 
        nullable=False, 
        default=ApprovalStatus.PENDING
    )
    
    policy_decision: Mapped[str] = mapped_column(sa.String, nullable=False)
    reason: Mapped[str] = mapped_column(sa.String, nullable=False)
    
    resolution_reason: Mapped[str | None] = mapped_column(sa.String, nullable=True)

    requested_at: Mapped[datetime] = timestamp_col(server_default=True)
    resolved_at: Mapped[datetime | None] = timestamp_col(nullable=True)
    created_at: Mapped[datetime] = timestamp_col(server_default=True)
    updated_at: Mapped[datetime] = timestamp_col(server_default=True)

    __table_args__ = (
        sa.CheckConstraint(
            status.in_(list(ApprovalStatus.ALL)),
            name="ck_approval_requests_status"
        ),
        sa.Index("idx_approval_requests_merchant_id", "merchant_id"),
    )
