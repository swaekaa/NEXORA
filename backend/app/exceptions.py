"""
NEXORA Backend — Domain Exception Hierarchy

Establishes the pattern for all business-logic exceptions.
Business logic is NOT implemented here — only the exception types and their
HTTP mapping contract.

How to use:
    raise PolicyViolationError("Unit price below merchant minimum")

FastAPI exception handlers in main.py convert these to structured JSON responses.
"""
from __future__ import annotations

from typing import Any


class NexoraError(Exception):
    """
    Base class for all NEXORA domain exceptions.

    Attributes:
        message: Human-readable description (safe to surface in API response).
        code:    Machine-readable error code (e.g. "POLICY_VIOLATION").
        detail:  Optional structured context for the error.
    """

    # Subclasses set this to control the default HTTP status code
    http_status: int = 500
    default_code: str = "NEXORA_ERROR"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        self.detail = detail or {}

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the standard NEXORA error response shape."""
        payload: dict[str, Any] = {
            "error": self.code,
            "message": self.message,
        }
        if self.detail:
            payload["detail"] = self.detail
        return payload


# ── 400-range: Client / Business-Logic Errors ─────────────────────────────────

class ValidationError(NexoraError):
    """Raised when input data fails schema validation outside of Pydantic."""
    http_status = 422
    default_code = "VALIDATION_ERROR"


class PolicyViolationError(NexoraError):
    """
    Raised when a proposed agreement violates one or more policy rules.
    This is the primary exception thrown by the Policy Engine (Phase 4).

    detail should include:
        rule_name, expected, actual, reason
    """
    http_status = 400
    default_code = "POLICY_VIOLATION"


class AgreementValidationError(NexoraError):
    """
    Raised when an agreement fails integrity checks
    (e.g. unit_price * quantity ≠ total_amount).
    """
    http_status = 400
    default_code = "AGREEMENT_VALIDATION_ERROR"


class PaymentValidationError(NexoraError):
    """
    Raised when a payment amount does not match the authorised agreement amount.
    This is Failure Case 1 — never allow money to flow for a mismatched amount.
    """
    http_status = 400
    default_code = "PAYMENT_VALIDATION_ERROR"


class WebhookValidationError(NexoraError):
    """
    Raised when a webhook fails signature verification.
    This is Failure Case 6.
    """
    http_status = 400
    default_code = "WEBHOOK_VALIDATION_ERROR"


class AuthorizationRequiredError(NexoraError):
    """
    Raised when a transaction exceeds the merchant's autonomous limit
    and must be approved by a human.
    This is Failure Case 3.
    """
    http_status = 202  # Accepted but not yet actioned
    default_code = "HUMAN_APPROVAL_REQUIRED"


class ResourceNotFoundError(NexoraError):
    """Raised when a requested resource does not exist."""
    http_status = 404
    default_code = "NOT_FOUND"


class InvalidStateTransitionError(NexoraError):
    """
    Raised when a state machine (Negotiation, Agreement) receives an
    illegal transition request.
    """
    http_status = 409
    default_code = "INVALID_STATE_TRANSITION"


class DuplicateResourceError(NexoraError):
    """Raised when creating a resource that already exists (idempotency guard)."""
    http_status = 409
    default_code = "DUPLICATE_RESOURCE"


# ── 500-range: Internal / Infrastructure Errors ───────────────────────────────

class DatabaseError(NexoraError):
    """Raised for unexpected database-layer failures."""
    http_status = 500
    default_code = "DATABASE_ERROR"


class ConfigurationError(NexoraError):
    """Raised when required configuration is missing or invalid at startup."""
    http_status = 500
    default_code = "CONFIGURATION_ERROR"
