"""
NEXORA — ORM Models Package

IMPORTANT: ALL models must be imported here.
Alembic's autogenerate reads Base.metadata, which is only populated
once the model classes are imported and registered with Base.

Import order matters for avoiding circular import issues:
  1. Models with no FK dependencies first (Merchant, Buyer)
  2. Then models that depend on them (Policy, Product)
  3. Then lifecycle models (Negotiation, NegotiationMessage)
  4. Then outcome models (Agreement, Payment)
"""

# ── Tier 1: Root entities (no cross-domain FKs) ───────────────────────────────
from app.models.merchant import Merchant, MerchantStatus
from app.models.buyer import Buyer, BuyerStatus

# ── Tier 2: Merchant-owned entities ──────────────────────────────────────────
from app.models.policy import Policy
from app.models.product import Product, ProductStatus

# ── Tier 3: Lifecycle entities ────────────────────────────────────────────────
from app.models.negotiation import Negotiation, NegotiationState
from app.models.negotiation_message import NegotiationMessage, SenderType, MessageType

# ── Tier 4: Outcome entities ──────────────────────────────────────────────────
from app.models.agreement import Agreement, AgreementStatus
from app.models.payment import Payment, PaymentStatus

__all__ = [
    # Models
    "Merchant",
    "Buyer",
    "Policy",
    "Product",
    "Negotiation",
    "NegotiationMessage",
    "Agreement",
    "Payment",
    # Status / Enum helpers
    "MerchantStatus",
    "BuyerStatus",
    "ProductStatus",
    "NegotiationState",
    "SenderType",
    "MessageType",
    "AgreementStatus",
    "PaymentStatus",
]
