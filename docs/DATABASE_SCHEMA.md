# NEXORA — Database Schema

**Version:** 2.0 (Phase 2 Implementation)
**Date:** August 23, 2026
**Status:** Implemented & Verified

> This document reflects the **actual implemented schema** from Phase 2.
> Phase 0's DATABASE_SCHEMA.md was an early draft — this is the canonical reference.

---

## 1. Design Principles

| Principle | Implementation |
|-----------|----------------|
| Monetary values | `NUMERIC(18, 2)` — never FLOAT or REAL |
| All IDs | UUID v4 (`gen_random_uuid()`) |
| All timestamps | `TIMESTAMPTZ` UTC |
| Status fields | Controlled string enums with CHECK constraints |
| Financial history | RESTRICT deletion — never silently deleted by cascade |
| Append-only records | `NegotiationMessage` — no `updated_at`, no UPDATE in application code |
| Agreement immutability | Commercial terms set once; changes only via new negotiation lifecycle |

---

## 2. Three-Layer Truth Architecture

```
NegotiationMessage  →  "What did the agents say?"
Agreement           →  "What did they actually agree to?"
Payment             →  "What financially happened?"
```

These three entities must **never** be collapsed into one table or JSON blob.

---

## 3. Entity Relationship Diagram

```
merchants
    ├── policies        (CASCADE delete with merchant)
    ├── products        (CASCADE delete with merchant)
    └── negotiations    (RESTRICT — financial history protected)

buyers
    └── negotiations    (RESTRICT — financial history protected)

products
    └── negotiations    (RESTRICT — product being negotiated)

negotiations
    ├── negotiation_messages  (CASCADE delete with negotiation)
    └── agreement             (RESTRICT — cannot delete if agreement exists)

agreement
    ├── → merchant (RESTRICT)
    ├── → buyer    (RESTRICT)
    ├── → product  (RESTRICT, snapshot of product.name captured)
    └── payment    (RESTRICT — cannot delete if payment exists)
```

---

## 4. Table Definitions

### merchants

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| name | VARCHAR(255) | NOT NULL | |
| email | VARCHAR(255) | NOT NULL, UNIQUE | |
| description | TEXT | nullable | |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | active \| inactive \| suspended |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | onupdate trigger |

**Check constraints:**
- `ck_merchant_status`: `status IN ('active', 'inactive', 'suspended')`

**Indexes:**
- `idx_merchants_status` on `(status)`

---

### policies

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| merchant_id | UUID | FK→merchants.id ON DELETE CASCADE | |
| name | VARCHAR(255) | NOT NULL | e.g., "Default Policy" |
| minimum_price | NUMERIC(18,2) | NOT NULL, >0 | Floor price for negotiation |
| maximum_discount_percent | NUMERIC(5,2) | NOT NULL, 0-100 | Max % discount agent can offer |
| maximum_autonomous_transaction | NUMERIC(18,2) | NOT NULL, >0 | Agent autonomous limit |
| human_approval_required | BOOLEAN | NOT NULL, DEFAULT false | Override: always require human |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | |
| max_negotiation_rounds | INTEGER | NOT NULL, DEFAULT 10, >0 | |
| max_delivery_days | INTEGER | NOT NULL, DEFAULT 7, >0 | |
| min_warranty_months | INTEGER | NOT NULL, DEFAULT 12, ≥0 | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Check constraints:**
- `ck_policy_minimum_price_positive`: `minimum_price > 0`
- `ck_policy_discount_range`: `maximum_discount_percent >= 0 AND <= 100`
- `ck_policy_autonomous_limit_positive`: `maximum_autonomous_transaction > 0`
- `ck_policy_max_rounds_positive`: `max_negotiation_rounds > 0`

**Indexes:**
- `idx_policies_merchant_id` on `(merchant_id)`

> **Design note:** All financial constraints are explicit typed columns — not opaque JSONB.
> This is intentional: the Policy Engine must be able to read and validate these deterministically.

---

### buyers

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| name | VARCHAR(255) | NOT NULL | |
| email | VARCHAR(255) | NOT NULL, UNIQUE | |
| organization | VARCHAR(255) | nullable | |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | active \| inactive \| blocked |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Check constraints:**
- `ck_buyer_status`: `status IN ('active', 'inactive', 'blocked')`

**Indexes:**
- `idx_buyers_status` on `(status)`

---

### products

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| merchant_id | UUID | FK→merchants.id ON DELETE CASCADE | |
| name | VARCHAR(255) | NOT NULL | |
| description | TEXT | nullable | |
| sku | VARCHAR(100) | NOT NULL | NOT globally unique — see composite unique |
| price | NUMERIC(18,2) | NOT NULL, >0 | Current catalog price |
| currency | CHAR(3) | NOT NULL, DEFAULT 'INR' | |
| inventory | INTEGER | NOT NULL, DEFAULT 0, ≥0 | |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | active \| inactive \| out_of_stock |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Unique constraints:**
- `uq_product_merchant_sku`: `(merchant_id, sku)` — SKU unique **per merchant only**

**Check constraints:**
- `ck_product_price_positive`: `price > 0`
- `ck_product_inventory_non_negative`: `inventory >= 0`
- `ck_product_status`: `status IN ('active', 'inactive', 'out_of_stock')`

**Indexes:**
- `idx_products_merchant_id` on `(merchant_id)`
- `idx_products_status` on `(status)`

> **Design note:** Two merchants may have the same SKU string. The composite unique constraint
> `(merchant_id, sku)` is the correct behaviour — not a global unique on `sku` alone.

---

### negotiations

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| buyer_id | UUID | FK→buyers.id ON DELETE RESTRICT | |
| merchant_id | UUID | FK→merchants.id ON DELETE RESTRICT | |
| product_id | UUID | FK→products.id ON DELETE RESTRICT | |
| state | VARCHAR(20) | NOT NULL, DEFAULT 'discover' | Controlled enum |
| round_count | INTEGER | NOT NULL, DEFAULT 0, ≥0 | |
| max_rounds | INTEGER | NOT NULL, DEFAULT 10, >0 | |
| started_at | TIMESTAMPTZ | NOT NULL | |
| expires_at | TIMESTAMPTZ | nullable | |
| ended_at | TIMESTAMPTZ | nullable | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Valid states:**

| State | Meaning |
|-------|---------|
| discover | Initial contact phase |
| request | Buyer has formally requested a quote |
| offer | Merchant has made an offer |
| counter_offer | Counter-offer in progress |
| accepted | Both parties agreed (**terminal**) |
| rejected | Negotiation rejected (**terminal**) |
| expired | Negotiation timed out (**terminal**) |

**Check constraints:**
- `ck_negotiation_state`: `state IN ('discover', 'request', 'offer', 'counter_offer', 'accepted', 'rejected', 'expired')`

**Indexes:**
- `idx_negotiations_buyer_id` on `(buyer_id)`
- `idx_negotiations_merchant_id` on `(merchant_id)`
- `idx_negotiations_state` on `(state)`

---

### negotiation_messages

**APPEND-ONLY** — no UPDATE or DELETE in application code.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| negotiation_id | UUID | FK→negotiations.id ON DELETE CASCADE | |
| sender_type | VARCHAR(20) | NOT NULL | buyer_agent \| merchant_agent \| system |
| sender_id | VARCHAR(255) | NOT NULL | Logical agent ID (not always a FK) |
| message_type | VARCHAR(20) | NOT NULL | request \| offer \| counter_offer \| accept \| reject \| system_event |
| content | TEXT | nullable | Human-readable "what the agent said" |
| payload | JSONB | nullable | Semi-structured terms (prices as strings) |
| sequence_number | INTEGER | NOT NULL, >0 | Ordered within negotiation |
| created_at | TIMESTAMPTZ | NOT NULL | No `updated_at` — append-only |

**Unique constraints:**
- `uq_message_negotiation_sequence`: `(negotiation_id, sequence_number)`

**Check constraints:**
- `ck_message_sender_type`: `sender_type IN ('buyer_agent', 'merchant_agent', 'system')`
- `ck_message_type`: `message_type IN ('request', 'offer', 'counter_offer', 'accept', 'reject', 'system_event')`
- `ck_message_sequence_positive`: `sequence_number > 0`

**Indexes:**
- `idx_messages_negotiation_id` on `(negotiation_id)`

> **Design note:** `payload` JSONB stores negotiation terms but is NOT canonical financial truth.
> Canonical terms are copied to Agreement typed columns when the negotiation is accepted.
> Prices in payload are stored as **strings** to preserve Decimal precision.

---

### agreements

**IMMUTABLE** after creation — commercial terms must never change.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| negotiation_id | UUID | FK→negotiations.id ON DELETE RESTRICT, UNIQUE | One-to-one with negotiation |
| merchant_id | UUID | FK→merchants.id ON DELETE RESTRICT | |
| buyer_id | UUID | FK→buyers.id ON DELETE RESTRICT | |
| product_id | UUID | FK→products.id ON DELETE RESTRICT | |
| product_name | VARCHAR(255) | NOT NULL | Snapshot at agreement time |
| quantity | INTEGER | NOT NULL, >0 | |
| unit_price | NUMERIC(18,2) | NOT NULL, >0 | Negotiated price (NOT current product price) |
| total_amount | NUMERIC(18,2) | NOT NULL, >0 | Must equal quantity × unit_price |
| currency | CHAR(3) | NOT NULL, DEFAULT 'INR' | |
| payment_terms | VARCHAR(50) | NOT NULL | e.g., 'upfront', 'net30' |
| delivery_days | INTEGER | NOT NULL, >0 | |
| warranty_months | INTEGER | NOT NULL, ≥0 | |
| discounts_applied | JSONB | nullable | Informational only (canonical price is unit_price) |
| policy_decision | VARCHAR(50) | nullable | PASS \| FAIL \| REQUIRES_HUMAN_APPROVAL |
| policy_checks | JSONB | nullable | Policy Engine check results |
| policy_validated_at | TIMESTAMPTZ | nullable | |
| blocking_reason | TEXT | nullable | Set if policy FAIL |
| agreement_hash | VARCHAR(64) | nullable | SHA-256 of immutable commercial fields |
| status | VARCHAR(30) | NOT NULL, DEFAULT 'pending_validation' | Controlled enum |
| expires_at | TIMESTAMPTZ | nullable | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Valid statuses:**

| Status | Terminal | Notes |
|--------|----------|-------|
| pending_validation | No | Awaiting Policy Engine |
| validated | No | Policy Engine passed |
| validation_failed | **Yes** | Policy Engine rejected |
| pending_approval | No | Awaiting human approval |
| approved | No | Human approved |
| payment_initiated | No | Razorpay order created |
| payment_captured | **Yes** | Payment confirmed |
| payment_failed | **Yes** | Payment failed |
| expired | **Yes** | Agreement expired |
| cancelled | **Yes** | Cancelled |

**Check constraints:**
- `ck_agreement_quantity_positive`: `quantity > 0`
- `ck_agreement_unit_price_positive`: `unit_price > 0`
- `ck_agreement_total_positive`: `total_amount > 0`
- `ck_agreement_delivery_positive`: `delivery_days > 0`
- `ck_agreement_warranty_non_negative`: `warranty_months >= 0`

**Indexes:**
- `idx_agreements_negotiation_id` on `(negotiation_id)`
- `idx_agreements_merchant_id` on `(merchant_id)`
- `idx_agreements_buyer_id` on `(buyer_id)`
- `idx_agreements_status` on `(status)`

> **Agreement Snapshot Principle:**
> `unit_price` captures the **negotiated** price, NOT the current product catalog price.
> If the product price changes after an agreement is created, the agreement is unaffected.
> This is intentional denormalization for historical correctness.

> **Agreement Total Integrity:**
> The Policy Engine (Phase 4) independently calculates `quantity × unit_price` using `Decimal`
> and compares it to `total_amount`. A mismatch rejects the agreement with `VALIDATION_FAILED`.

---

### payments

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| agreement_id | UUID | FK→agreements.id ON DELETE RESTRICT, UNIQUE | One-to-one with agreement |
| razorpay_order_id | VARCHAR(255) | NOT NULL, UNIQUE | Created at payment initiation |
| razorpay_payment_id | VARCHAR(255) | nullable, UNIQUE | Set after Razorpay captures |
| amount | NUMERIC(18,2) | NOT NULL, >0 | Must match agreement.total_amount |
| amount_paise | BIGINT | nullable | Amount in paise for Razorpay API |
| currency | CHAR(3) | NOT NULL, DEFAULT 'INR' | |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'created' | Controlled enum |
| captured_at | TIMESTAMPTZ | nullable | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Valid statuses:** `created` → `authorized` → `captured` (terminal); `failed`, `refunded`, `cancelled` (terminal)

**Check constraints:**
- `ck_payment_amount_positive`: `amount > 0`
- `ck_payment_status`: `status IN ('created', 'authorized', 'captured', 'failed', 'refunded', 'cancelled')`

**Indexes:**
- `idx_payments_agreement_id` on `(agreement_id)`
- `idx_payments_razorpay_order_id` on `(razorpay_order_id)`
- `idx_payments_status` on `(status)`

---

## 5. Deletion Behavior Summary

| Relationship | ON DELETE | Rationale |
|---|---|---|
| Merchant → Policy | CASCADE | Policies are merchant-owned config |
| Merchant → Product | CASCADE | Products are merchant-owned catalog |
| Merchant → Negotiation | RESTRICT | Financial history protected |
| Buyer → Negotiation | RESTRICT | Financial history protected |
| Product → Negotiation | RESTRICT | Product in negotiation is protected |
| Negotiation → Messages | CASCADE | Messages are part of negotiation |
| Negotiation → Agreement | RESTRICT | Cannot delete negotiation with agreement |
| Merchant → Agreement | RESTRICT | Financial record protected |
| Buyer → Agreement | RESTRICT | Financial record protected |
| Product → Agreement | RESTRICT | Financial record protected |
| Agreement → Payment | RESTRICT | Payment is financial record |

---

## 6. Currency Strategy

- Default currency: `INR`
- Currency stored as `CHAR(3)` (ISO 4217)
- Razorpay API uses paise: `amount_paise = int(amount * 100)`
- `Decimal` used throughout Python — never `float`
- Multi-currency support deferred to a future phase

---

## 7. UUID Strategy

- All primary keys use PostgreSQL `gen_random_uuid()` server-side
- Python model defaults also use `uuid.uuid4()` for in-memory creation
- `sa.UUID(as_uuid=True)` — Python receives native `uuid.UUID` objects, not strings
- No integer IDs anywhere in the domain models

---

## 8. Phase 2 Deviations from Phase 0 Architecture

| Item | Phase 0 Plan | Phase 2 Decision | Reason |
|------|-------------|-----------------|--------|
| Policy scope | Per-product (merchant_policies.product_id) | Merchant-level policy | Policy Engine operates at merchant level; per-product is premature |
| Razorpay fields | In Agreement table | Separate Payment table | Enforces 3-layer truth separation |
| Status as boolean | `is_active BOOLEAN` | Controlled string enum | `suspended` ≠ `inactive`; better auditability |
| `buyer_policies` table | In Phase 0 schema | Deferred to later phase | Not required for Phase 2 model foundation |
| `audit_events` table | In Phase 0 schema | Deferred to later phase | Append-only audit log implemented in Phase 10 |
| `approval_requests` table | In Phase 0 schema | Deferred to later phase | Human approval flow in Phase 8 |
| `webhook_events` table | In Phase 0 schema | Deferred to later phase | Webhook handling in Phase 11 |
