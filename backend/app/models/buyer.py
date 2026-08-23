"""
NEXORA — Buyer ORM Model

Buyer represents the entity whose interests the Buyer Agent represents.

This is a domain identity model — NOT an authentication model.
Authentication credentials (passwords, tokens) do NOT belong here.

Status values:
    active  → buyer can participate in negotiations
    inactive → buyer has been deactivated
    blocked  → buyer is blocked (e.g., fraud, non-payment)

Deletion rule:
    Buyer → Negotiation: RESTRICT
    We cannot delete a buyer who has negotiation/payment history.
    This protects the financial audit trail.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.negotiation import Negotiation


class BuyerStatus:
    """Controlled status values for Buyer."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"

    ALL = {ACTIVE, INACTIVE, BLOCKED}


class Buyer(Base):
    """
    Buyer entity — the organization represented by the Buyer Agent.

    Immutable fields:
        id, created_at

    Mutable fields:
        name, email, organization, status, updated_at
    """
    __tablename__ = "buyers"

    # ── Primary Key ──────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa.text("gen_random_uuid()"),
    )

    # ── Core Fields ───────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    email: Mapped[str] = mapped_column(sa.String(255), nullable=False, unique=True)
    organization: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)

    # Controlled status: active | inactive | blocked
    status: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        default=BuyerStatus.ACTIVE,
        server_default=sa.text("'active'"),
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=sa.func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    negotiations: Mapped[list[Negotiation]] = relationship(
        "Negotiation",
        back_populates="buyer",
        # NO CASCADE: financial history must not be deleted with buyer
        lazy="select",
    )

    # ── Table Arguments ───────────────────────────────────────────────────────
    __table_args__ = (
        sa.Index("idx_buyers_status", "status"),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'blocked')",
            name="ck_buyer_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<Buyer id={self.id} name={self.name!r} status={self.status!r}>"
