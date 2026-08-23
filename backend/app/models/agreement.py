"""
NEXORA — Agreement ORM Model

Agreement is the most important entity in the NEXORA financial model.
It is the CANONICAL COMMERCIAL TRUTH for a transaction.

Three truths in NEXORA:
    NegotiationMessage → "What did the agents say?"
    Agreement          → "What did they actually agree to?"    ← THIS MODEL
    Payment            → "What financially happened?"

Agreement Snapshot Principle (CRITICAL):
    Agreement stores its own unit_price, quantity, total_amount, currency.
    It does NOT reference the current Product price.
    If the Product price changes after agreement, the Agreement is unaffected.
    This is intentional denormalization for historical correctness.

Immutability Rules:
    The following fields MUST NOT change after creation:
        id, merchant_id, buyer_id, negotiation_id, product_id
        quantity, unit_price, total_amount, currency, payment_terms
        product_name (snapshot at time of agreement)
    These fields may change via controlled state transitions only:
        status, policy_decision, policy_checks, payment fields

Agreement Total Integrity:
    The Policy Engine (Phase 4) validates:
        calculated_total = quantity * unit_price (using Decimal)
        stored_total = total_amount
        They must match exactly to the nearest paisa (0.01).

Agreement Hash (future tamper-detection):
    SHA-256 of: f"{quantity}|{unit_price}|{total_amount}|{currency}|{payment_terms}"

Deletion rule:
    Negotiation → Agreement: RESTRICT
    Agreement → Payment: RESTRICT
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.negotiation import Negotiation
    from app.models.merchant import Merchant
    from app.models.buyer import Buyer
    from app.models.product import Product
    from app.models.payment import Payment


class AgreementStatus(str, Enum):
    """
    Controlled agreement status values.
    Only valid transitions (per AGREEMENT_SPEC.md) are allowed in application code.

    Terminal states (no outbound transitions):
        PAYMENT_CAPTURED, PAYMENT_FAILED, VALIDATION_FAILED, CANCELLED, EXPIRED
    """
    PENDING_VALIDATION = "pending_validation"
    VALIDATED = "validated"
    VALIDATION_FAILED = "validation_failed"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    PAYMENT_INITIATED = "payment_initiated"
    PAYMENT_CAPTURED = "payment_captured"
    PAYMENT_FAILED = "payment_failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


# Terminal states — no outbound transitions allowed from these
AGREEMENT_TERMINAL_STATES: frozenset[AgreementStatus] = frozenset({
    AgreementStatus.PAYMENT_CAPTURED,
    AgreementStatus.PAYMENT_FAILED,
    AgreementStatus.VALIDATION_FAILED,
    AgreementStatus.CANCELLED,
    AgreementStatus.EXPIRED,
})

# Attach to enum as a class-level constant for convenience
AgreementStatus.TERMINAL_STATES = AGREEMENT_TERMINAL_STATES  # type: ignore[attr-defined]

# All valid status string values — used in DB CHECK constraint
_ALL_AGREEMENT_STATUS_VALUES = ", ".join(f"'{s.value}'" for s in AgreementStatus)


class Agreement(Base):
    """
    Canonical commercial agreement — the financial truth of a NEXORA transaction.

    Created once when negotiation reaches ACCEPTED state.
    Commercial term fields are immutable after creation.
    Status transitions only via AgreementService (Phase 8).

    Note on Razorpay fields:
        razorpay_order_id and razorpay_payment_id are NOT stored here.
        They live in the Payment table.
        This enforces the separation: what was agreed vs what financially happened.
    """
    __tablename__ = "agreements"

    # ── Primary Key ──────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa.text("gen_random_uuid()"),
    )

    # ── Foreign Keys ──────────────────────────────────────────────────────────
    # One negotiation → exactly one agreement (UNIQUE enforces 1:1)
    negotiation_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("negotiations.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,  # One negotiation can only produce one agreement
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("merchants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    buyer_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("buyers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # ── Product Snapshot (immutable after creation) ────────────────────────────
    # Captures product name at agreement time — survives product renames
    product_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)

    # ── Commercial Terms (IMMUTABLE AFTER CREATION) ──────────────────────────
    quantity: Mapped[int] = mapped_column(sa.Integer, nullable=False)

    # Price negotiated — NOT the current product price
    unit_price: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=18, scale=2, asdecimal=True),
        nullable=False,
    )
    # Must equal quantity * unit_price (validated by Policy Engine)
    total_amount: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=18, scale=2, asdecimal=True),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        sa.CHAR(3),
        nullable=False,
        default="INR",
        server_default=sa.text("'INR'"),
    )
    payment_terms: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
    )

    # ── Delivery & Warranty Terms (immutable after creation) ──────────────────
    delivery_days: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    warranty_months: Mapped[int] = mapped_column(sa.Integer, nullable=False)

    # ── Applied Discounts Snapshot (JSONB, for audit/display only) ────────────
    # The canonical price is unit_price — discounts_applied is informational
    discounts_applied: Mapped[dict[str, Any] | None] = mapped_column(
        sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql"),
        nullable=True,
    )

    # ── Policy Validation Results (set once by Policy Engine) ─────────────────
    policy_decision: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    policy_checks: Mapped[dict[str, Any] | None] = mapped_column(
        sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql"),
        nullable=True,
    )
    policy_validated_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    blocking_reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    # ── Integrity Hash (future tamper-detection) ───────────────────────────────
    # SHA-256 of: f"{quantity}|{unit_price}|{total_amount}|{currency}|{payment_terms}"
    agreement_hash: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        sa.String(30),
        nullable=False,
        default=AgreementStatus.PENDING_VALIDATION.value,
        server_default=sa.text("'pending_validation'"),
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    # Note: Agreement has created_at and updated_at.
    # The status field changes via controlled transitions — updated_at reflects these.
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
    negotiation: Mapped[Negotiation] = relationship(
        "Negotiation", back_populates="agreement"
    )
    merchant: Mapped[Merchant] = relationship("Merchant", lazy="select")
    buyer: Mapped[Buyer] = relationship("Buyer", lazy="select")
    product: Mapped[Product] = relationship("Product", back_populates="agreements")
    payment: Mapped[Payment | None] = relationship(
        "Payment",
        back_populates="agreement",
        uselist=False,  # One agreement → one payment
        lazy="select",
    )

    # ── Table Arguments ───────────────────────────────────────────────────────
    __table_args__ = (
        sa.Index("idx_agreements_negotiation_id", "negotiation_id"),
        sa.Index("idx_agreements_merchant_id", "merchant_id"),
        sa.Index("idx_agreements_buyer_id", "buyer_id"),
        sa.Index("idx_agreements_status", "status"),
        sa.CheckConstraint("quantity > 0", name="ck_agreement_quantity_positive"),
        sa.CheckConstraint("unit_price > 0", name="ck_agreement_unit_price_positive"),
        sa.CheckConstraint("total_amount > 0", name="ck_agreement_total_positive"),
        sa.CheckConstraint("delivery_days > 0", name="ck_agreement_delivery_positive"),
        sa.CheckConstraint("warranty_months >= 0", name="ck_agreement_warranty_non_negative"),
    )

    def __repr__(self) -> str:
        return (
            f"<Agreement id={self.id} status={self.status!r} "
            f"total={self.total_amount} currency={self.currency}>"
        )
