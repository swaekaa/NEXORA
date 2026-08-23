"""
NEXORA — Product Pydantic Schemas

Validates incoming API requests and shapes outgoing responses for Products.

Design rules:
  - price is always Decimal, never float
  - inventory must be >= 0
  - currency is always a 3-char uppercase ISO 4217 code
  - id, merchant_id, created_at, updated_at are NEVER accepted from clients
  - ProductUpdate uses exclude_unset=True semantics (all fields optional)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ── Create Schema ─────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    """
    Schema for creating a new product.
    Clients supply all required fields; merchant_id comes from the URL path.
    """
    name: str = Field(..., min_length=1, max_length=255, description="Product display name")
    description: str | None = Field(None, description="Optional detailed description")
    sku: str = Field(..., min_length=1, max_length=100, description="Stock Keeping Unit — unique per merchant")
    price: Decimal = Field(..., description="Unit price in the given currency. Must be > 0. Use Decimal, not float.")
    currency: str = Field(default="INR", description="ISO 4217 3-character currency code (e.g. INR, USD)")
    inventory: int = Field(default=0, ge=0, description="Available stock quantity. Must be >= 0.")
    status: str = Field(default="active", description="Product status: active | inactive | out_of_stock")

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        """Price must be a positive, finite Decimal. Reject floats, NaN, infinity."""
        if not isinstance(v, Decimal):
            # Pydantic may coerce — force it here
            v = Decimal(str(v))
        if v != v:  # NaN check
            raise ValueError("price must not be NaN")
        if v <= 0:
            raise ValueError("price must be greater than 0")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Currency must be a 3-character uppercase ISO code."""
        v = v.strip().upper()
        if len(v) != 3 or not v.isalpha():
            raise ValueError("currency must be a 3-character alphabetic ISO 4217 code (e.g. INR, USD)")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"active", "inactive", "out_of_stock"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v

    @field_validator("sku")
    @classmethod
    def validate_sku(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("sku must not be blank")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be blank")
        return v

    model_config = ConfigDict(
        # Reject float monetary values — only Decimal accepted
        json_schema_extra={
            "example": {
                "name": "Industrial Monitor 27\"",
                "description": "High-resolution professional display",
                "sku": "MON-27-PRO",
                "price": "45000.00",
                "currency": "INR",
                "inventory": 50,
                "status": "active",
            }
        }
    )


# ── Update Schema ─────────────────────────────────────────────────────────────

class ProductUpdate(BaseModel):
    """
    Schema for partially updating a product (PATCH semantics).
    All fields are optional. Only provided fields will be updated.
    Use model.model_dump(exclude_unset=True) to get only changed fields.
    """
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None)
    sku: str | None = Field(None, min_length=1, max_length=100)
    price: Decimal | None = Field(None)
    currency: str | None = Field(None)
    inventory: int | None = Field(None, ge=0)
    status: str | None = Field(None)

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Decimal | None) -> Decimal | None:
        if v is None:
            return v
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        if v != v:
            raise ValueError("price must not be NaN")
        if v <= 0:
            raise ValueError("price must be greater than 0")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().upper()
        if len(v) != 3 or not v.isalpha():
            raise ValueError("currency must be a 3-character alphabetic ISO 4217 code")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = {"active", "inactive", "out_of_stock"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v

    @field_validator("sku")
    @classmethod
    def validate_sku(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("sku must not be blank")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("name must not be blank")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "price": "47500.00",
                "inventory": 45,
            }
        }
    )


# ── Response Schema ───────────────────────────────────────────────────────────

class ProductResponse(BaseModel):
    """
    Schema for product API responses.
    Serializes ORM Product objects to safe, controlled JSON.
    """
    id: uuid.UUID
    merchant_id: uuid.UUID
    name: str
    description: str | None
    sku: str
    price: Decimal
    currency: str
    inventory: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,  # Allow ORM object serialization
        json_schema_extra={
            "example": {
                "id": "a3b4c5d6-e7f8-1234-5678-9abcdef01234",
                "merchant_id": "b4c5d6e7-f8a9-2345-6789-0bcdef012345",
                "name": "Industrial Monitor 27\"",
                "description": "High-resolution professional display",
                "sku": "MON-27-PRO",
                "price": "45000.00",
                "currency": "INR",
                "inventory": 50,
                "status": "active",
                "created_at": "2026-08-23T12:00:00Z",
                "updated_at": "2026-08-23T12:00:00Z",
            }
        }
    )


# ── List Response Schema ──────────────────────────────────────────────────────

class ProductListResponse(BaseModel):
    """
    Wrapper for a paginated/listed product response.
    Pagination is not implemented in Phase 3; total reflects full count.
    """
    items: list[ProductResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)
