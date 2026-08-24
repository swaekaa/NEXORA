"""
Phase 4 Unit Tests — Deterministic Policy Engine

Tests the core policy evaluation engine in isolation from the database,
network, and LLM. Verifies that financial logic is strict, Decimal-based,
and correctly applies precedence (DENY > HUMAN_APPROVAL > ALLOW).
"""
import uuid
from decimal import Decimal
import pytest

from app.policies.enums import ActionType, PolicyDecision
from app.policies.models import PolicyEvaluationContext, PolicyEvaluationRequest
from app.policies.engine import PolicyEngine

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def engine() -> PolicyEngine:
    return PolicyEngine()

@pytest.fixture
def base_context() -> PolicyEvaluationContext:
    return PolicyEvaluationContext(
        merchant_id=uuid.uuid4(),
        policy_id=uuid.uuid4(),
        minimum_price=Decimal("10500.00"),
        maximum_discount_percent=Decimal("10.00"),
        maximum_autonomous_transaction=Decimal("500000.00"),
        human_approval_required=False,
    )

@pytest.fixture
def base_request(base_context) -> PolicyEvaluationRequest:
    # 10 units @ 11,000 = 110,000.00
    return PolicyEvaluationRequest(
        action=ActionType.CREATE_AGREEMENT,
        merchant_id=base_context.merchant_id,
        product_id=uuid.uuid4(),
        unit_price=Decimal("11000.00"),
        quantity=10,
        total_amount=Decimal("110000.00"),
        currency="INR",
        discount_percent=Decimal("5.00"),
    )

# ── 1. Basic Flow & Determinism ───────────────────────────────────────────────

def test_valid_request_returns_allow(engine, base_request, base_context):
    result = engine.evaluate(base_request, base_context)
    assert result.decision == PolicyDecision.ALLOW
    assert not result.blocking_reason
    assert len(result.failed_checks) == 0

def test_engine_is_deterministic(engine, base_request, base_context):
    """Evaluating the same inputs 100 times must yield the exact same result."""
    first_result = engine.evaluate(base_request, base_context)
    for _ in range(100):
        result = engine.evaluate(base_request, base_context)
        assert result.decision == first_result.decision
        assert [c.passed for c in result.checks] == [c.passed for c in first_result.checks]

# ── 2. Total Integrity Rule ───────────────────────────────────────────────────

def test_total_integrity_exact_match(engine, base_request, base_context):
    base_request.unit_price = Decimal("10800.00")
    base_request.quantity = 100
    base_request.total_amount = Decimal("1080000.00")
    # This exceeds autonomous limit, but Integrity should pass
    result = engine.evaluate(base_request, base_context)
    integrity_check = next(c for c in result.checks if c.rule_name == "AGREEMENT_TOTAL_INTEGRITY")
    assert integrity_check.passed is True

def test_total_integrity_mismatch_denies(engine, base_request, base_context):
    """LLM hallucinated a total that is off by 1 paise."""
    base_request.total_amount = Decimal("110000.01")  # 11000.00 * 10 is 110000.00
    result = engine.evaluate(base_request, base_context)
    assert result.decision == PolicyDecision.DENY
    integrity_check = next(c for c in result.checks if c.rule_name == "AGREEMENT_TOTAL_INTEGRITY")
    assert integrity_check.passed is False
    assert "110000.01" in integrity_check.reason
    assert "110000.00" in integrity_check.reason

# ── 3. Currency Rule ──────────────────────────────────────────────────────────

def test_currency_inr_valid(engine, base_request, base_context):
    base_request.currency = "INR"
    result = engine.evaluate(base_request, base_context)
    assert result.decision == PolicyDecision.ALLOW

def test_currency_mismatch_denies(engine, base_request, base_context):
    base_request.currency = "USD"
    result = engine.evaluate(base_request, base_context)
    assert result.decision == PolicyDecision.DENY
    currency_check = next(c for c in result.checks if c.rule_name == "AGREEMENT_CURRENCY")
    assert currency_check.passed is False

# ── 4. Minimum Price Rule ─────────────────────────────────────────────────────

def test_minimum_price_above_limit(engine, base_request, base_context):
    base_request.unit_price = Decimal("10500.01")
    base_request.total_amount = Decimal("105000.10")
    result = engine.evaluate(base_request, base_context)
    assert result.decision == PolicyDecision.ALLOW

def test_minimum_price_exactly_at_limit(engine, base_request, base_context):
    base_request.unit_price = Decimal("10500.00")
    base_request.total_amount = Decimal("105000.00")
    result = engine.evaluate(base_request, base_context)
    assert result.decision == PolicyDecision.ALLOW

def test_minimum_price_below_limit(engine, base_request, base_context):
    base_request.unit_price = Decimal("10499.99")
    base_request.total_amount = Decimal("104999.90")
    result = engine.evaluate(base_request, base_context)
    assert result.decision == PolicyDecision.DENY
    min_price_check = next(c for c in result.checks if c.rule_name == "MERCHANT_MIN_PRICE")
    assert min_price_check.passed is False

# ── 5. Maximum Discount Rule ──────────────────────────────────────────────────

def test_discount_below_maximum(engine, base_request, base_context):
    base_request.discount_percent = Decimal("9.99")
    result = engine.evaluate(base_request, base_context)
    assert result.decision == PolicyDecision.ALLOW

def test_discount_exactly_at_maximum(engine, base_request, base_context):
    base_request.discount_percent = Decimal("10.00")
    result = engine.evaluate(base_request, base_context)
    assert result.decision == PolicyDecision.ALLOW

def test_discount_above_maximum(engine, base_request, base_context):
    base_request.discount_percent = Decimal("10.01")
    result = engine.evaluate(base_request, base_context)
    assert result.decision == PolicyDecision.DENY
    discount_check = next(c for c in result.checks if c.rule_name == "MERCHANT_MAX_DISCOUNT")
    assert discount_check.passed is False

def test_discount_zero_allowed(engine, base_request, base_context):
    base_request.discount_percent = Decimal("0.00")
    base_context.maximum_discount_percent = Decimal("0.00")
    result = engine.evaluate(base_request, base_context)
    assert result.decision == PolicyDecision.ALLOW

def test_discount_full_allowed(engine, base_request, base_context):
    base_request.discount_percent = Decimal("100.00")
    base_context.maximum_discount_percent = Decimal("100.00")
    result = engine.evaluate(base_request, base_context)
    assert result.decision == PolicyDecision.ALLOW

# ── 6. Autonomous Transaction Rule ────────────────────────────────────────────

def test_autonomous_limit_below(engine, base_request, base_context):
    base_request.unit_price = Decimal("10500.00")
    base_request.quantity = 40
    base_request.total_amount = Decimal("420000.00")  # < 500k
    result = engine.evaluate(base_request, base_context)
    assert result.decision == PolicyDecision.ALLOW

def test_autonomous_limit_exact(engine, base_request, base_context):
    base_request.unit_price = Decimal("10000.00")  # Assuming min_price was 10000 for this test
    base_context.minimum_price = Decimal("10000.00")
    base_request.quantity = 50
    base_request.total_amount = Decimal("500000.00")  # == 500k
    result = engine.evaluate(base_request, base_context)
    assert result.decision == PolicyDecision.ALLOW

def test_autonomous_limit_exceeded(engine, base_request, base_context):
    base_request.unit_price = Decimal("10000.00")
    base_context.minimum_price = Decimal("10000.00")
    base_request.quantity = 51
    base_request.total_amount = Decimal("510000.00")  # > 500k limit
    result = engine.evaluate(base_request, base_context)
    
    # Exceeding the autonomous limit is NOT a DENY. It's a HUMAN_APPROVAL_REQUIRED.
    assert result.decision == PolicyDecision.HUMAN_APPROVAL_REQUIRED
    limit_check = next(c for c in result.checks if c.rule_name == "MERCHANT_AUTONOMOUS_LIMIT")
    assert limit_check.passed is False

# ── 7. Human Approval Override ────────────────────────────────────────────────

def test_human_approval_required_forces_approval(engine, base_request, base_context):
    """If the merchant policy forces human approval, the engine returns HUMAN_APPROVAL_REQUIRED even for small deals."""
    base_context.human_approval_required = True
    result = engine.evaluate(base_request, base_context)
    assert result.decision == PolicyDecision.HUMAN_APPROVAL_REQUIRED
    override_check = next(c for c in result.checks if c.rule_name == "MERCHANT_HUMAN_APPROVAL_OVERRIDE")
    assert override_check.passed is False

# ── 8. Multiple Violations & Precedence ───────────────────────────────────────

def test_multiple_violations_reported(engine, base_request, base_context):
    """The engine must not short-circuit. It must report all failures."""
    # 1. Price below minimum
    base_request.unit_price = Decimal("10400.00")
    base_request.quantity = 10
    # 2. Total math is hallucinated
    base_request.total_amount = Decimal("150000.00")
    # 3. Discount too high
    base_request.discount_percent = Decimal("15.00")
    
    result = engine.evaluate(base_request, base_context)
    assert result.decision == PolicyDecision.DENY
    
    failed_names = [c.rule_name for c in result.failed_checks]
    assert "MERCHANT_MIN_PRICE" in failed_names
    assert "AGREEMENT_TOTAL_INTEGRITY" in failed_names
    assert "MERCHANT_MAX_DISCOUNT" in failed_names
    assert len(failed_names) == 3

def test_deny_overrides_human_approval(engine, base_request, base_context):
    """If a hard rule is violated (DENY), but it also exceeds the autonomous limit, the result MUST be DENY."""
    # Trigger HUMAN_APPROVAL_REQUIRED
    base_request.unit_price = Decimal("11000.00")
    base_request.quantity = 100
    base_request.total_amount = Decimal("1100000.00") # > 500k limit
    
    # Trigger DENY
    base_request.discount_percent = Decimal("15.00") # > 10% limit
    
    result = engine.evaluate(base_request, base_context)
    
    # Precedence ensures DENY wins over HUMAN_APPROVAL_REQUIRED
    assert result.decision == PolicyDecision.DENY
    
    # Both rules should be recorded as failed
    failed_names = [c.rule_name for c in result.failed_checks]
    assert "MERCHANT_AUTONOMOUS_LIMIT" in failed_names
    assert "MERCHANT_MAX_DISCOUNT" in failed_names
