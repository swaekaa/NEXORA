# NEXORA — Payment Flow

**Version:** 1.0  
**Date:** August 22, 2026

---

## 1. Payment Lifecycle Overview

```
Agreement Status: VALIDATED (or APPROVED after human review)
         ↓
PaymentAuthorizationLayer.authorize(agreement)
         ↓
[Defense Check 1] PolicyEngine.validate_agreement() — again
         ↓
[Defense Check 2] agreement.total_amount == calculated (Decimal)
         ↓
Convert to paise: amount_paise = int(Decimal(total) * 100)
         ↓
razorpay_client.create_order(amount_paise, "INR", receipt, notes)
         ↓
Save razorpay_order_id → agreement
Agreement status → PAYMENT_INITIATED
Audit: PAYMENT_AUTHORIZED
         ↓
Frontend: Load Razorpay Checkout (key_id + order_id, NEVER key_secret)
         ↓
[User/Agent completes payment in Test Mode]
         ↓
Razorpay sends webhook: payment.captured
         ↓
WebhookProcessor:
  1. Verify HMAC-SHA256 signature (webhook_secret)
  2. Check X-Razorpay-Event-Id (idempotency)
  3. Verify payment amount == agreement amount (paise)
  4. Update agreement: status = PAYMENT_CAPTURED
  5. Save razorpay_payment_id, payment_captured_at
  6. Audit: PAYMENT_CAPTURED
         ↓
Settlement complete
```

---

## 2. Amount Conversion Rules

**Rule:** All monetary amounts stored as `NUMERIC(18,2)` (₹ decimal).  
**Rule:** Razorpay requires integer paise.  
**Conversion:**

```python
from decimal import Decimal, ROUND_HALF_UP

def to_paise(amount_inr: Decimal) -> int:
    """
    Convert INR Decimal to integer paise for Razorpay.
    Example: Decimal("10819.20") → 1081920
    
    Uses integer multiplication to avoid floating-point errors.
    """
    # Quantize to 2 decimal places first
    quantized = amount_inr.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    # Multiply by 100 and convert to int (exact, no float)
    paise = int(quantized * 100)
    return paise

# Test
assert to_paise(Decimal("10819.20")) == 1081920
assert to_paise(Decimal("1082000.00")) == 108200000
```

---

## 3. Payment Verification Flow

```
Frontend receives:
  razorpay_payment_id: "pay_xxxx"
  razorpay_order_id: "order_yyyy"
  razorpay_signature: "abc123..."
          ↓
Frontend sends to: POST /api/v1/payments/verify
  {
    "razorpay_order_id": "order_yyyy",
    "razorpay_payment_id": "pay_xxxx",
    "razorpay_signature": "abc123..."
  }
          ↓
Backend:
  1. Load agreement by razorpay_order_id
  2. Verify signature: HMAC-SHA256("order_yyyy|pay_xxxx", key_secret)
  3. If mismatch: return 400, log audit PAYMENT_AMOUNT_MISMATCH
  4. If match: log PAYMENT_AUTHORIZED (webhook will finalize state)
          ↓
Note: Agreement status NOT updated here — only on webhook
      Frontend payment state is never trusted for settlement
```

---

## 4. States and Invariants

| State | Razorpay Order | Meaning |
|-------|---------------|---------|
| PAYMENT_INITIATED | Created | Order exists, payment pending |
| PAYMENT_CAPTURED | Captured | Money received, settlement pending |
| PAYMENT_FAILED | Failed | Payment declined |

**Invariants:**
- `razorpay_order_id` set ONCE (unique constraint)
- `razorpay_payment_id` set ONCE
- `payment_amount_paise` verified on webhook and stored
- Agreement NEVER transitions to PAYMENT_CAPTURED without webhook confirmation

---

## 5. Failure Scenarios in Payment Flow

| Scenario | Detection | Result |
|----------|-----------|--------|
| Payment amount ≠ agreement | Webhook handler | BLOCK, audit, state unchanged |
| Razorpay order creation fails | API call exception | PAYMENT_INITIATED not set, retry safe |
| Webhook arrives for unknown order | Handler check | Log warning, 200 response |
| Payment signature mismatch | Verify handler | 400, audit PAYMENT_BLOCKED |
| Payment.failed event | Webhook handler | agreement → PAYMENT_FAILED |
