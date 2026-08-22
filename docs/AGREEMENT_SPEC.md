# NEXORA — Commercial Agreement Specification

**Version:** 1.0  
**Date:** August 22, 2026  
**Status:** Canonical Reference

---

## 1. Purpose

The Commercial Agreement is the **single source of truth** for any NEXORA transaction. Once created and validated, it defines exactly what was agreed, at what price, under what conditions — and becomes the binding reference for payment.

**No payment can be authorized without a validated agreement.**  
**No payment amount can differ from the agreement amount.**

---

## 2. Agreement Lifecycle

```
NEGOTIATION ACCEPT
      ↓
AgreementEngine.create_from_negotiation()
      ↓
status: PENDING_VALIDATION
      ↓
PolicyEngine.validate_agreement()
      ↓
   ┌──┴──┐
FAIL    PASS    REQUIRES_HUMAN_APPROVAL
  ↓       ↓              ↓
VALIDATION_FAILED    VALIDATED    PENDING_APPROVAL
                        ↓              ↓ (human approves)
               PaymentAuthLayer     APPROVED
                        ↓              ↓
                PAYMENT_INITIATED   PaymentAuthLayer
                        ↓              ↓
                (Razorpay webhook)  PAYMENT_INITIATED
                        ↓
                  ┌─────┴────┐
            CAPTURED      FAILED
                ↓              ↓
          PAYMENT_CAPTURED  PAYMENT_FAILED
```

---

## 3. Full Agreement Schema

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "version": 1,
  "merchant_id": "uuid",
  "buyer_id": "uuid",
  "negotiation_id": "uuid",
  
  "product": {
    "id": "uuid",
    "name": "Dell 24\" Monitor",
    "sku": "DELL-24-FHD-001",
    "description": "Full HD IPS Display, 1920x1080"
  },
  
  "commercial_terms": {
    "quantity": 100,
    "unit_price": "10820.00",
    "total_amount": "1082000.00",
    "currency": "INR",
    "payment_terms": "upfront",
    "discounts_applied": [
      {
        "type": "BULK_DISCOUNT",
        "tier": "100+ units",
        "percentage": "8.00",
        "applied_to": "base_price"
      },
      {
        "type": "UPFRONT_DISCOUNT",
        "percentage": "2.00",
        "applied_to": "post_bulk_price"
      }
    ]
  },
  
  "delivery_terms": {
    "delivery_days": 5,
    "delivery_method": "courier",
    "delivery_address": null
  },
  
  "warranty_terms": {
    "warranty_months": 24,
    "warranty_type": "manufacturer"
  },
  
  "payment": {
    "razorpay_order_id": null,
    "razorpay_payment_id": null,
    "payment_captured_at": null,
    "payment_amount_paise": null
  },
  
  "policy_validation": {
    "validated_at": null,
    "decision": null,
    "checks": [],
    "blocking_reason": null
  },
  
  "metadata": {
    "created_at": "2026-08-22T17:00:00Z",
    "expires_at": "2026-08-23T17:00:00Z",
    "status": "PENDING_VALIDATION",
    "last_updated_at": "2026-08-22T17:00:00Z",
    "negotiation_rounds": 2,
    "agreement_hash": "sha256_of_canonical_fields"
  }
}
```

---

## 4. Immutability Rules

### 4.1 Immutable Fields (Once Created)
These fields are set at creation and MUST NEVER change:
- `id`
- `merchant_id`
- `buyer_id`
- `negotiation_id`
- `product.id`
- `commercial_terms.quantity`
- `commercial_terms.unit_price`
- `commercial_terms.total_amount`
- `commercial_terms.currency`
- `commercial_terms.payment_terms`

### 4.2 Mutable Fields (Controlled State Machine)
These fields change only via explicit service methods:
- `status` (only via `AgreementService.transition_status()`)
- `payment.razorpay_order_id` (set once, immutable after)
- `payment.razorpay_payment_id` (set once, immutable after)
- `policy_validation` (set once after validation)

### 4.3 Agreement Hash
On creation, a SHA-256 hash of all immutable commercial fields is stored:
```python
canonical = f"{quantity}|{unit_price}|{total_amount}|{currency}|{payment_terms}"
agreement_hash = hashlib.sha256(canonical.encode()).hexdigest()
```
This allows detection of any tampering with core fields.

---

## 5. Status Transition Rules

| From Status | Allowed Transitions | Trigger |
|-------------|---------------------|---------|
| PENDING_VALIDATION | → VALIDATED | PolicyEngine PASS |
| PENDING_VALIDATION | → VALIDATION_FAILED | PolicyEngine FAIL |
| PENDING_VALIDATION | → PENDING_APPROVAL | PolicyEngine REQUIRES_HUMAN_APPROVAL |
| VALIDATED | → PAYMENT_INITIATED | PaymentAuthLayer.authorize() |
| PENDING_APPROVAL | → APPROVED | Human merchant approves |
| PENDING_APPROVAL | → CANCELLED | Human merchant rejects |
| PENDING_APPROVAL | → EXPIRED | 24h auto-expiry |
| APPROVED | → PAYMENT_INITIATED | PaymentAuthLayer.authorize() |
| PAYMENT_INITIATED | → PAYMENT_CAPTURED | Webhook: payment.captured (verified) |
| PAYMENT_INITIATED | → PAYMENT_FAILED | Webhook: payment.failed |
| PAYMENT_CAPTURED | (terminal) | — |
| PAYMENT_FAILED | (terminal) | — |
| VALIDATION_FAILED | (terminal) | — |
| CANCELLED | (terminal) | — |
| EXPIRED | (terminal) | — |

Any attempted transition not in this table raises `InvalidAgreementTransitionError`.

---

## 6. Agreement Total Validation

The policy engine always independently recalculates the total:

```python
# In PolicyEngine._check_agreement_integrity():
from decimal import Decimal, ROUND_HALF_UP

calculated = Decimal(str(agreement.unit_price)) * Decimal(str(agreement.quantity))
stored = Decimal(str(agreement.total_amount))

# Must match to the last paise (0.01 INR)
if calculated.quantize(Decimal("0.01")) != stored.quantize(Decimal("0.01")):
    return PolicyCheck(
        rule_name="AGREEMENT_TOTAL_INTEGRITY",
        passed=False,
        expected=str(calculated),
        actual=str(stored),
        reason=f"Total mismatch: {calculated} calculated, {stored} stored"
    )
```

---

## 7. Demo Agreement Example

The following is the expected agreement for the demo scenario (100 Dell monitors, buyer pays upfront):

```json
{
  "id": "aab12345-...",
  "commercial_terms": {
    "quantity": 100,
    "unit_price": "10819.20",
    "total_amount": "1081920.00",
    "currency": "INR",
    "payment_terms": "upfront",
    "discounts_applied": [
      {"type": "BULK_DISCOUNT", "percentage": "8.00"},
      {"type": "UPFRONT_DISCOUNT", "percentage": "2.00"}
    ]
  },
  "delivery_terms": {"delivery_days": 5},
  "warranty_terms": {"warranty_months": 24},
  "status": "PAYMENT_CAPTURED"
}
```

**Calculation verification:**
- Base: ₹12,000
- 8% bulk discount (100+ units): ₹12,000 × 0.92 = ₹11,040
- 2% upfront discount: ₹11,040 × 0.98 = ₹10,819.20
- Total: ₹10,819.20 × 100 = ₹10,81,920
- Buyer budget: ₹11,00,000 ✓ (under budget)
- Merchant minimum: ₹10,500 ✓ (above minimum)
- Autonomous limit: ₹10,81,920 < ₹10,00,000? No → ₹10,81,920 > ₹10,00,000 → **REQUIRES_HUMAN_APPROVAL**

*Note: The demo scenario will need the autonomous limit set above ₹10,81,920 (e.g., ₹20,00,000) for the happy path, and a separate demo for the approval flow.*
