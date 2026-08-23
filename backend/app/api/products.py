"""
NEXORA — Product API Router

HTTP routes for merchant product management.
All routes enforce merchant ownership via the service layer.

Endpoints:
  POST   /api/v1/merchants/{merchant_id}/products
  GET    /api/v1/merchants/{merchant_id}/products
  GET    /api/v1/merchants/{merchant_id}/products/{product_id}
  PATCH  /api/v1/merchants/{merchant_id}/products/{product_id}
  DELETE /api/v1/merchants/{merchant_id}/products/{product_id}

DELETE semantics: soft-delete (status → inactive), not hard-delete.
Reason: Product → Agreement has a RESTRICT FK; products with agreement
history cannot be physically removed.

Authentication: not implemented in Phase 3 (planned for Phase 6).
The merchant_id path parameter acts as the resource identifier.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.schemas.product import ProductCreate, ProductListResponse, ProductResponse, ProductUpdate
from app.services import product_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/merchants/{merchant_id}/products",
    tags=["products"],
)


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create product",
    description=(
        "Create a new product in the merchant's catalog. "
        "SKU must be unique per merchant. "
        "Price must be a positive Decimal value."
    ),
    responses={
        201: {"description": "Product created"},
        404: {"description": "Merchant not found"},
        409: {"description": "Duplicate SKU for this merchant"},
        422: {"description": "Validation error (invalid price, currency, etc.)"},
    },
)
async def create_product(
    merchant_id: uuid.UUID,
    payload: ProductCreate,
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    product = await product_service.create_product(
        session=db,
        merchant_id=merchant_id,
        payload=payload,
    )
    return ProductResponse.model_validate(product)


@router.get(
    "",
    response_model=ProductListResponse,
    status_code=status.HTTP_200_OK,
    summary="List products",
    description=(
        "List all products belonging to the specified merchant. "
        "Results are ordered by creation date (newest first). "
        "Filtering is enforced at the database level — cross-merchant products are never returned."
    ),
    responses={
        200: {"description": "List of products"},
        404: {"description": "Merchant not found"},
    },
)
async def list_products(
    merchant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ProductListResponse:
    products = await product_service.list_products(session=db, merchant_id=merchant_id)
    return ProductListResponse(
        items=[ProductResponse.model_validate(p) for p in products],
        total=len(products),
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Get product",
    description=(
        "Retrieve a single product by ID. "
        "Returns 404 if the product does not exist OR belongs to a different merchant. "
        "Cross-merchant resource existence is never leaked."
    ),
    responses={
        200: {"description": "Product details"},
        404: {"description": "Product not found or not accessible"},
    },
)
async def get_product(
    merchant_id: uuid.UUID,
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    product = await product_service.get_product(
        session=db,
        merchant_id=merchant_id,
        product_id=product_id,
    )
    return ProductResponse.model_validate(product)


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Update product",
    description=(
        "Partially update a product (PATCH semantics). "
        "Only provided fields are updated. "
        "id, merchant_id, created_at cannot be modified. "
        "SKU changes are allowed but must remain unique per merchant."
    ),
    responses={
        200: {"description": "Updated product"},
        404: {"description": "Merchant or product not found"},
        409: {"description": "Duplicate SKU"},
        422: {"description": "Validation error"},
    },
)
async def update_product(
    merchant_id: uuid.UUID,
    product_id: uuid.UUID,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    product = await product_service.update_product(
        session=db,
        merchant_id=merchant_id,
        product_id=product_id,
        payload=payload,
    )
    return ProductResponse.model_validate(product)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Deactivate product",
    description=(
        "Soft-delete a product by setting its status to 'inactive'. "
        "Hard deletion is not supported because products may be referenced by "
        "historical Agreement records (RESTRICT foreign key). "
        "Deactivated products are excluded from active catalog listings."
    ),
    responses={
        404: {"description": "Merchant or product not found"},
    },
)
async def deactivate_product(
    merchant_id: uuid.UUID,
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    await product_service.deactivate_product(
        session=db,
        merchant_id=merchant_id,
        product_id=product_id,
    )
