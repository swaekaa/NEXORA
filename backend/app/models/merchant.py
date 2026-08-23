"""
NEXORA — Merchant ORM Model

Merchant represents a business that sells products via NEXORA.
It is the parent of Policy and Product objects.

Deletion rules:
  - Merchant → Policy:        CASCADE (policies are owned by the merchant)
  - Merchant → Product:       CASCADE (products are owned by the merchant)
  - Merchant → Negotiation:   RESTRICT (do not delete a merchant with financial history)

Status values are controlled strings, not booleans, to allow for 'suspended'
as a distinct state from merely 'inactive'.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.policy import Policy
    from app.models.product import Product
    from app.models.negotiation import Negotiation


class MerchantStatus:
    """Controlled status values for Merchant. Not a DB enum — stored as VARCHAR."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

    ALL = {ACTIVE, INACTIVE, SUSPENDED}


class Merchant(Base):
    """
    Business entity that sells products through NEXORA.

    Immutable fields:
        id, created_at

    Mutable fields:
        name, description, status, updated_at
    """
    __tablename__ = "merchants"

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
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    # Controlled status: active | inactive | suspended
    status: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        default=MerchantStatus.ACTIVE,
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
    policies: Mapped[list[Policy]] = relationship(
        "Policy",
        back_populates="merchant",
        cascade="all, delete-orphan",   # CASCADE: policies owned by merchant
        lazy="select",
    )
    products: Mapped[list[Product]] = relationship(
        "Product",
        back_populates="merchant",
        cascade="all, delete-orphan",   # CASCADE: products owned by merchant
        lazy="select",
    )
    negotiations: Mapped[list[Negotiation]] = relationship(
        "Negotiation",
        back_populates="merchant",
        # NO CASCADE: financial history must not be deleted
        # Deleting a merchant with negotiations raises IntegrityError
        lazy="select",
    )

    # ── Table Arguments ───────────────────────────────────────────────────────
    __table_args__ = (
        sa.Index("idx_merchants_status", "status"),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'suspended')",
            name="ck_merchant_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<Merchant id={self.id} name={self.name!r} status={self.status!r}>"
