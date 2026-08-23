"""
NEXORA — Policy API Router

HTTP routes for merchant policy management.
All routes enforce merchant ownership via the service layer.

Endpoints:
  POST   /api/v1/merchants/{merchant_id}/policies
  GET    /api/v1/merchants/{merchant_id}/policies
  GET    /api/v1/merchants/{merchant_id}/policies/{policy_id}
  PATCH  /api/v1/merchants/{merchant_id}/policies/{policy_id}
  DELETE /api/v1/merchants/{merchant_id}/policies/{policy_id}

Active Policy Rule:
  Only ONE policy may be active per merchant at a time.
  Creating or activating a policy automatically deactivates any existing active policy.
  This is enforced in the service layer, not in the router.

DELETE semantics: hard-delete.
Policies have no FK to Agreements (agreements snapshot their terms directly),
so hard deletion is safe. Use PATCH to deactivate without deleting.

Authentication: not implemented in Phase 3 (planned for Phase 6).
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.schemas.policy import PolicyCreate, PolicyListResponse, PolicyResponse, PolicyUpdate
from app.services import policy_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/merchants/{merchant_id}/policies",
    tags=["policies"],
)


@router.post(
    "",
    response_model=PolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create policy",
    description=(
        "Create a new negotiation policy for the merchant. "
        "If is_active=True (default), any existing active policy is automatically deactivated. "
        "Only one policy may be active per merchant at a time."
    ),
    responses={
        201: {"description": "Policy created"},
        404: {"description": "Merchant not found"},
        422: {"description": "Validation error (invalid financial values)"},
    },
)
async def create_policy(
    merchant_id: uuid.UUID,
    payload: PolicyCreate,
    db: AsyncSession = Depends(get_db),
) -> PolicyResponse:
    policy = await policy_service.create_policy(
        session=db,
        merchant_id=merchant_id,
        payload=payload,
    )
    return PolicyResponse.model_validate(policy)


@router.get(
    "",
    response_model=PolicyListResponse,
    status_code=status.HTTP_200_OK,
    summary="List policies",
    description=(
        "List all policies belonging to the specified merchant. "
        "Results are ordered by creation date (newest first). "
        "Includes both active and inactive policies."
    ),
    responses={
        200: {"description": "List of policies"},
        404: {"description": "Merchant not found"},
    },
)
async def list_policies(
    merchant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PolicyListResponse:
    policies = await policy_service.list_policies(session=db, merchant_id=merchant_id)
    return PolicyListResponse(
        items=[PolicyResponse.model_validate(p) for p in policies],
        total=len(policies),
    )


@router.get(
    "/{policy_id}",
    response_model=PolicyResponse,
    status_code=status.HTTP_200_OK,
    summary="Get policy",
    description=(
        "Retrieve a single policy by ID. "
        "Returns 404 if the policy does not exist OR belongs to a different merchant."
    ),
    responses={
        200: {"description": "Policy details"},
        404: {"description": "Policy not found or not accessible"},
    },
)
async def get_policy(
    merchant_id: uuid.UUID,
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PolicyResponse:
    policy = await policy_service.get_policy(
        session=db,
        merchant_id=merchant_id,
        policy_id=policy_id,
    )
    return PolicyResponse.model_validate(policy)


@router.patch(
    "/{policy_id}",
    response_model=PolicyResponse,
    status_code=status.HTTP_200_OK,
    summary="Update policy",
    description=(
        "Partially update a policy (PATCH semantics). "
        "Only provided fields are updated. "
        "Setting is_active=True automatically deactivates any other active policy. "
        "id, merchant_id, created_at cannot be modified."
    ),
    responses={
        200: {"description": "Updated policy"},
        404: {"description": "Merchant or policy not found"},
        422: {"description": "Validation error"},
    },
)
async def update_policy(
    merchant_id: uuid.UUID,
    policy_id: uuid.UUID,
    payload: PolicyUpdate,
    db: AsyncSession = Depends(get_db),
) -> PolicyResponse:
    policy = await policy_service.update_policy(
        session=db,
        merchant_id=merchant_id,
        policy_id=policy_id,
        payload=payload,
    )
    return PolicyResponse.model_validate(policy)


@router.delete(
    "/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete policy",
    description=(
        "Hard-delete a policy. "
        "Unlike products, policies have no FK to Agreements, so hard deletion is safe. "
        "To deactivate without deleting, use PATCH with is_active=false."
    ),
    responses={
        404: {"description": "Merchant or policy not found"},
    },
)
async def delete_policy(
    merchant_id: uuid.UUID,
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    await policy_service.delete_policy(
        session=db,
        merchant_id=merchant_id,
        policy_id=policy_id,
    )
