"""
NEXORA — Inventory Reservation ORM Model

Tracks the lifecycle of inventory allocated to a specific agreement.

Reservation Status Lifecycle:
RESERVED  -> COMMITTED (Payment captured)
RESERVED  -> RELEASED  (Razorpay error, payment failure)
RESERVED  -> EXPIRED   (TTL exceeded)
COMMITTED -> FULFILLED (Merchant ships)

Terminal States: COMMITTED, RELEASED, EXPIRED, FULFILLED
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
    from app.models.agreement import Agreement
    from app.models.product import Product


class ReservationStatus(str, Enum):
    """Controlled status values for Inventory Reservation."""
    RESERVED = "reserved"
    COMMITTED = "committed"
    RELEASED = "released"
    EXPIRED = "expired"
    FULFILLED = "fulfilled"

    # Terminal states (cannot transition OUT of these states)
    # Note: FULFILLED is the terminal state of COMMITTED. 
    # But COMMITTED can only transition to FULFILLED.
    # RELEASED and EXPIRED are absolutely terminal.
    
    @classmethod
    def get_terminal_states(cls) -> set[str]:
        return {cls.RELEASED.value, cls.EXPIRED.value, cls.FULFILLED.value}


class InventoryReservation(Base):
    """
    Tracks inventory reserved for an Agreement.
    """
    __tablename__ = "inventory_reservations"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa.text("gen_random_uuid()"),
    )

    agreement_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("agreements.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,  # 1 reservation per agreement
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        default=ReservationStatus.RESERVED.value,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
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
    agreement: Mapped[Agreement] = relationship(
        "Agreement",
        backref="inventory_reservation",
    )
    product: Mapped[Product] = relationship(
        "Product",
    )

    # ── Table Arguments ───────────────────────────────────────────────────────
    __table_args__ = (
        sa.CheckConstraint(
            "quantity > 0",
            name="ck_inventory_reservation_quantity_positive",
        ),
        sa.CheckConstraint(
            "status IN ('reserved', 'committed', 'released', 'expired', 'fulfilled')",
            name="ck_inventory_reservation_status",
        ),
        sa.Index("idx_inventory_reservations_status", "status"),
        sa.Index("idx_inventory_reservations_expires_at", "expires_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<InventoryReservation id={self.id} "
            f"agreement_id={self.agreement_id} "
            f"qty={self.quantity} status={self.status}>"
        )
