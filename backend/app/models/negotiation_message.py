"""
NEXORA — NegotiationMessage ORM Model

NegotiationMessage is the IMMUTABLE RECORD of what happened during negotiation.

Three truths in NEXORA:
    NegotiationMessage → "What did the agents say?"
    Agreement          → "What did they actually agree to?"
    Payment            → "What financially happened?"

This model answers the first question. It must NEVER be collapsed into
Agreement or Negotiation.

Key properties:
  - APPEND-ONLY: No UPDATE or DELETE should occur in application code
  - sequence_number provides strict ordering within a negotiation
  - UNIQUE(negotiation_id, sequence_number) prevents duplicate or ambiguous ordering
  - payload (JSONB) stores semi-structured negotiation terms
  - Financial TRUTH never lives only in JSONB — it is copied to Agreement typed columns

JSONB payload structure (example):
    {
        "quantity": 100,
        "unit_price": "10800.00",
        "currency": "INR",
        "delivery_days": 5,
        "warranty_months": 12,
        "payment_terms": "upfront"
    }

Note: prices in payload are STRING to preserve Decimal precision.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.negotiation import Negotiation


class SenderType(str, Enum):
    """Who sent this message."""
    BUYER_AGENT = "buyer_agent"
    MERCHANT_AGENT = "merchant_agent"
    SYSTEM = "system"


class MessageType(str, Enum):
    """What kind of message this is."""
    REQUEST = "request"
    OFFER = "offer"
    COUNTER_OFFER = "counter_offer"
    ACCEPT = "accept"
    REJECT = "reject"
    SYSTEM_EVENT = "system_event"


_VALID_SENDERS = ", ".join(f"'{s.value}'" for s in SenderType)
_VALID_MSG_TYPES = ", ".join(f"'{s.value}'" for s in MessageType)


class NegotiationMessage(Base):
    """
    Immutable record of a single message in the negotiation exchange.

    Append-only — do not provide update/delete in application code.

    sequence_number:
        Strictly ordered within a negotiation.
        UNIQUE(negotiation_id, sequence_number) prevents gaps/duplicates.
        Application code must determine the next sequence number before inserting.

    payload:
        JSONB for semi-structured negotiation terms.
        Prices here are strings (to preserve Decimal).
        This is NOT the canonical financial truth — that lives in Agreement.

    sender_id:
        The identifier of the specific agent instance (e.g., buyer's UUID or system component name).
        This is NOT a foreign key — agents are logical entities, not necessarily DB rows.
    """
    __tablename__ = "negotiation_messages"

    # ── Primary Key ──────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa.text("gen_random_uuid()"),
    )

    # ── Foreign Key ───────────────────────────────────────────────────────────
    negotiation_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        # CASCADE: messages are owned by the negotiation
        sa.ForeignKey("negotiations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Message Classification ─────────────────────────────────────────────
    sender_type: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
    )
    # Logical sender ID — buyer UUID, merchant UUID, or system component name
    sender_id: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
    )
    message_type: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
    )

    # ── Content ───────────────────────────────────────────────────────────────
    # Human-readable content (what the agent "said")
    content: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    # Semi-structured negotiation terms (prices as strings to preserve Decimal)
    # NOT the canonical financial truth — that is Agreement
    payload: Mapped[dict[str, Any] | None] = mapped_column(
        sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql"),
        nullable=True,
    )

    # ── Ordering ──────────────────────────────────────────────────────────────
    # Strictly ordered within a negotiation.
    # Starts at 1. Application code must manage incrementing.
    sequence_number: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
    )

    # ── Timestamp (no updated_at — append-only) ───────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=sa.func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    negotiation: Mapped[Negotiation] = relationship(
        "Negotiation",
        back_populates="messages",
    )

    # ── Table Arguments ───────────────────────────────────────────────────────
    __table_args__ = (
        # Strict ordering — prevents duplicate sequence within a negotiation
        sa.UniqueConstraint(
            "negotiation_id", "sequence_number",
            name="uq_message_negotiation_sequence",
        ),
        sa.Index("idx_messages_negotiation_id", "negotiation_id"),
        sa.CheckConstraint(
            f"sender_type IN ({_VALID_SENDERS})",
            name="ck_message_sender_type",
        ),
        sa.CheckConstraint(
            f"message_type IN ({_VALID_MSG_TYPES})",
            name="ck_message_type",
        ),
        sa.CheckConstraint(
            "sequence_number > 0",
            name="ck_message_sequence_positive",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<NegotiationMessage id={self.id} "
            f"negotiation_id={self.negotiation_id} "
            f"seq={self.sequence_number} type={self.message_type!r}>"
        )
