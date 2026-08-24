# NEXORA — Failure Handling Specification

**Version:** 1.0  
**Date:** August 22, 2026  
**Status:** Canonical Reference

---

## Overview

NEXORA is explicitly designed to handle failures gracefully. Every failure mode produces:
1. A structured error response
2. An audit event with failure_reason
3. Correct system state (no corruption)
4. A human-readable explanation

The Razorpay Buildathon explicitly evaluates failure recovery. NEXORA demonstrates all 7 failure scenarios in the demo.

---

## Failure Case 1: Payment Amount Mismatch

### Scenario
An agent (or attacker) attempts to initiate or confirm a payment with an amount different from the validated agreement.

### Trigger Methods
- Webhook arrives with `payment.entity.amount` ≠ `agreement.total_amount * 100`
- (Hypothetical) LLM tries to call Razorpay with different amount

### Detection Point
`WebhookProcessor.handle_payment_captured()`:
```python
captured_amount_paise = event["payload"]["payment"]["entity"]["amount"]
expected_amount_paise = int(agreement.total_amount * 100)

if captured_amount_paise != expected_amount_paise:
    # BLOCK immediately
    await audit.record(AuditEvent(
        action=AuditAction.PAYMENT_AMOUNT_MISMATCH,
        agreement_id=agreement.id,
        decision="BLOCKED",
        failure_reason=f"Amount mismatch: expected {expected_amount_paise} paise, got {captured_amount_paise}",
        result="Payment NOT marked as captured"
    ))
    raise PaymentAmountMismatchError(
        expected=expected_amount_paise,
        received=captured_amount_paise
    )
```

### System State After Failure
- Agreement status: `PAYMENT_INITIATED` (remains, not corrupted)
- Audit event: `PAYMENT_AMOUNT_MISMATCH` with amounts
- Alert: Human-visible in merchant dashboard

### Demo Trigger
Script `simulate_failures.py simulate_amount_mismatch(agreement_id)`:
- Sends a forged webhook with amount = original_amount + 100 (1 rupee extra)
- System blocks it, logs audit event

---

## Failure Case 2: Price Below Merchant Minimum

### Scenario
Buyer agent tries to negotiate a unit price below the merchant's configured minimum price floor.

### Trigger
Buyer agent calls `submit_buy_request` or `submit_counteroffer` with `proposed_unit_price < merchant_policy.minimum_price`.

### Detection Point
**First detection:** `MerchantAgent._evaluate_buyer_request()`:
```python
# Pre-check before generating offer
if buyer_max_unit_price < policy.minimum_price:
    # Merchant agent counteroffer at minimum_price or reject
    return MerchantDecision(
        action="COUNTER",
        counter_price=policy.minimum_price,
        reason=f"Cannot go below ₹{policy.minimum_price} minimum price"
    )
```

**Second detection (defense in depth):** `PolicyEngine.validate_agreement()`:
```python
# MERCHANT_MIN_PRICE rule always runs
check = self._rule_min_price(agreement, policy)
# If FAIL → PolicyResult.decision = FAIL → agreement.status = VALIDATION_FAILED
```

### System State After Failure
- If detected at negotiation: merchant agent counters at minimum or rejects
- If detected at policy engine: agreement status = `VALIDATION_FAILED`
- Audit event: `POLICY_BLOCKED` with rule `MERCHANT_MIN_PRICE`

### Demo Trigger
Buyer submits goal: "Buy 5 monitors at ₹9,000 each" (below ₹10,500 minimum)

---

## Failure Case 3: Exceeds Merchant Autonomous Limit

### Scenario
A negotiated transaction total exceeds the merchant's configured autonomous limit (e.g., ₹10,00,000).

### Trigger
Agreement total > `merchant_policy.autonomous_limit`

### Detection Point
`PolicyEngine._rule_autonomous_limit()`:
```python
passed = (request.total_amount <= context.maximum_autonomous_transaction)
return PolicyCheck(
    rule_name="MERCHANT_AUTONOMOUS_LIMIT",
    passed=passed,
    ...
)
```
Then `_compile_result()` returns `PolicyDecision.HUMAN_APPROVAL_REQUIRED`.

**Flow:**
```
PolicyResult.decision = REQUIRES_HUMAN_APPROVAL
    ↓
AgreementEngine: agreement.status = PENDING_APPROVAL
    ↓
ApprovalService.create_request(agreement_id, reason, total, limit)
    ↓
Audit: HUMAN_APPROVAL_REQUESTED
    ↓
Merchant dashboard shows approval card
    ↓
[Merchant clicks APPROVE]
    ↓
agreement.status = APPROVED
PaymentAuthLayer.authorize() → Razorpay Order created
    ↓
[OR Merchant clicks REJECT]
    ↓
agreement.status = CANCELLED
Audit: HUMAN_REJECTED
```

### Demo Trigger
Configure demo merchant with `autonomous_limit = ₹10,00,000`.
Demo negotiation: 150 monitors at ₹12,000 = ₹18,00,000 > limit → escalation.

---

## Failure Case 4: Duplicate Razorpay Webhook

### Scenario
Razorpay delivers the same webhook event twice (network retry, Razorpay retry policy).

### Trigger
Two POST requests to `/api/v1/webhooks/razorpay` with identical `X-Razorpay-Event-Id`.

### Detection Point
`WebhookProcessor.process()`:
```python
event_id = request.headers.get("X-Razorpay-Event-Id")

# Check idempotency table
existing = await db.execute(
    select(WebhookEvent).where(WebhookEvent.event_id == event_id)
)
if existing.scalar_one_or_none():
    # Already processed — silently succeed
    await audit.record(AuditEvent(
        action=AuditAction.WEBHOOK_DUPLICATE,
        result=f"Event {event_id} already processed — skipped"
    ))
    return {"status": "already_processed"}  # HTTP 200
```

### System State After Failure
- No duplicate processing
- No duplicate audit event (only the original)
- One `WEBHOOK_DUPLICATE` audit entry for the duplicate
- HTTP 200 returned (Razorpay won't retry)

### Demo Trigger
`simulate_failures.py replay_webhook(event_id)`:
- Captures real webhook event_id
- Sends it again
- Shows WEBHOOK_DUPLICATE in audit log

---

## Failure Case 5: Razorpay Payment Failure

### Scenario
Payment is attempted but Razorpay returns payment.failed event (insufficient funds, card declined, etc.)

### Trigger
Razorpay webhook event: `payment.failed`

### Handler
```python
async def handle_payment_failed(event: dict, db: AsyncSession):
    payment_id = event["payload"]["payment"]["entity"]["id"]
    order_id = event["payload"]["payment"]["entity"]["order_id"]
    error_code = event["payload"]["payment"]["entity"].get("error_code")
    error_description = event["payload"]["payment"]["entity"].get("error_description")
    
    agreement = await get_agreement_by_razorpay_order(db, order_id)
    if agreement:
        await transition_agreement_status(db, agreement.id, "PAYMENT_FAILED")
        await audit.record(AuditEvent(
            action=AuditAction.PAYMENT_FAILED,
            agreement_id=agreement.id,
            razorpay_reference=payment_id,
            decision="PAYMENT_FAILED",
            failure_reason=f"Razorpay error: {error_code} — {error_description}",
            result="Agreement marked as PAYMENT_FAILED"
        ))
```

### System State After Failure
- Agreement status: `PAYMENT_FAILED` (terminal)
- Agreement commercial terms: UNCHANGED (not corrupted)
- Audit event: `PAYMENT_FAILED` with Razorpay error details
- Dashboard: Shows failed payment with reason

### Demo Trigger
Use Razorpay Test Mode failure card: `4000 0000 0000 0002` (payment always fails)

---

## Failure Case 6: Invalid Webhook Signature

### Scenario
A malformed, forged, or tampered webhook arrives. Signature doesn't match.

### Trigger
POST to `/api/v1/webhooks/razorpay` with wrong/missing `X-Razorpay-Signature` header.

### Detection Point
```python
@router.post("/api/v1/webhooks/razorpay")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    
    # FIRST action — before any parsing
    if not verify_webhook_signature(raw_body, signature, settings.RAZORPAY_WEBHOOK_SECRET):
        await audit.record(AuditEvent(
            action=AuditAction.WEBHOOK_INVALID_SIGNATURE,
            agent_id="system",
            agent_type=AgentType.SYSTEM,
            decision="REJECTED",
            failure_reason="HMAC-SHA256 signature verification failed",
            result="Webhook rejected"
        ))
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
```

### System State After Failure
- No processing occurs
- HTTP 400 returned
- Audit event: `WEBHOOK_INVALID_SIGNATURE`
- Body never parsed

### Demo Trigger
`simulate_failures.py send_invalid_signature()`:
- Sends real Razorpay-format webhook with wrong secret
- Shows 400 response + audit event

---

## Failure Case 7: Invalid LLM Tool Arguments

### Scenario
LLM generates tool call arguments that fail Pydantic schema validation (e.g., negative quantity, missing required field, wrong type).

### Trigger
LLM produces:
```json
{
  "tool": "submit_buy_request",
  "args": {
    "product_id": "uuid",
    "quantity": -5,
    "max_unit_price": "not_a_number",
    "max_delivery_days": 7,
    "payment_terms": "upfront"
  }
}
```

### Detection Point
```python
def dispatch_tool(tool_name: str, raw_args: dict) -> dict:
    schema_class = TOOL_SCHEMAS[tool_name]
    try:
        validated_args = schema_class(**raw_args)
    except ValidationError as e:
        # Return error to LLM — do not execute
        error_response = {
            "error": "INVALID_TOOL_ARGS",
            "tool": tool_name,
            "validation_errors": e.errors()
        }
        audit.record(AuditEvent(
            action=AuditAction.INVALID_TOOL_ARGS,
            result=f"Tool {tool_name} called with invalid args",
            failure_reason=str(e.errors())
        ))
        return error_response   # LLM gets this, can retry
```

**Retry logic:**
```python
MAX_RETRIES = 3
for attempt in range(MAX_RETRIES):
    result = await llm.call_with_tools(...)
    if "error" not in result:
        break
    if attempt == MAX_RETRIES - 1:
        # Give up — pause negotiation
        raise MaxToolRetriesError(f"Tool {tool_name} failed {MAX_RETRIES} times")
```

### System State After Failure
- Tool never executes
- LLM receives structured error and retries
- After 3 failures: negotiation paused, audit event logged
- No financial state corrupted

### Demo Trigger
Temporarily inject a bad system prompt instruction to cause malformed tool output, then restore.

---

## Failure Summary Table

| # | Failure | Detection Point | HTTP Code | System State | Audit Action |
|---|---------|----------------|-----------|--------------|--------------|
| F1 | Amount mismatch | WebhookProcessor | Internal block | PAYMENT_INITIATED (unchanged) | PAYMENT_AMOUNT_MISMATCH |
| F2 | Price below min | PolicyEngine | 200 (negotiation continues) | VALIDATION_FAILED | POLICY_BLOCKED |
| F3 | Exceeds auto limit | PolicyEngine | 200 (escalation) | PENDING_APPROVAL | HUMAN_APPROVAL_REQUESTED |
| F4 | Duplicate webhook | WebhookProcessor | 200 | Unchanged | WEBHOOK_DUPLICATE |
| F5 | Payment failed | WebhookProcessor | Internal | PAYMENT_FAILED | PAYMENT_FAILED |
| F6 | Invalid signature | WebhookProcessor | 400 | Unchanged | WEBHOOK_INVALID_SIGNATURE |
| F7 | Invalid tool args | Tool dispatcher | Internal | Negotiation paused | INVALID_TOOL_ARGS |
