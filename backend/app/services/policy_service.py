"""
NEXORA — Policy Service

Business logic and database access for the Merchant Catalog Policy API.

Key rules enforced here:
  1. ONE ACTIVE POLICY PER MERCHANT:
     When creating or activating a policy, the service automatically deactivates
     any existing active policy for that merchant. This is a hard constraint from
     the Policy model docstring and the Policy Engine specification.

  2. OWNERSHIP IN SQL:
     All queries filter by merchant_id in the WHERE clause — not in Python.

  3. HARD DELETE SUPPORTED:
     Unlike Products, Policies have no FK relationship to Agreements.
     Agreements snapshot the agreed terms; the policy that authorized them is
     not referenced. Hard delete is therefore safe. We also provide a
     deactivate (soft-disable) path via PATCH.

  4. ALL FINANCIAL VALUES ARE DECIMAL:
     minimum_price, maximum_discount_percent, maximum_autonomous_transaction
     are never coerced to float.
"""
from __future__ import annotations

import logging
import uuid

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import DatabaseError, DuplicateResourceError, ResourceNotFoundError
from app.models.merchant import Merchant
from app.models.policy import Policy
from app.schemas.policy import PolicyCreate, PolicyUpdate

logger = logging.getLogger(__name__)


# ── Internal Helpers ──────────────────────────────────────────────────────────

async def _get_merchant_or_404(session: AsyncSession, merchant_id: uuid.UUID) -> Merchant:
    """Fetch merchant or raise ResourceNotFoundError."""
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


async def _get_policy_or_404(
    session: AsyncSession,
    policy_id: uuid.UUID,
    merchant_id: uuid.UUID,
) -> Policy:
    """
    Fetch a policy enforcing ownership in SQL.
    Returns 404 whether the policy doesn't exist OR belongs to another merchant.
    """
    result = await session.execute(
        sa.select(Policy).where(
            Policy.id == policy_id,
            Policy.merchant_id == merchant_id,
        )
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        raise ResourceNotFoundError(
            f"Policy {policy_id} not found",
            detail={"policy_id": str(policy_id), "merchant_id": str(merchant_id)},
        )
    return policy


async def _deactivate_existing_active_policies(
    session: AsyncSession,
    merchant_id: uuid.UUID,
    exclude_policy_id: uuid.UUID | None = None,
) -> None:
    """
    Deactivate all currently active policies for a merchant.

    Called when creating a new active policy or activating an existing one.
    This enforces the ONE ACTIVE POLICY PER MERCHANT constraint.

    Args:
        exclude_policy_id: skip this policy (used when activating an existing policy
                           to avoid deactivating the one we're about to activate)
    """
    query = sa.select(Policy).where(
        Policy.merchant_id == merchant_id,
        Policy.is_active == True,  # noqa: E712
    )
    if exclude_policy_id is not None:
        query = query.where(Policy.id != exclude_policy_id)

    result = await session.execute(query)
    active_policies = result.scalars().all()

    for policy in active_policies:
        policy.is_active = False
        logger.info(
            "policy_deactivated_by_new_active | merchant_id=%s policy_id=%s",
            merchant_id,
            policy.id,
        )

    if active_policies:
        await session.flush()


def _handle_integrity_error(exc: IntegrityError, merchant_id: uuid.UUID) -> None:
    """Translate PostgreSQL IntegrityErrors to domain exceptions."""
    error_str = str(exc.orig).lower()

    if "ck_policy_minimum_price_positive" in error_str or ("minimum_price" in error_str and "positive" in error_str):
        raise DatabaseError(
            "minimum_price must be greater than 0",
            detail={"constraint": "ck_policy_minimum_price_positive"},
        )
    if "ck_policy_discount_range" in error_str:
        raise DatabaseError(
            "maximum_discount_percent must be between 0 and 100",
            detail={"constraint": "ck_policy_discount_range"},
        )
    if "ck_policy_autonomous_limit_positive" in error_str:
        raise DatabaseError(
            "maximum_autonomous_transaction must be greater than 0",
            detail={"constraint": "ck_policy_autonomous_limit_positive"},
        )
    raise DatabaseError(
        "Database constraint violation",
        detail={"error": "integrity_error"},
    )


# ── Service Functions ─────────────────────────────────────────────────────────

async def create_policy(
    session: AsyncSession,
    merchant_id: uuid.UUID,
    payload: PolicyCreate,
) -> Policy:
    """
    Create a new policy for the given merchant.

    If is_active=True (default), any existing active policy is automatically
    deactivated first. This enforces the ONE ACTIVE POLICY PER MERCHANT rule.

    Flow:
      1. Verify merchant exists
      2. If new policy is_active=True, deactivate existing active policies
      3. Build Policy ORM instance
      4. Commit and refresh
      5. Return ORM object
    """
    await _get_merchant_or_404(session, merchant_id)

    if payload.is_active:
        await _deactivate_existing_active_policies(session, merchant_id)

    policy = Policy(
        merchant_id=merchant_id,
        name=payload.name,
        minimum_price=payload.minimum_price,
        maximum_discount_percent=payload.maximum_discount_percent,
        maximum_autonomous_transaction=payload.maximum_autonomous_transaction,
        human_approval_required=payload.human_approval_required,
        is_active=payload.is_active,
        max_negotiation_rounds=payload.max_negotiation_rounds,
        max_delivery_days=payload.max_delivery_days,
        min_warranty_months=payload.min_warranty_months,
    )
    session.add(policy)

    try:
        await session.flush()
        await session.commit()
        await session.refresh(policy)
    except IntegrityError as exc:
        await session.rollback()
        _handle_integrity_error(exc, merchant_id)

    logger.info(
        "policy_created | merchant_id=%s policy_id=%s name=%r is_active=%s",
        merchant_id,
        policy.id,
        policy.name,
        policy.is_active,
    )
    return policy


async def list_policies(
    session: AsyncSession,
    merchant_id: uuid.UUID,
) -> list[Policy]:
    """
    List all policies belonging to a merchant, ordered newest first.
    Filtering is in PostgreSQL — not Python.
    """
    await _get_merchant_or_404(session, merchant_id)

    result = await session.execute(
        sa.select(Policy)
        .where(Policy.merchant_id == merchant_id)
        .order_by(Policy.created_at.desc())
    )
    return list(result.scalars().all())


async def get_policy(
    session: AsyncSession,
    merchant_id: uuid.UUID,
    policy_id: uuid.UUID,
) -> Policy:
    """
    Retrieve a single policy, enforcing merchant ownership in SQL.
    Returns 404 if not found or not owned by merchant.
    """
    await _get_merchant_or_404(session, merchant_id)
    return await _get_policy_or_404(session, policy_id, merchant_id)


async def update_policy(
    session: AsyncSession,
    merchant_id: uuid.UUID,
    policy_id: uuid.UUID,
    payload: PolicyUpdate,
) -> Policy:
    """
    Partially update a policy (PATCH semantics).

    If is_active is set to True, existing active policies are deactivated first.
    Uses exclude_unset=True — only provided fields are applied.

    Protected fields (never updated): id, merchant_id, created_at
    """
    await _get_merchant_or_404(session, merchant_id)
    policy = await _get_policy_or_404(session, policy_id, merchant_id)

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        return policy

    # If activating this policy, deactivate others first
    if update_data.get("is_active") is True:
        await _deactivate_existing_active_policies(
            session, merchant_id, exclude_policy_id=policy_id
        )

    for field, value in update_data.items():
        setattr(policy, field, value)

    try:
        await session.flush()
        await session.commit()
        await session.refresh(policy)
    except IntegrityError as exc:
        await session.rollback()
        _handle_integrity_error(exc, merchant_id)

    logger.info(
        "policy_updated | merchant_id=%s policy_id=%s fields=%s",
        merchant_id,
        policy_id,
        list(update_data.keys()),
    )
    return policy


async def delete_policy(
    session: AsyncSession,
    merchant_id: uuid.UUID,
    policy_id: uuid.UUID,
) -> None:
    """
    Hard-delete a policy.

    WHY HARD DELETE (unlike Products):
    Policies have no FK relationship to Agreements. Agreements snapshot their
    negotiated terms directly (unit_price, quantity). The Policy that authorized
    those terms is not referenced by FK, so deleting it is safe.

    If the deleted policy was active, no new active policy is automatically
    created — the merchant must create or activate a new one.

    Raises:
      ResourceNotFoundError: merchant or policy not found
    """
    await _get_merchant_or_404(session, merchant_id)
    policy = await _get_policy_or_404(session, policy_id, merchant_id)

    await session.delete(policy)
    await session.commit()

    logger.info(
        "policy_deleted | merchant_id=%s policy_id=%s",
        merchant_id,
        policy_id,
    )
