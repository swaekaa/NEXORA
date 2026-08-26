"""
NEXORA — Audit Event ORM Model

Append-only audit trail for all significant business and AI agent decisions.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, uuid_pk, timestamp_col


class AuditEvent(Base):
    """
    Append-only record of a business event.
    """
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    
    event_type: Mapped[str] = mapped_column(sa.String, nullable=False)
    
    actor_type: Mapped[str] = mapped_column(sa.String, nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(sa.UUID(as_uuid=True), nullable=True)
    
    # Optional references to the main entities
    agreement_id: Mapped[uuid.UUID | None] = mapped_column(sa.UUID(as_uuid=True), nullable=True)
    negotiation_id: Mapped[uuid.UUID | None] = mapped_column(sa.UUID(as_uuid=True), nullable=True)
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(sa.UUID(as_uuid=True), nullable=True)
    
    # Structured metadata (e.g. reasoning, policy results, etc)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    
    # Immutable timestamp
    created_at: Mapped[datetime] = timestamp_col(server_default=True)

    __table_args__ = (
        sa.Index("idx_audit_events_agreement_id", "agreement_id"),
        sa.Index("idx_audit_events_merchant_id", "merchant_id"),
        sa.Index("idx_audit_events_created_at", "created_at"),
    )
