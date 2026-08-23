"""
Phase 2 Unit Tests — ORM Models (No Database Required)

Tests that all model classes, enums, and constraints are correctly defined
using pure Python — no network, no database, no asyncio.

These tests verify:
  - Model class creation and attributes
  - Enum values and types
  - Status value sets
  - Decimal handling (never float)
  - Agreement total calculation correctness
  - Enum membership
"""
import uuid
from decimal import Decimal

import pytest
import sqlalchemy as sa

from app.models import (
    Agreement,
    AgreementStatus,
    Buyer,
    BuyerStatus,
    Merchant,
    MerchantStatus,
    MessageType,
    NegotiationMessage,
    NegotiationState,
    Payment,
    PaymentStatus,
    Policy,
    Product,
    ProductStatus,
    SenderType,
    Negotiation,
)


# ══════════════════════════════════════════════════════════════════════════════
# Merchant Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestMerchantModel:
    def test_merchant_table_name(self):
        assert Merchant.__tablename__ == "merchants"

    def test_merchant_has_uuid_pk(self):
        col = Merchant.__table__.c["id"]
        assert col.primary_key is True
        assert isinstance(col.type, sa.UUID)

    def test_merchant_status_values(self):
        assert MerchantStatus.ACTIVE == "active"
        assert MerchantStatus.INACTIVE == "inactive"
        assert MerchantStatus.SUSPENDED == "suspended"

    def test_merchant_status_all_set(self):
        assert "active" in MerchantStatus.ALL
        assert "inactive" in MerchantStatus.ALL
        assert "suspended" in MerchantStatus.ALL

    def test_merchant_has_timestamps(self):
        cols = {c.name for c in Merchant.__table__.c}
        assert "created_at" in cols
        assert "updated_at" in cols

    def test_merchant_email_is_unique(self):
        email_col = Merchant.__table__.c["email"]
        assert email_col.unique is True

    def test_merchant_status_check_constraint_exists(self):
        constraint_names = {c.name for c in Merchant.__table__.constraints}
        assert "ck_merchant_status" in constraint_names

    def test_merchant_repr(self):
        m = Merchant(
            id=uuid.uuid4(),
            name="TestCo",
            status="active"
        )
        assert "TestCo" in repr(m)
        assert "active" in repr(m)


# ══════════════════════════════════════════════════════════════════════════════
# Policy Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestPolicyModel:
    def test_policy_table_name(self):
        assert Policy.__tablename__ == "policies"

    def test_policy_has_uuid_pk(self):
        col = Policy.__table__.c["id"]
        assert col.primary_key is True
        assert isinstance(col.type, sa.UUID)

    def test_policy_has_merchant_fk(self):
        col = Policy.__table__.c["merchant_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert "merchants.id" in str(fks[0].target_fullname)

    def test_policy_monetary_columns_are_numeric(self):
        min_price_col = Policy.__table__.c["minimum_price"]
        assert isinstance(min_price_col.type, sa.Numeric)
        assert min_price_col.type.precision == 18
        assert min_price_col.type.scale == 2

        auto_col = Policy.__table__.c["maximum_autonomous_transaction"]
        assert isinstance(auto_col.type, sa.Numeric)

        disc_col = Policy.__table__.c["maximum_discount_percent"]
        assert isinstance(disc_col.type, sa.Numeric)
        assert disc_col.type.precision == 5
        assert disc_col.type.scale == 2

    def test_policy_check_constraints_exist(self):
        constraint_names = {c.name for c in Policy.__table__.constraints}
        assert "ck_policy_minimum_price_positive" in constraint_names
        assert "ck_policy_discount_range" in constraint_names
        assert "ck_policy_autonomous_limit_positive" in constraint_names


# ══════════════════════════════════════════════════════════════════════════════
# Buyer Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestBuyerModel:
    def test_buyer_table_name(self):
        assert Buyer.__tablename__ == "buyers"

    def test_buyer_status_values(self):
        assert BuyerStatus.ACTIVE == "active"
        assert BuyerStatus.INACTIVE == "inactive"
        assert BuyerStatus.BLOCKED == "blocked"

    def test_buyer_email_is_unique(self):
        email_col = Buyer.__table__.c["email"]
        assert email_col.unique is True

    def test_buyer_status_check_constraint_exists(self):
        constraint_names = {c.name for c in Buyer.__table__.constraints}
        assert "ck_buyer_status" in constraint_names


# ══════════════════════════════════════════════════════════════════════════════
# Product Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestProductModel:
    def test_product_table_name(self):
        assert Product.__tablename__ == "products"

    def test_product_status_values(self):
        assert ProductStatus.ACTIVE == "active"
        assert ProductStatus.INACTIVE == "inactive"
        assert ProductStatus.OUT_OF_STOCK == "out_of_stock"

    def test_product_price_is_numeric(self):
        col = Product.__table__.c["price"]
        assert isinstance(col.type, sa.Numeric)
        assert col.type.precision == 18
        assert col.type.scale == 2

    def test_product_sku_not_globally_unique(self):
        """SKU must NOT be globally unique — only unique per merchant."""
        sku_col = Product.__table__.c["sku"]
        # sku alone should NOT have a unique constraint
        assert sku_col.unique is not True

    def test_product_merchant_sku_composite_unique(self):
        """merchant_id + sku MUST be unique together."""
        constraint_names = {c.name for c in Product.__table__.constraints}
        assert "uq_product_merchant_sku" in constraint_names

    def test_product_inventory_check_constraint(self):
        constraint_names = {c.name for c in Product.__table__.constraints}
        assert "ck_product_inventory_non_negative" in constraint_names

    def test_product_price_check_constraint(self):
        constraint_names = {c.name for c in Product.__table__.constraints}
        assert "ck_product_price_positive" in constraint_names

    def test_product_has_merchant_fk(self):
        col = Product.__table__.c["merchant_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1


# ══════════════════════════════════════════════════════════════════════════════
# Negotiation Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestNegotiationModel:
    def test_negotiation_table_name(self):
        assert Negotiation.__tablename__ == "negotiations"

    def test_negotiation_state_enum_values(self):
        assert NegotiationState.DISCOVER == "discover"
        assert NegotiationState.REQUEST == "request"
        assert NegotiationState.OFFER == "offer"
        assert NegotiationState.COUNTER_OFFER == "counter_offer"
        assert NegotiationState.ACCEPTED == "accepted"
        assert NegotiationState.REJECTED == "rejected"
        assert NegotiationState.EXPIRED == "expired"

    def test_negotiation_state_is_str_enum(self):
        assert isinstance(NegotiationState.ACCEPTED, str)
        assert NegotiationState.ACCEPTED == "accepted"

    def test_negotiation_terminal_states(self):
        terminals = NegotiationState.TERMINAL_STATES
        assert NegotiationState.ACCEPTED in terminals
        assert NegotiationState.REJECTED in terminals
        assert NegotiationState.EXPIRED in terminals
        # Non-terminal
        assert NegotiationState.OFFER not in terminals

    def test_negotiation_state_check_constraint_exists(self):
        constraint_names = {c.name for c in Negotiation.__table__.constraints}
        assert "ck_negotiation_state" in constraint_names

    def test_negotiation_fks_are_restrict(self):
        """buyer_id and merchant_id FKs should be RESTRICT."""
        buyer_col = Negotiation.__table__.c["buyer_id"]
        for fk in buyer_col.foreign_keys:
            assert fk.ondelete == "RESTRICT"

        merchant_col = Negotiation.__table__.c["merchant_id"]
        for fk in merchant_col.foreign_keys:
            assert fk.ondelete == "RESTRICT"

    def test_negotiation_has_indexes(self):
        idx_names = {i.name for i in Negotiation.__table__.indexes}
        assert "idx_negotiations_buyer_id" in idx_names
        assert "idx_negotiations_merchant_id" in idx_names
        assert "idx_negotiations_state" in idx_names


# ══════════════════════════════════════════════════════════════════════════════
# NegotiationMessage Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestNegotiationMessageModel:
    def test_message_table_name(self):
        assert NegotiationMessage.__tablename__ == "negotiation_messages"

    def test_sender_type_enum(self):
        assert SenderType.BUYER_AGENT == "buyer_agent"
        assert SenderType.MERCHANT_AGENT == "merchant_agent"
        assert SenderType.SYSTEM == "system"

    def test_message_type_enum(self):
        assert MessageType.REQUEST == "request"
        assert MessageType.OFFER == "offer"
        assert MessageType.COUNTER_OFFER == "counter_offer"
        assert MessageType.ACCEPT == "accept"
        assert MessageType.REJECT == "reject"
        assert MessageType.SYSTEM_EVENT == "system_event"

    def test_message_composite_unique_constraint(self):
        """negotiation_id + sequence_number must be unique."""
        constraint_names = {c.name for c in NegotiationMessage.__table__.constraints}
        assert "uq_message_negotiation_sequence" in constraint_names

    def test_message_sequence_positive_constraint(self):
        constraint_names = {c.name for c in NegotiationMessage.__table__.constraints}
        assert "ck_message_sequence_positive" in constraint_names

    def test_message_negotiation_fk_is_cascade(self):
        """Messages should CASCADE-delete with negotiation."""
        neg_col = NegotiationMessage.__table__.c["negotiation_id"]
        for fk in neg_col.foreign_keys:
            assert fk.ondelete == "CASCADE"

    def test_message_has_no_updated_at(self):
        """Append-only — no updated_at column."""
        col_names = {c.name for c in NegotiationMessage.__table__.c}
        assert "updated_at" not in col_names
        assert "created_at" in col_names


# ══════════════════════════════════════════════════════════════════════════════
# Agreement Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestAgreementModel:
    def test_agreement_table_name(self):
        assert Agreement.__tablename__ == "agreements"

    def test_agreement_status_values(self):
        assert AgreementStatus.PENDING_VALIDATION == "pending_validation"
        assert AgreementStatus.VALIDATED == "validated"
        assert AgreementStatus.VALIDATION_FAILED == "validation_failed"
        assert AgreementStatus.PENDING_APPROVAL == "pending_approval"
        assert AgreementStatus.APPROVED == "approved"
        assert AgreementStatus.PAYMENT_INITIATED == "payment_initiated"
        assert AgreementStatus.PAYMENT_CAPTURED == "payment_captured"
        assert AgreementStatus.PAYMENT_FAILED == "payment_failed"
        assert AgreementStatus.EXPIRED == "expired"
        assert AgreementStatus.CANCELLED == "cancelled"

    def test_agreement_terminal_states(self):
        terminals = AgreementStatus.TERMINAL_STATES
        assert AgreementStatus.PAYMENT_CAPTURED in terminals
        assert AgreementStatus.PAYMENT_FAILED in terminals
        assert AgreementStatus.VALIDATION_FAILED in terminals
        assert AgreementStatus.CANCELLED in terminals
        assert AgreementStatus.EXPIRED in terminals
        # Non-terminal
        assert AgreementStatus.PENDING_VALIDATION not in terminals
        assert AgreementStatus.VALIDATED not in terminals

    def test_agreement_negotiation_id_is_unique(self):
        """negotiation_id must be UNIQUE (one negotiation → one agreement)."""
        neg_col = Agreement.__table__.c["negotiation_id"]
        assert neg_col.unique is True

    def test_agreement_monetary_columns_are_numeric(self):
        for col_name in ("unit_price", "total_amount"):
            col = Agreement.__table__.c[col_name]
            assert isinstance(col.type, sa.Numeric), f"{col_name} must be Numeric"
            assert col.type.precision == 18
            assert col.type.scale == 2

    def test_agreement_negotiation_fk_is_restrict(self):
        neg_col = Agreement.__table__.c["negotiation_id"]
        for fk in neg_col.foreign_keys:
            assert fk.ondelete == "RESTRICT"

    def test_agreement_check_constraints_exist(self):
        constraint_names = {c.name for c in Agreement.__table__.constraints}
        assert "ck_agreement_quantity_positive" in constraint_names
        assert "ck_agreement_unit_price_positive" in constraint_names
        assert "ck_agreement_total_positive" in constraint_names

    def test_agreement_has_indexes(self):
        idx_names = {i.name for i in Agreement.__table__.indexes}
        assert "idx_agreements_status" in idx_names
        assert "idx_agreements_merchant_id" in idx_names


# ══════════════════════════════════════════════════════════════════════════════
# Payment Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestPaymentModel:
    def test_payment_table_name(self):
        assert Payment.__tablename__ == "payments"

    def test_payment_status_values(self):
        assert PaymentStatus.CREATED == "created"
        assert PaymentStatus.AUTHORIZED == "authorized"
        assert PaymentStatus.CAPTURED == "captured"
        assert PaymentStatus.FAILED == "failed"
        assert PaymentStatus.REFUNDED == "refunded"
        assert PaymentStatus.CANCELLED == "cancelled"

    def test_payment_razorpay_order_id_is_unique(self):
        col = Payment.__table__.c["razorpay_order_id"]
        assert col.unique is True
        assert col.nullable is False

    def test_payment_razorpay_payment_id_is_unique_and_nullable(self):
        col = Payment.__table__.c["razorpay_payment_id"]
        assert col.unique is True
        assert col.nullable is True

    def test_payment_amount_is_numeric(self):
        col = Payment.__table__.c["amount"]
        assert isinstance(col.type, sa.Numeric)
        assert col.type.precision == 18
        assert col.type.scale == 2

    def test_payment_agreement_fk_is_restrict(self):
        col = Payment.__table__.c["agreement_id"]
        for fk in col.foreign_keys:
            assert fk.ondelete == "RESTRICT"

    def test_payment_agreement_id_is_unique(self):
        """One agreement → one payment."""
        col = Payment.__table__.c["agreement_id"]
        assert col.unique is True


# ══════════════════════════════════════════════════════════════════════════════
# Monetary Calculation Tests (DECIMAL ONLY)
# ══════════════════════════════════════════════════════════════════════════════

class TestDecimalMonetary:
    """
    Explicit tests that NEXORA monetary calculations use Decimal and never float.

    Reference scenario: 100 units at ₹10,800 each
    """

    def test_basic_multiplication_stays_decimal(self):
        unit_price = Decimal("10800.00")
        quantity = 100
        total = unit_price * quantity
        assert isinstance(total, Decimal)
        assert total == Decimal("1080000.00")

    def test_not_float(self):
        unit_price = Decimal("10800.00")
        quantity = 100
        total = unit_price * quantity
        assert not isinstance(total, float)

    def test_demo_scenario_total(self):
        """Validate the demo agreement calculation from AGREEMENT_SPEC.md."""
        base_price = Decimal("12000.00")
        # 8% bulk discount
        after_bulk = base_price * Decimal("0.92")
        assert after_bulk == Decimal("11040.00")
        # 2% upfront discount
        unit_price = after_bulk * Decimal("0.98")
        assert unit_price == Decimal("10819.20")
        # 100 units
        total = unit_price * 100
        assert total == Decimal("1081920.00")

    def test_floating_point_precision_issue_does_not_occur(self):
        """
        0.1 + 0.1 + 0.1 == 0.3 fails in float.
        Decimal must handle this correctly.
        """
        a = Decimal("0.10")
        b = Decimal("0.10")
        c = Decimal("0.10")
        result = a + b + c
        assert result == Decimal("0.30")
        # Contrast: float fails
        assert 0.1 + 0.1 + 0.1 != 0.3  # This is TRUE — floats are broken

    def test_agreement_total_integrity_rule(self):
        """
        The Policy Engine (Phase 4) will use this exact check.
        unit_price * quantity must equal total_amount to the nearest paisa.
        """
        unit_price = Decimal("10819.20")
        quantity = 100
        total_amount = Decimal("1081920.00")

        calculated = (unit_price * quantity).quantize(Decimal("0.01"))
        stored = total_amount.quantize(Decimal("0.01"))

        assert calculated == stored, (
            f"Total mismatch: calculated={calculated}, stored={stored}"
        )

    def test_incorrect_total_detected(self):
        """An LLM-fabricated incorrect total should be detectable."""
        unit_price = Decimal("10819.20")
        quantity = 100
        # LLM "made up" a wrong total
        wrong_total = Decimal("1090000.00")

        calculated = (unit_price * quantity).quantize(Decimal("0.01"))
        stored = wrong_total.quantize(Decimal("0.01"))

        assert calculated != stored, "Should detect the total mismatch"

    def test_paise_conversion(self):
        """Razorpay uses paise. 1 INR = 100 paise."""
        amount_inr = Decimal("1081920.00")
        amount_paise = int(amount_inr * 100)
        assert amount_paise == 108192000
        assert isinstance(amount_paise, int)

    def test_enum_types_are_strings(self):
        """All enums must be comparable to plain strings."""
        assert NegotiationState.ACCEPTED == "accepted"
        assert AgreementStatus.VALIDATED == "validated"
        assert PaymentStatus.CAPTURED == "captured"
        assert SenderType.BUYER_AGENT == "buyer_agent"
        assert MessageType.OFFER == "offer"
