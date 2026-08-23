"""
NEXORA — Product Service

Business logic and database access for the Merchant Catalog Product API.

Responsibilities:
  - Merchant existence validation
  - Product ownership enforcement (merchant_id in SQL WHERE clause)
  - Async SQLAlchemy 2.0 queries (select, execute, scalars)
  - IntegrityError translation to domain exceptions
  - Soft-delete (deactivate) instead of hard-delete
    Reason: Product → Agreement has RESTRICT FK. Products with agreement history
    cannot be hard-deleted. We set status="inactive" instead.
  - Transaction management (rollback on error)

All monetary values are Decimal throughout — no float conversion.
"""
from __future__ import annotations

import logging
import uuid

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import DatabaseError, DuplicateResourceError, ResourceNotFoundError
from app.models.merchant import Merchant
from app.models.product import Product, ProductStatus
from app.schemas.product import ProductCreate, ProductUpdate

logger = logging.getLogger(__name__)


# ── Internal Helpers ──────────────────────────────────────────────────────────

async def _get_merchant_or_404(session: AsyncSession, merchant_id: uuid.UUID) -> Merchant:
    """
    Fetch merchant by ID or raise ResourceNotFoundError.
    Called before any product operation to verify the merchant exists.
    """
    result = await session.execute(
        sa.select(Merchant).where(Merchant.id == merchant_id)
    )
    merchant = result.scalar_one_or_none()
    if merchant is None:
        raise ResourceNotFoundError(
            f"Merchant {merchant_id} not found",
            detail={"merchant_id": str(merchant_id)},
        )
    return merchant


async def _get_product_or_404(
    session: AsyncSession,
    product_id: uuid.UUID,
    merchant_id: uuid.UUID,
) -> Product:
    """
    Fetch a product by ID AND merchant_id (ownership enforced in SQL).
    Returns 404 whether the product doesn't exist OR belongs to another merchant.
    This prevents leaking the existence of another merchant's resources.
    """
    result = await session.execute(
        sa.select(Product).where(
            Product.id == product_id,
            Product.merchant_id == merchant_id,
        )
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise ResourceNotFoundError(
            f"Product {product_id} not found",
            detail={"product_id": str(product_id), "merchant_id": str(merchant_id)},
        )
    return product


def _handle_integrity_error(exc: IntegrityError, merchant_id: uuid.UUID) -> None:
    """
    Translate PostgreSQL IntegrityErrors into clean domain exceptions.
    Inspects the constraint name to produce a meaningful error message.
    """
    error_str = str(exc.orig).lower()

    if "uq_product_merchant_sku" in error_str or "unique" in error_str and "sku" in error_str:
        raise DuplicateResourceError(
            "A product with this SKU already exists for this merchant",
            detail={"merchant_id": str(merchant_id), "constraint": "uq_product_merchant_sku"},
        )
    if "ck_product_price_positive" in error_str or "price" in error_str:
        raise DatabaseError(
            "Product price violates database constraint (must be > 0)",
            detail={"constraint": "ck_product_price_positive"},
        )
    if "ck_product_inventory_non_negative" in error_str or "inventory" in error_str:
        raise DatabaseError(
            "Product inventory violates database constraint (must be >= 0)",
            detail={"constraint": "ck_product_inventory_non_negative"},
        )
    # Unknown integrity error — do not expose raw DB details
    raise DatabaseError(
        "Database constraint violation",
        detail={"error": "integrity_error"},
    )


# ── Service Functions ─────────────────────────────────────────────────────────

async def create_product(
    session: AsyncSession,
    merchant_id: uuid.UUID,
    payload: ProductCreate,
) -> Product:
    """
    Create a new product for the given merchant.

    Flow:
      1. Verify merchant exists (404 if not)
      2. Build Product ORM instance
      3. Add to session and flush (triggers DB constraints)
      4. Commit and refresh
      5. Return ORM object

    Raises:
      ResourceNotFoundError: merchant not found
      DuplicateResourceError: duplicate SKU for same merchant
      DatabaseError: unexpected constraint violation
    """
    await _get_merchant_or_404(session, merchant_id)

    product = Product(
        merchant_id=merchant_id,
        name=payload.name,
        description=payload.description,
        sku=payload.sku,
        price=payload.price,
        currency=payload.currency,
        inventory=payload.inventory,
        status=payload.status,
    )
    session.add(product)

    try:
        await session.flush()
        await session.commit()
        await session.refresh(product)
    except IntegrityError as exc:
        await session.rollback()
        _handle_integrity_error(exc, merchant_id)

    logger.info(
        "product_created | merchant_id=%s product_id=%s sku=%s",
        merchant_id,
        product.id,
        product.sku,
    )
    return product


async def list_products(
    session: AsyncSession,
    merchant_id: uuid.UUID,
) -> list[Product]:
    """
    List all products belonging to a merchant, ordered by creation time (newest first).

    Filtering is performed in PostgreSQL (WHERE merchant_id = ?),
    NOT in Python. No full table scan.

    Pagination: not implemented in Phase 3. Planned for Phase 5+.
    """
    await _get_merchant_or_404(session, merchant_id)

    result = await session.execute(
        sa.select(Product)
        .where(Product.merchant_id == merchant_id)
        .order_by(Product.created_at.desc())
    )
    return list(result.scalars().all())


async def get_product(
    session: AsyncSession,
    merchant_id: uuid.UUID,
    product_id: uuid.UUID,
) -> Product:
    """
    Retrieve a single product by ID, enforcing merchant ownership in the SQL query.

    Returns 404 if the product does not exist OR belongs to a different merchant.
    This is intentional: cross-merchant resource existence must not be leaked.
    """
    await _get_merchant_or_404(session, merchant_id)
    return await _get_product_or_404(session, product_id, merchant_id)


async def update_product(
    session: AsyncSession,
    merchant_id: uuid.UUID,
    product_id: uuid.UUID,
    payload: ProductUpdate,
) -> Product:
    """
    Partially update a product (PATCH semantics).

    Only fields explicitly set in the payload are applied.
    Uses exclude_unset=True so omitted fields are not touched.

    Protected fields (never updated):
      id, merchant_id, created_at

    Raises:
      ResourceNotFoundError: merchant or product not found
      DuplicateResourceError: duplicate SKU attempted
      DatabaseError: unexpected constraint violation
    """
    await _get_merchant_or_404(session, merchant_id)
    product = await _get_product_or_404(session, product_id, merchant_id)

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        # Nothing to update — return as-is
        return product

    for field, value in update_data.items():
        setattr(product, field, value)

    try:
        await session.flush()
        await session.commit()
        await session.refresh(product)
    except IntegrityError as exc:
        await session.rollback()
        _handle_integrity_error(exc, merchant_id)

    logger.info(
        "product_updated | merchant_id=%s product_id=%s fields=%s",
        merchant_id,
        product_id,
        list(update_data.keys()),
    )
    return product


async def deactivate_product(
    session: AsyncSession,
    merchant_id: uuid.UUID,
    product_id: uuid.UUID,
) -> None:
    """
    Soft-delete a product by setting status = 'inactive'.

    WHY SOFT DELETE:
    The Product → Agreement relationship has a RESTRICT foreign key.
    PostgreSQL will refuse to hard-delete a product that is referenced by
    any Agreement record. Since NEXORA must preserve financial history,
    we deactivate instead of hard-deleting.

    After deactivation:
      - Product no longer appears in 'active' catalog listings
      - Agreement history referencing this product remains intact
      - The product can be reactivated if needed

    Raises:
      ResourceNotFoundError: merchant or product not found
    """
    await _get_merchant_or_404(session, merchant_id)
    product = await _get_product_or_404(session, product_id, merchant_id)

    product.status = ProductStatus.INACTIVE
    await session.commit()

    logger.info(
        "product_deactivated | merchant_id=%s product_id=%s",
        merchant_id,
        product_id,
    )
