"""
NEXORA — Catalog Router

Top-level entry point for the Phase 3 Merchant Catalog API.
Aggregates the products and policies sub-routers under a single import.

This file is referenced in main.py as:
    from app.api.catalog import router as catalog_router
    app.include_router(catalog_router, prefix="/api/v1")

Final URL structure:
    /api/v1/merchants/{merchant_id}/products
    /api/v1/merchants/{merchant_id}/products/{product_id}
    /api/v1/merchants/{merchant_id}/policies
    /api/v1/merchants/{merchant_id}/policies/{policy_id}
"""
from fastapi import APIRouter

from app.api.products import router as products_router
from app.api.policies import router as policies_router

router = APIRouter()

router.include_router(products_router)
router.include_router(policies_router)
