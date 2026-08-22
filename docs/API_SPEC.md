# NEXORA — API Specification

**Version:** 1.0  
**Date:** August 22, 2026  
**Base URL:** `http://localhost:8000`  
**Format:** REST / JSON

---

## Authentication (MVP)

MVP uses a simple API key header for merchant actions:
```
X-NEXORA-API-KEY: <merchant_api_key>
```
Public endpoints (buyer chat, catalog) require no authentication.
All keys are environment-variable configured, never hardcoded.

---

## 1. Health

### GET /health
```json
{
  "status": "ok",
  "timestamp": "2026-08-22T17:00:00Z",
  "db": "connected",
  "version": "1.0.0"
}
```

---

## 2. Catalog

### GET /api/v1/catalog
List all available products.

**Response 200:**
```json
{
  "products": [
    {
      "id": "uuid",
      "merchant_id": "uuid",
      "name": "Dell 24\" Monitor",
      "description": "...",
      "base_price": "12000.00",
      "currency": "INR",
      "available_stock": 500
    }
  ]
}
```

### GET /api/v1/catalog/{product_id}
Product detail (without sensitive policy minimums — those stay server-side).

---

## 3. Buyer Session

### POST /api/v1/buyer/session
Start a buyer session.

**Request:**
```json
{
  "buyer_id": "uuid",
  "goal": "Buy 100 monitors under ₹11L, delivery within 7 days"
}
```

**Response 201:**
```json
{
  "session_id": "uuid",
  "status": "active",
  "created_at": "2026-08-22T17:00:00Z"
}
```

### POST /api/v1/buyer/session/{session_id}/message
Send message to buyer agent (triggers negotiation flow).

**Request:**
```json
{
  "message": "Buy 100 monitors under ₹11L, delivery within 7 days"
}
```

**Response 200:**
```json
{
  "agent_response": "I've submitted a purchase request for 100 Dell 24\" Monitors...",
  "negotiation_id": "uuid",
  "negotiation_status": "REQUEST",
  "latest_offer": null
}
```

### GET /api/v1/buyer/session/{session_id}
Get session state including current negotiation.

---

## 4. Negotiations

### GET /api/v1/negotiations/{negotiation_id}
Get negotiation state and all messages.

**Response 200:**
```json
{
  "id": "uuid",
  "status": "OFFER",
  "round_count": 1,
  "product": {"name": "Dell 24\" Monitor"},
  "messages": [
    {
      "id": "uuid",
      "sender": "buyer_agent",
      "type": "request",
      "content": "Requesting 100 units at ₹10,800/unit, upfront payment",
      "structured_data": {
        "quantity": 100,
        "unit_price": "10800.00",
        "payment_terms": "upfront"
      },
      "created_at": "2026-08-22T17:00:00Z"
    }
  ],
  "expires_at": "2026-08-22T17:30:00Z"
}
```

---

## 5. Agreements

### GET /api/v1/agreements/{agreement_id}
Get full agreement detail including policy validation result.

**Response 200:**
```json
{
  "id": "uuid",
  "status": "VALIDATED",
  "commercial_terms": {
    "quantity": 100,
    "unit_price": "10819.20",
    "total_amount": "1081920.00",
    "currency": "INR",
    "payment_terms": "upfront"
  },
  "delivery_terms": {"delivery_days": 5},
  "warranty_terms": {"warranty_months": 24},
  "policy_validation": {
    "decision": "PASS",
    "checks": [
      {"rule_name": "MERCHANT_MIN_PRICE", "passed": true},
      {"rule_name": "BUYER_MAX_BUDGET", "passed": true},
      {"rule_name": "AGREEMENT_TOTAL_INTEGRITY", "passed": true}
    ]
  },
  "payment": {
    "razorpay_order_id": "order_abc123",
    "status": "PAYMENT_CAPTURED"
  }
}
```

### GET /api/v1/agreements
List agreements (merchant dashboard use).

**Query params:** `status`, `merchant_id`, `buyer_id`, `limit`, `offset`

---

## 6. Payments

### POST /api/v1/payments/initiate
Initiate payment for a validated agreement.

**Request:**
```json
{
  "agreement_id": "uuid"
}
```

**Response 200:**
```json
{
  "razorpay_order_id": "order_abc123",
  "razorpay_key_id": "rzp_test_xxxx",
  "amount_paise": 108192000,
  "currency": "INR",
  "agreement_id": "uuid"
}
```

**Note:** `razorpay_key_id` is returned (not key_secret). Frontend uses this to initialize Checkout.

### POST /api/v1/payments/verify
Verify payment signature after Razorpay Checkout completes.

**Request:**
```json
{
  "razorpay_order_id": "order_abc123",
  "razorpay_payment_id": "pay_xyz789",
  "razorpay_signature": "abc123..."
}
```

**Response 200:**
```json
{
  "verified": true,
  "agreement_id": "uuid",
  "message": "Payment verified. Awaiting webhook confirmation for settlement."
}
```

---

## 7. Approvals

### GET /api/v1/approvals
List pending approvals for merchant.

**Response 200:**
```json
{
  "approvals": [
    {
      "id": "uuid",
      "agreement_id": "uuid",
      "reason": "Transaction ₹18,00,000 exceeds autonomous limit ₹10,00,000",
      "proposed_total": "1800000.00",
      "autonomous_limit": "1000000.00",
      "status": "PENDING",
      "created_at": "..."
    }
  ]
}
```

### POST /api/v1/approvals/{approval_id}/approve
Merchant approves a transaction.

**Response 200:**
```json
{
  "status": "APPROVED",
  "agreement_id": "uuid",
  "message": "Agreement approved. Proceeding to payment authorization."
}
```

### POST /api/v1/approvals/{approval_id}/reject
Merchant rejects a transaction.

**Request:**
```json
{"reason": "Customer not verified"}
```

---

## 8. Audit

### GET /api/v1/audit
Query audit events.

**Query params:** `agreement_id`, `session_id`, `action`, `agent_type`, `limit` (max 100), `offset`, `from_timestamp`, `to_timestamp`

**Response 200:**
```json
{
  "events": [
    {
      "id": "uuid",
      "timestamp": "2026-08-22T17:00:00Z",
      "agent_id": "merchant_agent",
      "agent_type": "merchant_agent",
      "action": "POLICY_VALIDATED",
      "decision": "PASS",
      "policy_checked": "MERCHANT_MIN_PRICE",
      "policy_result": "PASS",
      "result": "All policy checks passed. Agreement validated.",
      "failure_reason": null,
      "agreement_id": "uuid"
    }
  ],
  "total": 42,
  "limit": 50,
  "offset": 0
}
```

---

## 9. Webhooks (Razorpay → NEXORA)

### POST /api/v1/webhooks/razorpay
Razorpay webhook receiver.

**Headers:**
```
X-Razorpay-Signature: <hmac_sha256>
X-Razorpay-Event-Id: <unique_event_id>
Content-Type: application/json
```

**Response:** Always 200 if signature valid; 400 if invalid signature.

---

## 10. Merchant Dashboard

### GET /api/v1/merchants/{merchant_id}/dashboard
Summary stats for merchant dashboard.

**Response 200:**
```json
{
  "active_negotiations": 2,
  "pending_approvals": 1,
  "total_agreements": 15,
  "paid_agreements": 12,
  "total_revenue": "15234500.00",
  "currency": "INR"
}
```

### GET /api/v1/merchants/{merchant_id}/policy/{product_id}
Get merchant policy (authenticated endpoint).

### PUT /api/v1/merchants/{merchant_id}/policy/{product_id}
Update merchant policy.

---

## Error Response Format

```json
{
  "error": "POLICY_REJECTED",
  "message": "Unit price ₹9,500 is below merchant minimum ₹10,500",
  "code": "MERCHANT_MIN_PRICE",
  "details": {
    "expected": ">= 10500.00",
    "actual": "9500.00"
  }
}
```

**HTTP Status Codes:**
- `200` OK
- `201` Created
- `400` Bad Request (invalid input, bad signature)
- `404` Not Found
- `409` Conflict (invalid state transition)
- `422` Unprocessable Entity (Pydantic validation error)
- `500` Internal Server Error
