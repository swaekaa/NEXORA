# NEXORA — Policy Engine Specification

**Version:** 1.0  
**Date:** August 22, 2026  
**Status:** Canonical Reference

---

## 1. Fundamental Principle

The Policy Engine is the most critical component in NEXORA.

**It has exactly ONE rule:**
> Every financial validation is deterministic, calculable, and has zero LLM dependency.

The Policy Engine:
- Has no network calls
- Has no LLM calls
- Has no randomness
- Uses only `Decimal` arithmetic
- Returns a typed, structured result
- Can be tested in isolation with pure unit tests

---

## 2. Policy Engine Interface

```python
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

class PolicyDecision(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REQUIRES_HUMAN_APPROVAL = "REQUIRES_HUMAN_APPROVAL"

@dataclass
class PolicyCheck:
    rule_name: str        # Unique rule identifier
    passed: bool          # True = rule satisfied
    expected: str         # What the rule expects
    actual: str           # What the agreement contains
    reason: str           # Human-readable explanation (empty if passed)

@dataclass
class PolicyResult:
    decision: PolicyDecision
    checks: list[PolicyCheck] = field(default_factory=list)
    blocking_reason: Optional[str] = None   # Set if FAIL, summary of blocking rules
    
    @property
    def failed_checks(self) -> list[PolicyCheck]:
        return [c for c in self.checks if not c.passed]
    
    @property
    def passed_checks(self) -> list[PolicyCheck]:
        return [c for c in self.checks if c.passed]
```

---

## 3. Merchant Rules

### Rule: MERCHANT_MIN_PRICE
**Purpose:** Merchant's floor price — LLM cannot negotiate below this.  
**Check:** `agreement.unit_price >= policy.minimum_price`

```python
def _rule_min_price(self, agreement, policy) -> PolicyCheck:
    unit_price = Decimal(str(agreement.unit_price))
    min_price = Decimal(str(policy.minimum_price))
    passed = unit_price >= min_price
    return PolicyCheck(
        rule_name="MERCHANT_MIN_PRICE",
        passed=passed,
        expected=f">= {min_price}",
        actual=str(unit_price),
        reason="" if passed else (
            f"Unit price ₹{unit_price} is below merchant minimum ₹{min_price}. "
            f"Shortfall: ₹{min_price - unit_price}"
        )
    )
```

### Rule: MERCHANT_MAX_DISCOUNT
**Purpose:** Ensure the negotiated discount doesn't exceed the allowed tier.  
**Check:** Calculate allowed price for this quantity tier; check agreement.unit_price >= allowed_floor

```python
def _rule_max_discount(self, agreement, policy) -> PolicyCheck:
    base_price = Decimal(str(policy.base_price))
    quantity = Decimal(str(agreement.quantity))
    unit_price = Decimal(str(agreement.unit_price))
    payment_terms = agreement.payment_terms
    
    # Find applicable bulk discount tier
    bulk_discount_pct = self._get_bulk_discount(int(quantity), policy.bulk_discounts)
    
    # Apply upfront discount if applicable
    upfront_pct = Decimal(str(policy.upfront_discount_pct)) if payment_terms == "upfront" else Decimal("0")
    
    # Calculate minimum allowed price considering all discounts
    # Order: base → bulk discount → upfront discount
    after_bulk = base_price * (Decimal("1") - bulk_discount_pct / Decimal("100"))
    after_upfront = after_bulk * (Decimal("1") - upfront_pct / Decimal("100"))
    
    # Minimum allowed = max(policy.minimum_price, calculated_floor)
    # Note: policy.minimum_price is the absolute floor
    allowed_floor = max(Decimal(str(policy.minimum_price)), after_upfront)
    
    # Unit price must be >= after_upfront (i.e., discount not exceeded)
    # AND >= minimum_price (checked by MERCHANT_MIN_PRICE separately)
    passed = unit_price >= after_upfront.quantize(Decimal("0.01"))
    
    return PolicyCheck(
        rule_name="MERCHANT_MAX_DISCOUNT",
        passed=passed,
        expected=f">= {after_upfront:.2f} (base ₹{base_price} - {bulk_discount_pct}% bulk - {upfront_pct}% upfront)",
        actual=str(unit_price),
        reason="" if passed else (
            f"Price ₹{unit_price} exceeds maximum allowed discount. "
            f"Minimum price after discounts: ₹{after_upfront:.2f}"
        )
    )
```

### Rule: MERCHANT_INVENTORY
**Purpose:** Cannot sell more than available stock.  
**Check:** `agreement.quantity <= product.available_stock`

### Rule: MERCHANT_DELIVERY
**Purpose:** Delivery commitment cannot exceed merchant capability.  
**Check:** `agreement.delivery_days <= policy.max_delivery_days`

### Rule: MERCHANT_PAYMENT_TERMS
**Purpose:** Payment terms must be in allowed list.  
**Check:** `agreement.payment_terms in policy.allowed_payment_terms`

### Rule: MERCHANT_AUTONOMOUS_LIMIT
**Purpose:** Transactions above threshold require human review.  
**Check:** `agreement.total_amount <= policy.autonomous_limit` → PASS | `> autonomous_limit` → REQUIRES_HUMAN_APPROVAL (not FAIL)

```python
def _rule_autonomous_limit(self, agreement, policy) -> tuple[PolicyCheck, bool]:
    total = Decimal(str(agreement.total_amount))
    limit = Decimal(str(policy.autonomous_limit))
    within_limit = total <= limit
    return PolicyCheck(
        rule_name="MERCHANT_AUTONOMOUS_LIMIT",
        passed=within_limit,
        expected=f"<= {limit}",
        actual=str(total),
        reason="" if within_limit else (
            f"Transaction ₹{total} exceeds autonomous limit ₹{limit}. "
            f"Human approval required."
        )
    ), not within_limit  # True = needs approval
```

---

## 4. Buyer Rules

### Rule: BUYER_MAX_BUDGET
**Purpose:** Buyer cannot spend more than their configured budget.  
**Check:** `agreement.total_amount <= buyer_policy.max_budget`

### Rule: BUYER_MAX_DELIVERY
**Purpose:** Delivery must meet buyer's deadline.  
**Check:** `agreement.delivery_days <= buyer_policy.max_delivery_days`

### Rule: BUYER_MIN_WARRANTY
**Purpose:** Product warranty must meet buyer's minimum requirement.  
**Check:** `agreement.warranty_months >= buyer_policy.min_warranty_months`

---

## 5. Agreement Integrity Rules

### Rule: AGREEMENT_TOTAL_INTEGRITY
**Purpose:** Backend independently verifies total = unit_price * quantity.  
**This is the core anti-hallucination check.**

```python
def _rule_total_integrity(self, agreement) -> PolicyCheck:
    unit_price = Decimal(str(agreement.unit_price))
    quantity = Decimal(str(agreement.quantity))
    total = Decimal(str(agreement.total_amount))
    
    calculated = (unit_price * quantity).quantize(Decimal("0.01"))
    stored = total.quantize(Decimal("0.01"))
    
    passed = calculated == stored
    return PolicyCheck(
        rule_name="AGREEMENT_TOTAL_INTEGRITY",
        passed=passed,
        expected=str(calculated),
        actual=str(stored),
        reason="" if passed else (
            f"Total integrity check FAILED. "
            f"Calculated: ₹{calculated} (unit_price × quantity = ₹{unit_price} × {quantity}). "
            f"Agreement claims: ₹{stored}. "
            f"Difference: ₹{abs(calculated - stored)}"
        )
    )
```

### Rule: AGREEMENT_CURRENCY
**Check:** `agreement.currency in SUPPORTED_CURRENCIES`  
Supported: `["INR"]` (MVP)

### Rule: AGREEMENT_NOT_EXPIRED
**Check:** `datetime.utcnow() < agreement.expires_at`

---

## 6. Decision Compilation

```python
def _compile_result(self, checks: list[PolicyCheck], needs_approval: bool) -> PolicyResult:
    failed = [c for c in checks if not c.passed]
    
    if failed:
        # Any failed check → FAIL
        blocking = "; ".join(c.reason for c in failed if c.reason)
        return PolicyResult(
            decision=PolicyDecision.FAIL,
            checks=checks,
            blocking_reason=blocking
        )
    
    if needs_approval:
        # All passed but above autonomous limit
        return PolicyResult(
            decision=PolicyDecision.REQUIRES_HUMAN_APPROVAL,
            checks=checks,
            blocking_reason="Transaction requires human merchant approval"
        )
    
    return PolicyResult(
        decision=PolicyDecision.PASS,
        checks=checks
    )
```

---

## 7. Discount Calculation Reference

### Bulk Discount Tiers (Demo Configuration)
| Quantity | Discount |
|----------|----------|
| 1–49 | 0% |
| 50–99 | 5% |
| 100+ | 8% |

### Upfront Payment Discount
| Payment Term | Discount |
|--------------|----------|
| upfront | 2% |
| net30 | 0% |
| net60 | 0% |

### Discount Application Order
1. Start with base_price
2. Apply bulk discount: `price = base * (1 - bulk_pct/100)`
3. Apply upfront discount: `price = price * (1 - upfront_pct/100)`

### Important
- Discounts compound in sequence
- The absolute minimum (minimum_price) is a hard floor regardless of calculated discounts
- All calculations use `Decimal`, rounded to 2 decimal places at the end only

---

## 8. Boundary Test Cases

Critical test cases that must all pass:

```python
# Test 1: Exactly at minimum price
assert policy_engine.check_min_price(unit_price=10500, min_price=10500) == PASS

# Test 2: 1 paise below minimum
assert policy_engine.check_min_price(unit_price=10499.99, min_price=10500) == FAIL

# Test 3: Exactly at bulk discount boundary
assert policy_engine.get_bulk_discount(quantity=100) == Decimal("8.00")  # 100+ tier
assert policy_engine.get_bulk_discount(quantity=99) == Decimal("5.00")   # 50-99 tier

# Test 4: Exactly at autonomous limit
assert policy_engine.check_autonomous_limit(total=1000000, limit=1000000) == PASS

# Test 5: 1 paise above autonomous limit
assert policy_engine.check_autonomous_limit(total=1000000.01, limit=1000000) == REQUIRES_HUMAN_APPROVAL

# Test 6: Total integrity — 1 paise mismatch
assert policy_engine.check_total_integrity(unit_price=10500, quantity=100, total=1050001) == FAIL

# Test 7: Buyer budget exactly met
assert policy_engine.check_buyer_budget(total=1100000, max_budget=1100000) == PASS

# Test 8: Buyer budget 1 paise over
assert policy_engine.check_buyer_budget(total=1100000.01, max_budget=1100000) == FAIL
```

---

## 9. Policy Configuration Schema (Per Merchant)

```json
{
  "merchant_id": "uuid",
  "product_id": "uuid",
  "base_price": "12000.00",
  "minimum_price": "10500.00",
  "bulk_discounts": [
    {"min_quantity": 50, "discount_pct": "5.00"},
    {"min_quantity": 100, "discount_pct": "8.00"}
  ],
  "upfront_discount_pct": "2.00",
  "autonomous_limit": "2000000.00",
  "max_delivery_days": 7,
  "min_warranty_months": 12,
  "allowed_payment_terms": ["upfront", "net30"],
  "max_negotiation_rounds": 10
}
```
