"""
NEXORA — Policy Pydantic Schemas

Validates incoming API requests and shapes outgoing responses for Policies.

Design rules:
  - minimum_price, maximum_discount_percent, maximum_autonomous_transaction → always Decimal
  - maximum_discount_percent must be in range [0, 100]
  - minimum_price must be > 0 (matches DB CHECK constraint)
  - maximum_autonomous_transaction must be > 0 (matches DB CHECK constraint)
  - id, merchant_id, created_at, updated_at are NEVER accepted from clients
  - PolicyUpdate uses exclude_unset=True semantics (all fields optional)

Active Policy Rule (enforced in service layer, not schema):
  Only ONE policy may be active per merchant at a time.
  The service layer deactivates any existing active policy when creating or
  activating a policy.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Create Schema ─────────────────────────────────────────────────────────────

class PolicyCreate(BaseModel):
    """
    Schema for creating a new merchant policy.
    merchant_id comes from the URL path, never from the request body.
    """
    name: str = Field(
        default="Default Policy",
        min_length=1,
        max_length=255,
        description="Human-readable policy name (e.g. 'Holiday Policy')",
    )

    # ── Financial Constraints ─────────────────────────────────────────────────
    minimum_price: Decimal = Field(
        ...,
        description="Lowest unit price the merchant will accept (must be > 0)",
    )
    maximum_discount_percent: Decimal = Field(
        default=Decimal("0.00"),
        description="Maximum discount the agent can offer (0.00 to 100.00)",
    )
    maximum_autonomous_transaction: Decimal = Field(
        ...,
        description="Max transaction value the agent can authorize without human approval (must be > 0)",
    )
    human_approval_required: bool = Field(
        default=False,
        description="If True, ALL transactions require human approval regardless of amount",
    )
    is_active: bool = Field(
        default=True,
        description="Whether this policy is currently active. Only one active policy per merchant.",
    )

    # ── Operational Limits ────────────────────────────────────────────────────
    max_negotiation_rounds: int = Field(
        default=10,
        ge=1,
        description="Maximum negotiation rounds before auto-rejection",
    )
    max_delivery_days: int = Field(
        default=7,
        ge=1,
        description="Maximum acceptable delivery days",
    )
    min_warranty_months: int = Field(
        default=12,
        ge=0,
        description="Minimum warranty duration in months",
    )

    @field_validator("minimum_price")
    @classmethod
    def validate_minimum_price(cls, v: Decimal) -> Decimal:
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        if v != v:  # NaN check
            raise ValueError("minimum_price must not be NaN")
        if v <= 0:
            raise ValueError("minimum_price must be greater than 0")
        return v

    @field_validator("maximum_discount_percent")
    @classmethod
    def validate_max_discount(cls, v: Decimal) -> Decimal:
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        if v != v:
            raise ValueError("maximum_discount_percent must not be NaN")
        if v < 0 or v > 100:
            raise ValueError("maximum_discount_percent must be between 0 and 100 inclusive")
        return v

    @field_validator("maximum_autonomous_transaction")
    @classmethod
    def validate_max_autonomous(cls, v: Decimal) -> Decimal:
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        if v != v:
            raise ValueError("maximum_autonomous_transaction must not be NaN")
        if v <= 0:
            raise ValueError("maximum_autonomous_transaction must be greater than 0")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Default Policy",
                "minimum_price": "40000.00",
                "maximum_discount_percent": "10.00",
                "maximum_autonomous_transaction": "500000.00",
                "human_approval_required": False,
                "is_active": True,
                "max_negotiation_rounds": 10,
                "max_delivery_days": 7,
                "min_warranty_months": 12,
            }
        }
    )


# ── Update Schema ─────────────────────────────────────────────────────────────

class PolicyUpdate(BaseModel):
    """
    Schema for partially updating a policy (PATCH semantics).
    All fields optional — only provided fields are updated.
    Use model.model_dump(exclude_unset=True).
    """
    name: str | None = Field(None, min_length=1, max_length=255)
    minimum_price: Decimal | None = Field(None)
    maximum_discount_percent: Decimal | None = Field(None)
    maximum_autonomous_transaction: Decimal | None = Field(None)
    human_approval_required: bool | None = Field(None)
    is_active: bool | None = Field(None)
    max_negotiation_rounds: int | None = Field(None, ge=1)
    max_delivery_days: int | None = Field(None, ge=1)
    min_warranty_months: int | None = Field(None, ge=0)

    @field_validator("minimum_price")
    @classmethod
    def validate_minimum_price(cls, v: Decimal | None) -> Decimal | None:
        if v is None:
            return v
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        if v <= 0:
            raise ValueError("minimum_price must be greater than 0")
        return v

    @field_validator("maximum_discount_percent")
    @classmethod
    def validate_max_discount(cls, v: Decimal | None) -> Decimal | None:
        if v is None:
            return v
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        if v < 0 or v > 100:
            raise ValueError("maximum_discount_percent must be between 0 and 100 inclusive")
        return v

    @field_validator("maximum_autonomous_transaction")
    @classmethod
    def validate_max_autonomous(cls, v: Decimal | None) -> Decimal | None:
        if v is None:
            return v
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        if v <= 0:
            raise ValueError("maximum_autonomous_transaction must be greater than 0")
        return v


# ── Response Schema ───────────────────────────────────────────────────────────

class PolicyResponse(BaseModel):
    """
    Schema for policy API responses.
    Serializes ORM Policy objects to controlled JSON output.
    """
    id: uuid.UUID
    merchant_id: uuid.UUID
    name: str
    minimum_price: Decimal
    maximum_discount_percent: Decimal
    maximum_autonomous_transaction: Decimal
    human_approval_required: bool
    is_active: bool
    max_negotiation_rounds: int
    max_delivery_days: int
    min_warranty_months: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "a3b4c5d6-e7f8-1234-5678-9abcdef01234",
                "merchant_id": "b4c5d6e7-f8a9-2345-6789-0bcdef012345",
                "name": "Default Policy",
                "minimum_price": "40000.00",
                "maximum_discount_percent": "10.00",
                "maximum_autonomous_transaction": "500000.00",
                "human_approval_required": False,
                "is_active": True,
                "max_negotiation_rounds": 10,
                "max_delivery_days": 7,
                "min_warranty_months": 12,
                "created_at": "2026-08-23T12:00:00Z",
                "updated_at": "2026-08-23T12:00:00Z",
            }
        }
    )


# ── List Response Schema ──────────────────────────────────────────────────────

class PolicyListResponse(BaseModel):
    """Wrapper for a list of policy responses."""
    items: list[PolicyResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)
