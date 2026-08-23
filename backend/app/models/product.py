"""
NEXORA — Product ORM Model

Product belongs to a Merchant and is what gets negotiated and sold.

Design decisions:
  - SKU is unique PER MERCHANT, not globally:
        UNIQUE(merchant_id, sku)
    Two merchants can have "MONITOR-001"; that is not a conflict.
  - Price stored as NUMERIC(18,2) — never float
  - Inventory must be >= 0 (CHECK constraint)
  - Price must be > 0 (CHECK constraint)
  - Status is controlled to prevent arbitrary LLM strings

Agreement Snapshot Principle:
    The Agreement captures unit_price at the time of agreement.
    If the product price later changes, historical agreements are unaffected.
    Products own their current catalog price; agreements own their agreed price.

Deletion rule:
    Merchant → Product: CASCADE
    Product → Agreement: RESTRICT (cannot delete a product with agreement history)
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
    from app.models.agreement import Agreement


class ProductStatus:
    """Controlled status values for Product."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"

    ALL = {ACTIVE, INACTIVE, OUT_OF_STOCK}


class Product(Base):
    """
    Catalog product sold by a Merchant.

    Immutable fields:
        id, merchant_id, sku, created_at

    Mutable fields:
        name, description, price, currency, inventory, status, updated_at
    """
    __tablename__ = "products"

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

    # ── Core Fields ───────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    # SKU is unique per merchant (not globally)
    sku: Mapped[str] = mapped_column(sa.String(100), nullable=False)

    # ── Financial Fields (NUMERIC only, never float) ──────────────────────────
    price: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=18, scale=2, asdecimal=True),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        sa.CHAR(3),
        nullable=False,
        default="INR",
        server_default=sa.text("'INR'"),
    )

    # ── Inventory ─────────────────────────────────────────────────────────────
    inventory: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
        server_default=sa.text("0"),
    )

    # Controlled status: active | inactive | out_of_stock
    status: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        default=ProductStatus.ACTIVE,
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
    merchant: Mapped[Merchant] = relationship(
        "Merchant",
        back_populates="products",
    )
    agreements: Mapped[list[Agreement]] = relationship(
        "Agreement",
        back_populates="product",
        # NO CASCADE: financial history must not be deleted
        lazy="select",
    )

    # ── Table Arguments ───────────────────────────────────────────────────────
    __table_args__ = (
        # SKU unique per merchant (not globally)
        sa.UniqueConstraint("merchant_id", "sku", name="uq_product_merchant_sku"),
        sa.Index("idx_products_merchant_id", "merchant_id"),
        sa.Index("idx_products_status", "status"),
        sa.CheckConstraint(
            "price > 0",
            name="ck_product_price_positive",
        ),
        sa.CheckConstraint(
            "inventory >= 0",
            name="ck_product_inventory_non_negative",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'out_of_stock')",
            name="ck_product_status",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Product id={self.id} sku={self.sku!r} "
            f"price={self.price} status={self.status!r}>"
        )
