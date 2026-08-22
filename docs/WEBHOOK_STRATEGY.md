# NEXORA — Webhook Strategy

**Version:** 1.0  
**Date:** August 22, 2026

---

## 1. Core Principles

1. **Verify before parse:** Check HMAC-SHA256 signature on raw body before parsing JSON
2. **Idempotency first:** Check `X-Razorpay-Event-Id` before any processing
3. **Respond fast:** Return 2xx within 5 seconds; process asynchronously
4. **Never trust:** Verify payment amount even after signature passes
5. **Always audit:** Every webhook event logged

---

## 2. Signature Verification

```python
import hmac
import hashlib

def verify_webhook_signature(
    raw_body: bytes,        # MUST be raw bytes — never pre-parsed
    signature: str,
    webhook_secret: str
) -> bool:
    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected, signature)
```

**CRITICAL:** `raw_body` must be bytes from `await request.body()`.  
Do NOT convert to string, do NOT parse JSON first.

---

## 3. Idempotency Implementation

```python
async def is_event_processed(db: AsyncSession, event_id: str) -> bool:
    result = await db.execute(
        select(WebhookEvent).where(WebhookEvent.event_id == event_id)
    )
    return result.scalar_one_or_none() is not None

async def mark_event_processed(
    db: AsyncSession,
    event_id: str,
    event_type: str,
    payload: dict,
    agreement_id: UUID | None
):
    db.add(WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        payload=payload,
        agreement_id=agreement_id,
        processing_result="SUCCESS"
    ))
    await db.commit()
```

---

## 4. Event Routing

```python
EVENT_HANDLERS = {
    "payment.captured": handle_payment_captured,
    "payment.failed":   handle_payment_failed,
    "order.paid":       handle_order_paid,
}

async def process_webhook_event(db: AsyncSession, event: dict):
    event_type = event.get("event")
    handler = EVENT_HANDLERS.get(event_type, handle_unknown_event)
    await handler(db, event)
```

---

## 5. Out-of-Order Event Handling

**Scenario:** `payment.captured` arrives before the agreement is linked to a Razorpay order.

```python
async def handle_payment_captured(db: AsyncSession, event: dict):
    order_id = event["payload"]["payment"]["entity"]["order_id"]
    agreement = await get_agreement_by_razorpay_order(db, order_id)
    
    if not agreement:
        # Out of order — log warning, return 200 (Razorpay will not retry)
        logger.warning(f"Received payment.captured for unknown order {order_id}")
        # Could queue for retry in production — MVP: log and continue
        return
    
    # Process normally...
```

---

## 6. Retry Strategy

Razorpay retries webhooks for 24 hours on non-2xx response.

**NEXORA always returns 2xx** — even for:
- Duplicate events (200 + "already_processed")
- Unknown events (200 + "event_type_not_handled")
- Processing errors (200 + error logged internally)

**Only exception:** Invalid signature → 400 (webhook is rejected, not retried)

---

## 7. Local Testing Setup

```bash
# Option 1: ngrok tunnel
ngrok http 8000
# Configure https://xxx.ngrok.io/api/v1/webhooks/razorpay in Razorpay Dashboard

# Option 2: Simulate webhook (for demos without network dependency)
python scripts/simulate_webhook.py --event payment.captured --agreement-id <uuid>
```

The simulation script generates a correctly-signed webhook payload.
