"""
NEXORA — Policy ORM Model

Policy defines what the Merchant Agent is authorized to negotiate.
It is the deterministic rule set consumed by the Policy Engine (Phase 4).

Design principles:
  - ALL financial constraints are explicit typed columns — NOT opaque JSON
  - JSONB is only used for extensible non-financial data (future use)
  - A merchant may have multiple named policies (e.g., "Holiday Policy", "Default Policy")
  - Only ONE policy may be active per merchant at a time
  - Policy is CASCADE-deleted with its merchant

Key fields that the Policy Engine reads:
    minimum_price                  → MERCHANT_MIN_PRICE rule
    maximum_discount_percent       → MERCHANT_MAX_DISCOUNT rule
    maximum_autonomous_transaction → AUTONOMOUS_LIMIT rule
    human_approval_required        → always requires human approval (override)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.merchant import Merchant


class Policy(Base):
    """
    Merchant policy — defines the financial authorization envelope for the Merchant Agent.

    Financial fields:
        minimum_price:                  lowest unit price the merchant will accept
        maximum_discount_percent:       max % discount the agent can offer (0.00–100.00)
        maximum_autonomous_transaction: agent can authorize ≤ this without human approval

    All percentage fields use NUMERIC(5, 2) — e.g., 8.00 means 8%.
    All monetary fields use NUMERIC(18, 2) — INR paise-accurate.
    """
    __tablename__ = "policies"

    # ── Primary Key ──────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa.text("gen_random_uuid()"),
    )

    # ── Foreign Key ───────────────────────────────────────────────────────────
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        default="Default Policy",
    )

    # ── Financial Constraints (ALL deterministic, typed) ──────────────────────
    # The lowest unit price the merchant will accept (INR)
    minimum_price: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=18, scale=2, asdecimal=True),
        nullable=False,
    )

    # Maximum discount the agent can offer (0.00 to 100.00)
    maximum_discount_percent: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=5, scale=2, asdecimal=True),
        nullable=False,
        default=Decimal("0.00"),
        server_default=sa.text("0.00"),
    )

    # Agent can autonomously authorize transactions ≤ this amount (INR)
    maximum_autonomous_transaction: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=18, scale=2, asdecimal=True),
        nullable=False,
    )

    # If True, ALL transactions require human approval regardless of amount
    human_approval_required: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("false"),
    )

    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=True,
        server_default=sa.text("true"),
    )

    # ── Operational Limits (non-financial, extensible later) ──────────────────
    max_negotiation_rounds: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=10,
        server_default=sa.text("10"),
    )
    max_delivery_days: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=7,
        server_default=sa.text("7"),
    )
    min_warranty_months: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=12,
        server_default=sa.text("12"),
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
    merchant: Mapped[Merchant] = relationship(
        "Merchant",
        back_populates="policies",
    )

    # ── Table Arguments ───────────────────────────────────────────────────────
    __table_args__ = (
        sa.Index("idx_policies_merchant_id", "merchant_id"),
        sa.CheckConstraint(
            "minimum_price > 0",
            name="ck_policy_minimum_price_positive",
        ),
        sa.CheckConstraint(
            "maximum_discount_percent >= 0 AND maximum_discount_percent <= 100",
            name="ck_policy_discount_range",
        ),
        sa.CheckConstraint(
            "maximum_autonomous_transaction > 0",
            name="ck_policy_autonomous_limit_positive",
        ),
        sa.CheckConstraint(
            "max_negotiation_rounds > 0",
            name="ck_policy_max_rounds_positive",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Policy id={self.id} merchant_id={self.merchant_id} "
            f"name={self.name!r} active={self.is_active}>"
        )
