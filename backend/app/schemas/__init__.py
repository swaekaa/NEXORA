"""
NEXORA — Pydantic Schemas
All monetary fields use Decimal — never float.

Phase 3 (complete):
  - ProductCreate, ProductUpdate, ProductResponse, ProductListResponse
  - PolicyCreate, PolicyUpdate, PolicyResponse, PolicyListResponse
"""
from app.schemas.product import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)
from app.schemas.policy import (
    PolicyCreate,
    PolicyListResponse,
    PolicyResponse,
    PolicyUpdate,
)

__all__ = [
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    "ProductListResponse",
    "PolicyCreate",
    "PolicyUpdate",
    "PolicyResponse",
    "PolicyListResponse",
]
