# NEXORA — Razorpay Integration Notes

**Version:** 1.0  
**Date:** August 22, 2026  
**Status:** Research Document — Verified Against Public Razorpay Documentation

---

## Purpose

This document records everything we know about Razorpay APIs relevant to NEXORA, including confirmed behavior, uncertainties, and decisions made due to ambiguity. Any Razorpay engineer reading this should see that we've done serious due diligence.

**Rule:** Never invent Razorpay API behavior. If uncertain, document here.

---

## 1. APIs Used in MVP

### 1.1 Orders API

**Endpoint:** `POST https://api.razorpay.com/v1/orders`  
**Authentication:** HTTP Basic Auth — `key_id:key_secret`  
**Status:** Confirmed. Stable, widely documented.

**Request:**
```json
{
  "amount": 108200000,
  "currency": "INR",
  "receipt": "agreement_<uuid>",
  "notes": {
    "agreement_id": "<uuid>",
    "merchant_id": "<uuid>",
    "buyer_id": "<uuid>"
  }
}
```

**Notes:**
- Amount is in smallest currency unit (paise for INR)
- `receipt` field: max 40 characters — must truncate UUID if needed: `"agr_" + agreement_id[:35]`
- `notes` field: max 15 key-value pairs, values max 256 chars
- Response `id` is the `razorpay_order_id`

**Confirmed behavior:**
- Creating an order does NOT charge the customer
- Order expires if not paid (configurable, default varies)
- Order can be paid only once

### 1.2 Payment Verification (Server-Side)

**Method:** HMAC-SHA256  
**Payload:** `razorpay_order_id + "|" + razorpay_payment_id`  
**Key:** `RAZORPAY_KEY_SECRET`  
**Status:** Confirmed. Official Razorpay documentation.

```python
import hmac
import hashlib

def verify_payment_signature(
    order_id: str,
    payment_id: str, 
    razorpay_signature: str,
    key_secret: str
) -> bool:
    payload = f"{order_id}|{payment_id}"
    expected = hmac.new(
        key_secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, razorpay_signature)
```

**Critical:** Use `key_secret`, NOT `webhook_secret` for payment verification.

### 1.3 Webhook Events

**Delivery:** Razorpay sends POST requests to configured URL  
**Header:** `X-Razorpay-Signature` (HMAC-SHA256 of raw body using webhook_secret)  
**Header:** `X-Razorpay-Event-Id` (unique ID for deduplication)  
**Status:** Confirmed.

**Webhook signature verification uses WEBHOOK_SECRET, not KEY_SECRET.**

```python
def verify_webhook_signature(raw_body: bytes, signature: str, webhook_secret: str) -> bool:
    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        raw_body,           # MUST be raw bytes, never parsed JSON
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

**Retry policy (confirmed):**
- Razorpay retries webhooks for up to 24 hours on non-2xx response
- Uses exponential backoff
- Must respond within 5 seconds (or Razorpay considers delivery failed)
- Always return 2xx even if processing is async

**Events in MVP scope:**
- `payment.captured` — payment successful
- `payment.failed` — payment failed
- `order.paid` — order status changed to paid

### 1.4 Fetch Order by ID

**Endpoint:** `GET https://api.razorpay.com/v1/orders/{order_id}`  
**Status:** Confirmed.

Used for: Polling payment status as fallback (in case webhook delivery is delayed in demo).

---

## 2. Test Mode

**Status:** Confirmed. Full test mode available.

### Test Mode Setup
1. Login to Razorpay Dashboard
2. Toggle to **Test Mode** (top-right)
3. Get Test Mode API keys: Dashboard → Settings → API Keys
4. **Test Mode Key ID** starts with `rzp_test_`
5. **Test Mode Key Secret** starts with (any alphanumeric)

### Test Cards (Confirmed)
| Card Number | Result |
|-------------|--------|
| 4111 1111 1111 1111 | Payment success |
| 5267 3181 8797 5449 | Payment success (Mastercard) |
| 4000 0000 0000 0002 | Payment failure |

### Webhook Testing in Test Mode
- Configure webhook URL in Test Mode Dashboard
- Cannot send to `localhost` — use ngrok or similar tunnel
- Default OTP for config changes in Test Mode: `754081`
- Razorpay Dashboard → Settings → Webhooks → Add URL

### Webhook Local Testing Setup
```bash
# Install ngrok
ngrok http 8000

# Get public URL
# e.g., https://abc123.ngrok.io

# Configure in Razorpay Dashboard:
# Webhook URL: https://abc123.ngrok.io/api/v1/webhooks/razorpay
# Events: payment.captured, payment.failed, order.paid
# Secret: your RAZORPAY_WEBHOOK_SECRET
```

---

## 3. Razorpay MCP Server

**Status:** Confirmed. Launched as official Razorpay product.

**Endpoint:** `https://mcp.razorpay.com/mcp`  
**Purpose:** Allows AI assistants (Claude, Cursor, Gemini) to use Razorpay APIs via natural language.

**Relevance to NEXORA:**
- NEXORA does NOT use Razorpay MCP Server internally (we call the REST API directly)
- NEXORA's own tool-calling architecture is analogous to MCP
- Future enhancement: NEXORA could expose an MCP server for external AI buyers to use

**Current Capabilities (per Razorpay docs):**
- Create payment links
- Fetch order details
- Manage refunds
- Check settlement data
- Via natural language → tool calls

**NEXORA Design Note:**
The NEXORA agent tool system is a **domain-specific version of this pattern** — instead of general Razorpay operations, NEXORA tools are purpose-built for negotiation and commerce.

---

## 4. Razorpay Agent Studio

**Status:** Confirmed. Launched at FTX'26 (March 2026).

**Purpose:** Platform for businesses to deploy autonomous AI agents for payment operations.

**Current Agents:**
- Dispute Responder (automate chargeback responses)
- Subscription Recovery (smart retry logic)
- Abandoned Cart Conversion
- RTO Shield (COD fraud detection)

**Relevance to NEXORA:**
- Agent Studio focuses on **post-payment operational agents**
- NEXORA focuses on **pre-payment negotiation and authorization agents**
- These are complementary, not competing
- NEXORA could integrate with Agent Studio for dispute handling in future

---

## 5. Agentic Payments / UPI

**Status:** Partially confirmed. Still evolving.

**Confirmed:**
- Razorpay partnered with OpenAI (Oct 2025) for agentic payments on ChatGPT
- Razorpay + NPCI partnered (Feb 2026) for expansion to Claude
- UPI Circle and UPI Reserve Pay enable consent-based autonomous transactions
- Partners: Bigbasket, Zomato, Swiggy, Zepto

**Uncertainty:**
- Direct API access for agentic UPI payments via Razorpay is NOT publicly documented for new integrations
- This appears to be a curated partnership program, not an open API
- NEXORA uses standard Orders API + Razorpay Checkout for MVP

**Decision:** Use Razorpay Orders API + standard payment flow for MVP. Document agentic UPI as a future integration path once public APIs are available.

---

## 6. Razorpay Vulcan

**Status:** Announced August 2026.

**What it is:** Razorpay's transformer-based AI foundation model for payments.  
**Trained on:** Trillions of transaction data points.  
**Capabilities:** Improve payment success rates, fraud detection, transaction routing.

**Relevance to NEXORA:**
- Vulcan is infrastructure-level AI (at Razorpay's end)
- NEXORA is application-level AI (at the merchant/buyer end)
- These are complementary layers
- NEXORA could potentially benefit from Vulcan-powered smart routing in future

---

## 7. API Limitations and Workarounds

### 7.1 Receipt Field Length
**Limitation:** `receipt` max 40 characters  
**Workaround:** `receipt = f"agr_{str(agreement_id)[:35]}"` (total: 4 + 35 = 39 chars ✓)

### 7.2 Webhook URL in Test Mode
**Limitation:** Cannot use `localhost` for webhooks  
**Workaround:** ngrok tunnel for development; document clearly in README

**Alternative for demo:** Pre-simulate webhook events using the test script:
```python
# scripts/simulate_webhook.py
# Generates valid Razorpay webhook payload with correct signature
# Can be used without ngrok for isolated demos
```

### 7.3 Razorpay Order Amount Minimum
**Limitation:** Minimum order amount is ₹1 (100 paise)  
**No impact:** All NEXORA transactions are B2B and well above this

### 7.4 Payment Links API (Not Used)
**Decision:** Not using Payment Links in MVP.  
**Reason:** Orders API + Razorpay Checkout gives more control over verification flow.  
**Future:** Could use payment links for asynchronous B2B invoicing.

---

## 8. Key Environment Variables

```bash
# Razorpay Test Mode (NEVER commit these values)
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxx

# Separate secret for webhook signature verification
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret_configured_in_dashboard

# Note: KEY_SECRET and WEBHOOK_SECRET are DIFFERENT
# KEY_SECRET: used for API auth + payment signature verification
# WEBHOOK_SECRET: used for webhook payload signature verification
```

---

## 9. Python SDK

```bash
pip install razorpay
```

```python
import razorpay
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# Create order
order = client.order.create({"amount": 108200000, "currency": "INR", "receipt": "agr_xyz"})

# Fetch order
order = client.order.fetch("order_abc123")

# Fetch payments for order
payments = client.order.payments("order_abc123")
```

---

## 10. Open Questions (To Verify Before Demo)

| Question | Status | Impact |
|----------|--------|--------|
| Does Test Mode webhook need OTP on setup? | Unverified | Setup process |
| Can we use multiple webhook URLs in Test Mode? | Unverified | Dev/prod isolation |
| Is there a Razorpay-provided webhook simulator? | Unverified | Demo reliability |
| Exact format of `X-Razorpay-Event-Id` header | Unverified | Idempotency implementation |
| Are all event types available in Test Mode? | Assumed yes | Failure demo |
| Minimum delay before webhook delivery | Unverified | Demo pacing |
