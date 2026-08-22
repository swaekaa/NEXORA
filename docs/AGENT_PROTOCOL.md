# NEXORA — Agent Communication Protocol

**Version:** 1.0  
**Date:** August 22, 2026  
**Status:** Canonical Reference

---

## 1. Overview

The NEXORA Agent Protocol defines how the AI Buyer Agent and AI Merchant Agent communicate during a negotiation. It governs:

- Message structure and typing
- Tool call schemas
- State machine transitions
- Tool output validation
- Error handling

The protocol is designed so that **LLMs never directly execute financial actions** — they only call tools that are validated by the deterministic backend before execution.

---

## 2. Tool-Calling Architecture

Both agents use structured tool calling:

```
LLM decides which tool to call
    ↓
LLM generates tool arguments (JSON)
    ↓
Pydantic schema validation (rejects invalid args)
    ↓
Tool execution in deterministic backend
    ↓
Tool result returned to LLM
    ↓
LLM decides next action
```

If Pydantic validation fails → error returned to LLM with schema details → LLM retries (max 3 attempts) → if still fails → `INVALID_TOOL_ARGS` audit event, negotiation paused.

---

## 3. Buyer Agent Tools

### 3.1 `discover_products`
Search the merchant catalog.

```json
{
  "tool": "discover_products",
  "args": {
    "query": "24 inch monitor",
    "max_results": 5
  }
}
```

**Response:**
```json
{
  "products": [
    {
      "id": "uuid",
      "name": "Dell 24\" Monitor",
      "description": "Full HD IPS panel",
      "base_price": "12000.00",
      "currency": "INR",
      "available_stock": 500
    }
  ]
}
```

### 3.2 `submit_buy_request`
Open a negotiation with the merchant.

```json
{
  "tool": "submit_buy_request",
  "args": {
    "product_id": "uuid",
    "quantity": 100,
    "max_unit_price": "11000.00",
    "max_delivery_days": 7,
    "min_warranty_months": 12,
    "payment_terms": "upfront",
    "message": "We need 100 units for our new office, prefer upfront payment for discount"
  }
}
```

**Validation rules:**
- `quantity`: int, > 0
- `max_unit_price`: Decimal string, > 0
- `payment_terms`: one of ["upfront", "net30", "net60"]
- `max_delivery_days`: int, 1–365
- `min_warranty_months`: int, 0–120

### 3.3 `submit_counteroffer`
Counter a merchant offer during active negotiation.

```json
{
  "tool": "submit_counteroffer",
  "args": {
    "negotiation_id": "uuid",
    "proposed_unit_price": "10800.00",
    "proposed_quantity": 100,
    "message": "Offering ₹10,800/unit upfront payment"
  }
}
```

### 3.4 `accept_offer`
Accept the current merchant offer.

```json
{
  "tool": "accept_offer",
  "args": {
    "negotiation_id": "uuid",
    "accepted_unit_price": "10820.00",
    "accepted_quantity": 100,
    "reason": "Price within budget, delivery within deadline, warranty meets requirements"
  }
}
```

### 3.5 `reject_offer`
Reject and terminate negotiation.

```json
{
  "tool": "reject_offer",
  "args": {
    "negotiation_id": "uuid",
    "reason": "Merchant cannot meet delivery deadline requirement of 7 days"
  }
}
```

---

## 4. Merchant Agent Tools

### 4.1 `evaluate_buy_request`
Evaluate buyer request against merchant policy.

```json
{
  "tool": "evaluate_buy_request",
  "args": {
    "negotiation_id": "uuid",
    "buyer_quantity": 100,
    "buyer_max_unit_price": "11000.00",
    "buyer_max_delivery_days": 7,
    "buyer_min_warranty_months": 12
  }
}
```

**Response (from deterministic backend):**
```json
{
  "feasible": true,
  "calculated_unit_price": "10819.20",
  "bulk_discount_applied_pct": "8.00",
  "upfront_discount_applied_pct": "2.00",
  "minimum_price": "10500.00",
  "delivery_days_available": 5,
  "warranty_months_offered": 24,
  "autonomous_limit": "1000000.00",
  "total_would_be": "1081920.00",
  "requires_approval": false
}
```

### 4.2 `generate_offer`
Generate an offer for the buyer. All prices validated by backend before sending.

```json
{
  "tool": "generate_offer",
  "args": {
    "negotiation_id": "uuid",
    "proposed_unit_price": "10820.00",
    "proposed_quantity": 100,
    "proposed_delivery_days": 5,
    "proposed_warranty_months": 24,
    "payment_terms": "upfront",
    "message": "Best price for 100 units with upfront payment"
  }
}
```

**Backend validation before sending:**
- `proposed_unit_price` >= `minimum_price` → otherwise REJECT tool call
- `proposed_unit_price` * `proposed_quantity` <= `autonomous_limit` → otherwise flag for approval

### 4.3 `request_human_approval`
Escalate to human merchant for large transactions.

```json
{
  "tool": "request_human_approval",
  "args": {
    "negotiation_id": "uuid",
    "reason": "Transaction total ₹15,00,000 exceeds autonomous limit of ₹10,00,000",
    "proposed_total": "1500000.00",
    "autonomous_limit": "1000000.00"
  }
}
```

### 4.4 `reject_buy_request`
Reject buyer's request.

```json
{
  "tool": "reject_buy_request",
  "args": {
    "negotiation_id": "uuid",
    "reason": "Product out of stock for requested quantity"
  }
}
```

---

## 5. Negotiation Message Format

Every message in the negotiation is stored with full attribution:

```json
{
  "id": "uuid",
  "negotiation_id": "uuid",
  "timestamp": "2026-08-22T17:00:00Z",
  "sender": "buyer_agent" | "merchant_agent" | "system",
  "type": "request" | "offer" | "counteroffer" | "accept" | "reject" | "system_event",
  "content": "Human-readable message text",
  "structured_data": {
    "unit_price": "10820.00",
    "quantity": 100,
    "delivery_days": 5,
    "warranty_months": 24,
    "payment_terms": "upfront"
  },
  "tool_call": "accept_offer",
  "policy_pre_check": null | "PASS" | "FAIL",
  "audit_event_id": "uuid"
}
```

---

## 6. System Prompt Templates

### 6.1 Buyer Agent System Prompt

```
You are an AI procurement agent for {buyer_name}. Your job is to purchase 
products on behalf of your principal, within strict constraints.

CONSTRAINTS (do not exceed these):
- Product: {product_query}
- Maximum quantity: {max_quantity}
- Maximum total budget: ₹{max_budget}
- Maximum unit price: ₹{max_unit_price}
- Maximum delivery: {max_delivery_days} days
- Minimum warranty: {min_warranty_months} months
- Preferred payment: {payment_terms}

RULES:
1. You MUST use tools for all external actions.
2. You CANNOT directly calculate or propose prices — always request evaluation.
3. You CANNOT authorize payment — that is handled by the payment layer.
4. You must provide a clear reason for every decision (for audit trail).
5. If an offer is within constraints, ACCEPT IT. Do not negotiate further unnecessarily.
6. If no acceptable offer is available after {max_rounds} rounds, REJECT.

Your goal: Acquire the product within constraints as efficiently as possible.
```

### 6.2 Merchant Agent System Prompt

```
You are an AI sales agent for {merchant_name}. Your job is to sell products
to buyer agents within your configured economic policies.

PRODUCT: {product_name}
BASE PRICE: ₹{base_price}/unit
MINIMUM PRICE: ₹{minimum_price}/unit (NEVER go below this — this is enforced)
BULK DISCOUNTS: {bulk_discount_tiers}
UPFRONT DISCOUNT: {upfront_discount_pct}%
AUTONOMOUS LIMIT: ₹{autonomous_limit}
DELIVERY: {min_delivery_days}–{max_delivery_days} days
WARRANTY: {warranty_months} months

RULES:
1. You MUST use tools for all external actions.
2. You MUST NEVER propose a unit price below ₹{minimum_price}.
3. If a buyer requests a price below minimum, counter at ₹{minimum_price} or reject.
4. If total exceeds ₹{autonomous_limit}, you MUST request human approval.
5. Apply bulk discounts automatically for qualifying quantities.
6. Apply upfront payment discount when buyer selects upfront payment.
7. Provide clear reasoning for every decision (for audit trail).

Your goal: Close deals profitably within policy boundaries.
```

---

## 7. Error Handling Protocol

### 7.1 Invalid Tool Arguments (Failure Case 7)

```
1. LLM generates tool call with invalid arguments
2. Pydantic validation raises ValidationError
3. Error details formatted as tool response:
   {
     "error": "INVALID_TOOL_ARGS",
     "tool": "submit_buy_request",
     "validation_errors": [
       {"field": "quantity", "error": "value must be greater than 0", "received": -5}
     ]
   }
4. Error returned to LLM
5. LLM retries with corrected arguments
6. Max 3 retries → if still failing → audit event INVALID_TOOL_ARGS, negotiation paused
```

### 7.2 Tool Execution Failure

If a tool call is syntactically valid but semantically blocked (e.g., policy FAIL):
```json
{
  "error": "POLICY_REJECTED",
  "tool": "generate_offer",
  "reason": "Proposed unit_price 9500.00 is below merchant minimum 10500.00",
  "policy_check": "MERCHANT_MIN_PRICE"
}
```

---

## 8. Round Limits

| Parameter | Default | Configurable |
|-----------|---------|--------------|
| `max_negotiation_rounds` | 10 | Per merchant policy |
| `negotiation_timeout_minutes` | 30 | Per merchant policy |
| `max_tool_retries` | 3 | System-wide |

If `max_negotiation_rounds` reached without agreement: auto-REJECT with reason "Max rounds exceeded."
