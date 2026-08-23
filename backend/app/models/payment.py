"""
NEXORA — Payment ORM Model

Payment represents the financial execution layer — what actually happened
with money (via Razorpay).

Three truths in NEXORA:
    NegotiationMessage → "What did the agents say?"
    Agreement          → "What did they actually agree to?"
    Payment            → "What financially happened?"    ← THIS MODEL

Payment records the Razorpay order/payment lifecycle.
One Agreement → Zero or One Payment (a payment is created when payment is initiated).

Key design decisions:
  - razorpay_order_id: UNIQUE, NOT NULL — created when payment is initiated
  - razorpay_payment_id: UNIQUE, nullable — only exists after Razorpay processes
  - amount: NUMERIC(18,2) — must match agreement.total_amount (validated in Phase 9)
  - amount_paise: Integer copy in paise for Razorpay API (1 INR = 100 paise)

Payment Consistency Rule:
    Payment.amount MUST equal Agreement.total_amount
    This is validated by the payment authorization layer (Phase 9).
    The database model makes this comparison straightforward.

Deletion rule:
    Agreement → Payment: RESTRICT
    We cannot delete an agreement while a payment exists.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.agreement import Agreement


class PaymentStatus(str, Enum):
    """
    Controlled payment status values mirroring the Razorpay order lifecycle.

    State transitions:
        created → authorized → captured (terminal)
        created → failed (terminal)
        captured → refunded (terminal)
        created → cancelled (terminal)
    """
    CREATED = "created"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


_VALID_PAYMENT_STATUSES = ", ".join(f"'{s.value}'" for s in PaymentStatus)


class Payment(Base):
    """
    Razorpay payment record linked to an Agreement.

    Maps:
        NEXORA Agreement → Razorpay Order → Razorpay Payment

    Immutable fields:
        id, agreement_id, razorpay_order_id, amount, currency, created_at

    Mutable fields (via controlled state transitions):
        razorpay_payment_id (set once when payment captured)
        status
        captured_at
        updated_at
    """
    __tablename__ = "payments"

    # ── Primary Key ──────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa.text("gen_random_uuid()"),
    )

    # ── Foreign Key ───────────────────────────────────────────────────────────
    agreement_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        # RESTRICT: cannot delete agreement with payment
        sa.ForeignKey("agreements.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,  # One agreement → one payment
    )

    # ── Razorpay Identifiers ──────────────────────────────────────────────────
    # Created when Razorpay order is created (payment initiation)
    # format: order_XXXXXXXXXXXXXXXX
    razorpay_order_id: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        unique=True,
    )

    # Created when payment is captured by Razorpay
    # format: pay_XXXXXXXXXXXXXXXX
    # Nullable: does not exist until Razorpay confirms capture
    razorpay_payment_id: Mapped[str | None] = mapped_column(
        sa.String(255),
        nullable=True,
        unique=True,
    )

    # ── Financial Fields ──────────────────────────────────────────────────────
    # Must match Agreement.total_amount exactly (validated before creating payment)
    amount: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=18, scale=2, asdecimal=True),
        nullable=False,
    )
    # amount in paise for Razorpay API (Razorpay uses smallest currency unit)
    # For INR: amount_paise = int(amount * 100)
    amount_paise: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        nullable=True,
    )
    currency: Mapped[str] = mapped_column(
        sa.CHAR(3),
        nullable=False,
        default="INR",
        server_default=sa.text("'INR'"),
    )

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        default=PaymentStatus.CREATED.value,
        server_default=sa.text("'created'"),
    )
    captured_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
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
    agreement: Mapped[Agreement] = relationship(
        "Agreement",
        back_populates="payment",
    )

    # ── Table Arguments ───────────────────────────────────────────────────────
    __table_args__ = (
        sa.Index("idx_payments_agreement_id", "agreement_id"),
        sa.Index("idx_payments_razorpay_order_id", "razorpay_order_id"),
        sa.Index("idx_payments_status", "status"),
        sa.CheckConstraint("amount > 0", name="ck_payment_amount_positive"),
        sa.CheckConstraint(
            f"status IN ({_VALID_PAYMENT_STATUSES})",
            name="ck_payment_status",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Payment id={self.id} status={self.status!r} "
            f"amount={self.amount} order={self.razorpay_order_id!r}>"
        )
