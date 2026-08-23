"""
NEXORA — Negotiation ORM Model

Negotiation is the LIFECYCLE / STATE MACHINE for a buyer-merchant interaction.

IMPORTANT: Negotiation is NOT the message history.
The actual agent-to-agent exchange is stored in NegotiationMessage.
This model tracks WHERE the negotiation is in its lifecycle.

State machine:
    discover → request → offer → counter_offer → accepted
                                              ↘ rejected
                                              ↘ expired

State transitions are controlled — arbitrary LLM-generated state strings
are rejected by the CHECK constraint.

Deletion rules:
    Merchant → Negotiation: RESTRICT (no deleting merchants with history)
    Buyer → Negotiation:    RESTRICT (no deleting buyers with history)
    Negotiation → Messages: CASCADE (messages are part of negotiation)
    Negotiation → Agreement: RESTRICT (cannot delete negotiation if agreement exists)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.buyer import Buyer
    from app.models.merchant import Merchant
    from app.models.product import Product
    from app.models.negotiation_message import NegotiationMessage
    from app.models.agreement import Agreement


class NegotiationState(str, Enum):
    """
    Controlled negotiation state values.
    Using str Enum so values are stable strings when stored / compared.

    State diagram:
        DISCOVER → REQUEST → OFFER ↔ COUNTER_OFFER → ACCEPTED
                                                   → REJECTED
        Any state can transition to EXPIRED
    """
    DISCOVER = "discover"
    REQUEST = "request"
    OFFER = "offer"
    COUNTER_OFFER = "counter_offer"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


# Terminal states — no transitions allowed FROM these (module-level, not in Enum body)
NEGOTIATION_TERMINAL_STATES: frozenset[NegotiationState] = frozenset({
    NegotiationState.ACCEPTED,
    NegotiationState.REJECTED,
    NegotiationState.EXPIRED,
})

# Attach to enum class for convenience
NegotiationState.TERMINAL_STATES = NEGOTIATION_TERMINAL_STATES  # type: ignore[attr-defined]

# All valid state string values — used in DB CHECK constraint
_VALID_STATES = ", ".join(f"'{s.value}'" for s in NegotiationState)


class Negotiation(Base):
    """
    Negotiation lifecycle tracker.

    Records WHO is negotiating, on WHAT, and WHERE the negotiation currently stands.
    The actual exchange content is in NegotiationMessage.

    Immutable fields:
        id, buyer_id, merchant_id, product_id, started_at, created_at

    Mutable fields:
        state, round_count, ended_at, expires_at, updated_at
    """
    __tablename__ = "negotiations"

    # ── Primary Key ──────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa.text("gen_random_uuid()"),
    )

    # ── Foreign Keys ──────────────────────────────────────────────────────────
    buyer_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        # RESTRICT: do not delete buyer with negotiations
        sa.ForeignKey("buyers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        # RESTRICT: do not delete merchant with negotiations
        sa.ForeignKey("merchants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        # RESTRICT: do not delete product being negotiated
        sa.ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # ── State Machine ─────────────────────────────────────────────────────────
    state: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        default=NegotiationState.DISCOVER.value,
        server_default=sa.text("'discover'"),
    )

    # How many negotiation rounds have occurred
    round_count: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
        server_default=sa.text("0"),
    )
    max_rounds: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=10,
        server_default=sa.text("10"),
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    started_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=sa.func.now(),
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True),
        nullable=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True),
        nullable=True,
    )
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
    buyer: Mapped[Buyer] = relationship("Buyer", back_populates="negotiations")
    merchant: Mapped[Merchant] = relationship("Merchant", back_populates="negotiations")
    product: Mapped[Product] = relationship("Product", lazy="select")

    messages: Mapped[list[NegotiationMessage]] = relationship(
        "NegotiationMessage",
        back_populates="negotiation",
        cascade="all, delete-orphan",   # CASCADE: messages owned by negotiation
        order_by="NegotiationMessage.sequence_number",
        lazy="select",
    )
    agreement: Mapped[Agreement | None] = relationship(
        "Agreement",
        back_populates="negotiation",
        # NO CASCADE: cannot delete negotiation while agreement exists
        uselist=False,
        lazy="select",
    )

    # ── Table Arguments ───────────────────────────────────────────────────────
    __table_args__ = (
        sa.Index("idx_negotiations_buyer_id", "buyer_id"),
        sa.Index("idx_negotiations_merchant_id", "merchant_id"),
        sa.Index("idx_negotiations_state", "state"),
        sa.CheckConstraint(
            f"state IN ({_VALID_STATES})",
            name="ck_negotiation_state",
        ),
        sa.CheckConstraint(
            "round_count >= 0",
            name="ck_negotiation_round_count_non_negative",
        ),
        sa.CheckConstraint(
            "max_rounds > 0",
            name="ck_negotiation_max_rounds_positive",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Negotiation id={self.id} state={self.state!r} "
            f"buyer_id={self.buyer_id} merchant_id={self.merchant_id}>"
        )
