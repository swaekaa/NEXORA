# NEXORA — Policy Engine Specification

**Version:** 1.1 (Updated Phase 4)  
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

## 2. Discrepancy Note (Phase 4 Update)

*Note: Earlier drafts of this document proposed a complex, JSON-based policy schema with bulk discount tiers and upfront payment arrays. During Phase 2 & 3, the database architecture was finalized with a simpler, strictly-typed SQL schema (`app.models.policy.Policy`). To adhere to strict financial bounds without opaque JSON parsing, the Policy Engine has been implemented to match the deployed database schema.*

---

## 3. Policy Engine Interface

The engine operates via structured Pydantic models and Enums.

```python
class PolicyDecision(str, Enum):
    ALLOW = "allow"
    HUMAN_APPROVAL_REQUIRED = "human_approval_required"
    DENY = "deny"

class PolicyResult:
    decision: PolicyDecision
    checks: list[PolicyCheck]
```

### Precedence Rule
`DENY > HUMAN_APPROVAL_REQUIRED > ALLOW`
If any rule evaluates to `DENY`, the entire result is `DENY`, regardless of whether other rules flag for human approval.

---

## 4. Input Models

The engine takes two inputs:
1. **PolicyEvaluationContext**: The merchant's active policy parameters (from the DB).
2. **PolicyEvaluationRequest**: The agent's proposed commercial action.

### Context (Merchant Policy Constraints)
```python
class PolicyEvaluationContext(BaseModel):
    merchant_id: uuid.UUID
    policy_id: uuid.UUID
    minimum_price: Decimal
    maximum_discount_percent: Decimal
    maximum_autonomous_transaction: Decimal
    human_approval_required: bool
```

### Request (Agent Proposal)
```python
class PolicyEvaluationRequest(BaseModel):
    action: ActionType
    merchant_id: uuid.UUID
    product_id: uuid.UUID
    unit_price: Decimal
    quantity: int
    total_amount: Decimal
    currency: str = "INR"
    discount_percent: Decimal = Decimal("0.00")
```

---

## 5. Rules Evaluated

The engine evaluates the following rules in deterministic order:

### 1. Total Integrity Rule (AGREEMENT_TOTAL_INTEGRITY)
**Purpose:** Ensure the LLM hasn't hallucinated math.
**Check:** `unit_price * quantity == total_amount`
**Decision if failed:** `DENY`

### 2. Currency Rule (AGREEMENT_CURRENCY)
**Purpose:** Prevent currency manipulation.
**Check:** `currency == "INR"`
**Decision if failed:** `DENY`

### 3. Minimum Price Rule (MERCHANT_MIN_PRICE)
**Purpose:** Protect merchant floor price.
**Check:** `unit_price >= context.minimum_price`
**Decision if failed:** `DENY`

### 4. Maximum Discount Rule (MERCHANT_MAX_DISCOUNT)
**Purpose:** Prevent unauthorized discounts.
**Check:** `discount_percent <= context.maximum_discount_percent`
**Decision if failed:** `DENY`

### 5. Human Approval Override (MERCHANT_HUMAN_APPROVAL_OVERRIDE)
**Purpose:** Allow merchant to force manual review of all deals.
**Check:** `context.human_approval_required == False`
**Decision if failed:** `HUMAN_APPROVAL_REQUIRED`

### 6. Autonomous Limit Rule (MERCHANT_AUTONOMOUS_LIMIT)
**Purpose:** High-value deals need human review.
**Check:** `total_amount <= context.maximum_autonomous_transaction`
**Decision if failed:** `HUMAN_APPROVAL_REQUIRED`

---

## 6. Financial Safety Requirements

1. **Decimal Everywhere:** Floating point math is strictly forbidden.
2. **Exhaustive Evaluation:** The engine must evaluate *all* rules, even after a failure is found, to return a complete list of violations to the LLM agent for self-correction.
3. **No Database Dependencies:** The engine requires data to be passed in. It does not query PostgreSQL.
