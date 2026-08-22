# NEXORA — Database Schema

**Version:** 1.0  
**Date:** August 22, 2026  
**Status:** Canonical Reference

---

## 1. Schema Principles

- All monetary values stored as `NUMERIC(18, 2)` — never FLOAT or REAL
- All IDs use UUID v4
- All timestamps in UTC
- All tables have `created_at` and `updated_at`
- `audit_events` is append-only (no UPDATE/DELETE in application code)
- `webhook_events` has unique constraint on `event_id` for idempotency
- Foreign keys enforced at DB level

---

## 2. Entity Relationship Diagram

```
merchants ──────────────────┐
    │                        │
    │ 1:many                 │
    ▼                        │
merchant_policies           │
    │                        │
    │                        │
products                    │
    │                        │
    └──────────┐             │
               │             │
buyers         │             │
    │          │             │
    │ 1:many   │ n:m         │
    ▼          ▼             ▼
buyer_policies  negotiations ──────── negotiation_messages
                    │
                    │ 1:1
                    ▼
                agreements
                    │
                    ├──── payments
                    ├──── approval_requests
                    └──── audit_events

webhook_events (standalone, idempotency log)
```

---

## 3. Table Definitions

### merchants

```sql
CREATE TABLE merchants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    api_key_hash    VARCHAR(255),           -- for simple auth (mvp)
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### buyers

```sql
CREATE TABLE buyers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    organization    VARCHAR(255),
    email           VARCHAR(255) UNIQUE NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### products

```sql
CREATE TABLE products (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id     UUID NOT NULL REFERENCES merchants(id),
    name            VARCHAR(255) NOT NULL,
    sku             VARCHAR(100) UNIQUE NOT NULL,
    description     TEXT,
    base_price      NUMERIC(18, 2) NOT NULL CHECK (base_price > 0),
    currency        CHAR(3) NOT NULL DEFAULT 'INR',
    available_stock INT NOT NULL DEFAULT 0 CHECK (available_stock >= 0),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_products_merchant_id ON products(merchant_id);
```

### merchant_policies

```sql
CREATE TABLE merchant_policies (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id             UUID NOT NULL REFERENCES merchants(id),
    product_id              UUID NOT NULL REFERENCES products(id),
    base_price              NUMERIC(18, 2) NOT NULL CHECK (base_price > 0),
    minimum_price           NUMERIC(18, 2) NOT NULL CHECK (minimum_price > 0),
    upfront_discount_pct    NUMERIC(5, 2) NOT NULL DEFAULT 0 CHECK (upfront_discount_pct >= 0 AND upfront_discount_pct <= 100),
    autonomous_limit        NUMERIC(18, 2) NOT NULL CHECK (autonomous_limit > 0),
    max_delivery_days       INT NOT NULL DEFAULT 7 CHECK (max_delivery_days > 0),
    min_warranty_months     INT NOT NULL DEFAULT 12 CHECK (min_warranty_months >= 0),
    allowed_payment_terms   TEXT[] NOT NULL DEFAULT ARRAY['upfront', 'net30'],
    max_negotiation_rounds  INT NOT NULL DEFAULT 10,
    is_active               BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT minimum_lte_base CHECK (minimum_price <= base_price),
    UNIQUE (merchant_id, product_id)
);
```

### bulk_discount_tiers

```sql
CREATE TABLE bulk_discount_tiers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id       UUID NOT NULL REFERENCES merchant_policies(id) ON DELETE CASCADE,
    min_quantity    INT NOT NULL CHECK (min_quantity > 0),
    discount_pct    NUMERIC(5, 2) NOT NULL CHECK (discount_pct >= 0 AND discount_pct <= 100),
    
    UNIQUE (policy_id, min_quantity)
);

CREATE INDEX idx_bulk_discount_policy ON bulk_discount_tiers(policy_id);
```

### buyer_policies

```sql
CREATE TABLE buyer_policies (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    buyer_id            UUID NOT NULL REFERENCES buyers(id) UNIQUE,
    max_budget          NUMERIC(18, 2) NOT NULL CHECK (max_budget > 0),
    max_delivery_days   INT NOT NULL DEFAULT 7 CHECK (max_delivery_days > 0),
    min_warranty_months INT NOT NULL DEFAULT 12 CHECK (min_warranty_months >= 0),
    allowed_merchants   UUID[] DEFAULT NULL,   -- NULL = any merchant
    preferred_payment   VARCHAR(50) DEFAULT 'upfront',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### negotiations

```sql
CREATE TYPE negotiation_status AS ENUM (
    'DISCOVER',
    'REQUEST',
    'OFFER',
    'COUNTER_OFFER',
    'ACCEPT',
    'REJECT',
    'EXPIRE',
    'AGREEMENT_CREATED'
);

CREATE TABLE negotiations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id     UUID NOT NULL REFERENCES merchants(id),
    buyer_id        UUID NOT NULL REFERENCES buyers(id),
    product_id      UUID NOT NULL REFERENCES products(id),
    status          negotiation_status NOT NULL DEFAULT 'DISCOVER',
    round_count     INT NOT NULL DEFAULT 0,
    max_rounds      INT NOT NULL DEFAULT 10,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL,   -- started_at + 30 minutes
    ended_at        TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_negotiations_buyer ON negotiations(buyer_id);
CREATE INDEX idx_negotiations_merchant ON negotiations(merchant_id);
CREATE INDEX idx_negotiations_status ON negotiations(status);
```

### negotiation_messages

```sql
CREATE TYPE message_sender AS ENUM ('buyer_agent', 'merchant_agent', 'system');
CREATE TYPE message_type AS ENUM ('request', 'offer', 'counteroffer', 'accept', 'reject', 'system_event');

CREATE TABLE negotiation_messages (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    negotiation_id      UUID NOT NULL REFERENCES negotiations(id) ON DELETE CASCADE,
    sender              message_sender NOT NULL,
    type                message_type NOT NULL,
    content             TEXT NOT NULL,
    structured_data     JSONB,             -- {unit_price, quantity, delivery_days, ...}
    tool_call           VARCHAR(100),      -- which tool was called
    policy_pre_check    VARCHAR(20),       -- PASS | FAIL | null
    round_number        INT NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_negotiation ON negotiation_messages(negotiation_id, created_at);
```

### agreements

```sql
CREATE TYPE agreement_status AS ENUM (
    'PENDING_VALIDATION',
    'VALIDATED',
    'VALIDATION_FAILED',
    'PENDING_APPROVAL',
    'APPROVED',
    'PAYMENT_INITIATED',
    'PAYMENT_CAPTURED',
    'PAYMENT_FAILED',
    'EXPIRED',
    'CANCELLED'
);

CREATE TABLE agreements (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id             UUID NOT NULL REFERENCES merchants(id),
    buyer_id                UUID NOT NULL REFERENCES buyers(id),
    negotiation_id          UUID NOT NULL REFERENCES negotiations(id) UNIQUE,
    product_id              UUID NOT NULL REFERENCES products(id),
    product_name            VARCHAR(255) NOT NULL,
    
    -- Commercial terms (immutable after PENDING_VALIDATION)
    quantity                INT NOT NULL CHECK (quantity > 0),
    unit_price              NUMERIC(18, 2) NOT NULL CHECK (unit_price > 0),
    total_amount            NUMERIC(18, 2) NOT NULL CHECK (total_amount > 0),
    currency                CHAR(3) NOT NULL DEFAULT 'INR',
    payment_terms           VARCHAR(50) NOT NULL,
    discounts_applied       JSONB,
    
    -- Delivery & warranty
    delivery_days           INT NOT NULL,
    warranty_months         INT NOT NULL,
    
    -- Payment
    razorpay_order_id       VARCHAR(255) UNIQUE,
    razorpay_payment_id     VARCHAR(255) UNIQUE,
    payment_captured_at     TIMESTAMPTZ,
    payment_amount_paise    BIGINT,        -- verified amount in paise
    
    -- Policy validation
    policy_decision         VARCHAR(50),
    policy_checks           JSONB,
    policy_validated_at     TIMESTAMPTZ,
    blocking_reason         TEXT,
    
    -- Integrity
    agreement_hash          VARCHAR(64),   -- SHA-256 of commercial terms
    
    -- Lifecycle
    status                  agreement_status NOT NULL DEFAULT 'PENDING_VALIDATION',
    expires_at              TIMESTAMPTZ NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_agreements_merchant ON agreements(merchant_id);
CREATE INDEX idx_agreements_buyer ON agreements(buyer_id);
CREATE INDEX idx_agreements_status ON agreements(status);
CREATE INDEX idx_agreements_razorpay_order ON agreements(razorpay_order_id);
```

### approval_requests

```sql
CREATE TYPE approval_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED', 'EXPIRED');

CREATE TABLE approval_requests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agreement_id    UUID NOT NULL REFERENCES agreements(id) UNIQUE,
    merchant_id     UUID NOT NULL REFERENCES merchants(id),
    reason          TEXT NOT NULL,
    proposed_total  NUMERIC(18, 2) NOT NULL,
    autonomous_limit NUMERIC(18, 2) NOT NULL,
    status          approval_status NOT NULL DEFAULT 'PENDING',
    reviewed_by     VARCHAR(255),
    review_note     TEXT,
    reviewed_at     TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ NOT NULL,   -- 24h from created_at
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_approvals_merchant ON approval_requests(merchant_id, status);
```

### webhook_events (Idempotency Log)

```sql
CREATE TABLE webhook_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id        VARCHAR(255) NOT NULL UNIQUE,  -- X-Razorpay-Event-Id
    event_type      VARCHAR(100) NOT NULL,
    payload         JSONB NOT NULL,
    processed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    agreement_id    UUID REFERENCES agreements(id),
    processing_result VARCHAR(50) NOT NULL DEFAULT 'SUCCESS'
);

CREATE UNIQUE INDEX idx_webhook_event_id ON webhook_events(event_id);
```

### audit_events

```sql
CREATE TYPE agent_type AS ENUM ('buyer_agent', 'merchant_agent', 'system', 'human');
CREATE TYPE audit_action AS ENUM (
    'NEGOTIATION_STARTED', 'OFFER_GENERATED', 'COUNTEROFFER_SUBMITTED',
    'OFFER_ACCEPTED', 'OFFER_REJECTED', 'AGREEMENT_CREATED',
    'POLICY_VALIDATED', 'POLICY_BLOCKED',
    'PAYMENT_AUTHORIZED', 'PAYMENT_BLOCKED', 'PAYMENT_CAPTURED', 'PAYMENT_FAILED',
    'PAYMENT_AMOUNT_MISMATCH',
    'HUMAN_APPROVAL_REQUESTED', 'HUMAN_APPROVED', 'HUMAN_REJECTED',
    'WEBHOOK_RECEIVED', 'WEBHOOK_DUPLICATE', 'WEBHOOK_INVALID_SIGNATURE',
    'INVALID_TOOL_ARGS', 'NEGOTIATION_EXPIRED', 'NEGOTIATION_MAX_ROUNDS'
);

CREATE TABLE audit_events (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    session_id          UUID,              -- negotiation_id
    agreement_id        UUID,
    agent_id            VARCHAR(100) NOT NULL,
    agent_type          agent_type NOT NULL,
    action              audit_action NOT NULL,
    input_summary       TEXT,
    decision            VARCHAR(50),
    policy_checked      VARCHAR(100),
    policy_result       VARCHAR(50),
    razorpay_reference  VARCHAR(255),
    result              TEXT NOT NULL,
    failure_reason      TEXT
    -- NO updated_at — this table is append-only
);

CREATE INDEX idx_audit_timestamp ON audit_events(timestamp DESC);
CREATE INDEX idx_audit_agreement ON audit_events(agreement_id);
CREATE INDEX idx_audit_session ON audit_events(session_id);
CREATE INDEX idx_audit_action ON audit_events(action);
```

---

## 4. Seed Data

### Demo Merchant
```json
{
  "name": "TechSupply Pro",
  "email": "merchant@demo.nexora.ai"
}
```

### Demo Product
```json
{
  "name": "Dell 24\" FHD Monitor",
  "sku": "DELL-24-FHD-001",
  "description": "Dell 24-inch Full HD IPS Display (P2422H), 1920x1080, USB-C",
  "base_price": "12000.00",
  "currency": "INR",
  "available_stock": 500
}
```

### Demo Policy
```json
{
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
  "allowed_payment_terms": ["upfront", "net30"]
}
```

### Demo Buyer
```json
{
  "name": "Horizon Corp Procurement Agent",
  "organization": "Horizon Corp",
  "email": "buyer@demo.nexora.ai"
}
```

### Demo Buyer Policy
```json
{
  "max_budget": "1100000.00",
  "max_delivery_days": 7,
  "min_warranty_months": 12,
  "preferred_payment": "upfront"
}
```
