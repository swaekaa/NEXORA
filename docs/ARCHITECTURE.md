# NEXORA — System Architecture

**Version:** 1.0  
**Date:** August 22, 2026  
**Status:** Approved for Implementation

---

## 1. Architectural Philosophy

NEXORA is built around one foundational principle:

> **LLMs propose. Deterministic systems decide.**

This is not a philosophical constraint — it is a financial safety requirement. In any system where an LLM can directly execute payments, the system is only as reliable as the LLM's ability to be perfectly consistent, hallucination-free, and manipulation-resistant. That is an impossible guarantee.

NEXORA's architecture makes the boundary explicit, structural, and enforced at the code level.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         LLM LAYER                                   │
│  - Understand natural language intent                               │
│  - Generate negotiation proposals (text)                            │
│  - Evaluate contextual trade-offs                                   │
│  - Request tool calls (structured schema)                           │
│  - Explain agent decisions (audit-friendly)                         │
│  - Decide WHICH tool to call, NOT the financial outcome             │
└────────────────────────────┬────────────────────────────────────────┘
                             │ Structured Tool Call (Pydantic-validated)
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    DETERMINISTIC LAYER                               │
│  - Calculate all prices, totals, discounts                          │
│  - Validate against merchant policy                                 │
│  - Validate against buyer policy                                    │
│  - Validate agreement integrity                                     │
│  - Authorize or BLOCK payment                                       │
│  - Verify Razorpay webhook signatures                               │
│  - Maintain all financial state in database                         │
│  - Enforce idempotency                                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. System Components

### 2.1 Component Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        NEXORA SYSTEM                             │
│                                                                  │
│  ┌─────────────┐        ┌──────────────────┐                    │
│  │  BUYER UI   │        │  MERCHANT DASH   │                    │
│  │  (React)    │        │  (React)         │                    │
│  └──────┬──────┘        └────────┬─────────┘                    │
│         │ WebSocket/REST         │ REST                         │
│         ▼                        ▼                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   FastAPI Backend                         │   │
│  │                                                          │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐   │   │
│  │  │  AI BUYER   │  │ AI MERCHANT  │  │  NEGOTIATION  │   │   │
│  │  │   AGENT     │  │    AGENT     │  │    ENGINE     │   │   │
│  │  └──────┬──────┘  └──────┬───────┘  └───────┬───────┘   │   │
│  │         │                │                   │           │   │
│  │         └────────────────┴───────────────────┘           │   │
│  │                          │                               │   │
│  │                          ▼                               │   │
│  │              ┌────────────────────┐                      │   │
│  │              │  AGREEMENT ENGINE  │                      │   │
│  │              └─────────┬──────────┘                      │   │
│  │                        │                                 │   │
│  │                        ▼                                 │   │
│  │          ┌──────────────────────────┐                    │   │
│  │          │   POLICY ENGINE          │                    │   │
│  │          │   (100% deterministic)   │                    │   │
│  │          └─────────────┬────────────┘                    │   │
│  │                        │                                 │   │
│  │               PASS     │     FAIL                        │   │
│  │            ┌───────────┴──────────┐                      │   │
│  │            ▼                      ▼                      │   │
│  │  ┌──────────────────┐  ┌─────────────────────────────┐   │   │
│  │  │ PAYMENT AUTH     │  │  BLOCK + AUDIT EVENT        │   │   │
│  │  │ LAYER            │  │  (reason logged)            │   │   │
│  │  └────────┬─────────┘  └─────────────────────────────┘   │   │
│  │           │                                               │   │
│  │           ▼                                               │   │
│  │  ┌──────────────────┐         ┌────────────────────────┐ │   │
│  │  │  RAZORPAY        │         │  HUMAN APPROVAL        │ │   │
│  │  │  INTEGRATION     │         │  SYSTEM                │ │   │
│  │  └────────┬─────────┘         └────────────────────────┘ │   │
│  │           │                                               │   │
│  │           ▼                                               │   │
│  │  ┌──────────────────┐  ┌─────────────────────────────┐   │   │
│  │  │ WEBHOOK          │  │  AUDIT TRAIL                │   │   │
│  │  │ PROCESSOR        │  │  (immutable event log)      │   │   │
│  │  └──────────────────┘  └─────────────────────────────┘   │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    PostgreSQL                             │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Responsibilities

#### AI Buyer Agent
- Accepts natural-language procurement goals
- Maintains buyer constraint profile (budget, quantity, delivery, warranty)
- Discovers products from merchant catalog
- Generates negotiation requests and counteroffers (via LLM)
- Evaluates merchant offers against buyer constraints (LLM proposes, policy validates)
- Requests agreement creation (deterministic backend executes)
- Provides explanations for every decision

#### AI Merchant Agent
- Maintains merchant product catalog
- Evaluates buyer requests against merchant policies (deterministic)
- Generates offers and counteroffers within policy boundaries (LLM proposes, policy validates)
- Never offers price below configured minimum (policy enforced)
- Escalates to human approval when required
- Tracks negotiation state

#### Negotiation Engine (State Machine)
States: `DISCOVER → REQUEST → OFFER → COUNTER_OFFER → ACCEPT → REJECT | EXPIRE → AGREEMENT_CREATED`

- Manages negotiation lifecycle
- Tracks all messages and proposals
- Enforces time limits
- Detects agreement or deadlock
- Triggers agreement creation on ACCEPT

#### Agreement Engine
- Converts accepted negotiation into canonical Commercial Agreement (JSON)
- Agreement becomes immutable once created (status: PENDING_VALIDATION)
- Assigns unique agreement_id
- Triggers policy validation

#### Policy Engine (CRITICAL — 100% Deterministic)
- Implemented as a pure-Python module (`PolicyEngine`) with strict Decimal operations
- Validates merchant constraints: minimum price, max discount, autonomous limit
- Evaluates against the typed DB `Policy` schema (no legacy JSON parsing)
- Validates agreement integrity: calculated totals must match agreement totals exactly
- Returns typed PolicyResult: PASS (ALLOW) | FAIL (DENY) | REQUIRES_HUMAN_APPROVAL
- Precedence: DENY > REQUIRES_HUMAN_APPROVAL > ALLOW
- Zero external dependencies (no LLM, no network, no DB queries)

#### Payment Authorization Layer
- Only activates after PolicyEngine returns PASS
- Creates Razorpay Order (amount, currency, receipt)
- Stores order reference linked to agreement
- Returns payment instructions
- Handles human approval flow for transactions above autonomous limit

#### Razorpay Integration
- Uses Test Mode exclusively during development
- Creates Orders via `POST /v1/orders`
- Verifies payment signatures: `HMAC-SHA256(order_id|payment_id, key_secret)`
- Does NOT trust frontend payment state

#### Webhook Processor
- Receives Razorpay webhook events
- Verifies HMAC-SHA256 signature on raw request body
- Uses `X-Razorpay-Event-Id` for deduplication
- Processes events idempotently
- Updates agreement/payment state
- Emits audit events

#### Audit Trail
- Append-only event log
- Every agent decision, policy check, payment action recorded
- Structured fields: timestamp, agent_id, agent_type, action, policy_checked, result, reason
- Never stores LLM chain-of-thought — structured decisions only

#### Human Approval System
- Triggered when transaction exceeds merchant autonomous limit
- Merchant dashboard shows pending approvals
- Approve → payment authorization proceeds
- Reject → negotiation terminated, reason logged

---

## 3. Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Frontend** | React 18 + TypeScript + Vite | Fast dev, type-safe, modern |
| **UI Styling** | Vanilla CSS + CSS variables | Full control, no framework lock-in |
| **Backend** | Python 3.11+ + FastAPI | Async, fast, Pydantic-native |
| **ORM** | SQLAlchemy 2.0 (async) | Industry standard, composable |
| **DB** | PostgreSQL 15 | ACID, reliable, JSON support |
| **Migrations** | Alembic | SQLAlchemy-native |
| **Validation** | Pydantic v2 | Schema validation for agent tools |
| **LLM** | OpenAI GPT-4o or Claude Sonnet (tool-calling) | Best structured output support |
| **Payments** | Razorpay Python SDK | Official SDK |
| **Containerization** | Docker + Docker Compose | Demo reliability |
| **Testing** | pytest + httpx (async) | FastAPI recommended |

---

## 4. Data Flow: Happy Path

```
1. Buyer submits goal: "Buy 100 monitors under ₹11L, 7-day delivery"

2. BuyerAgent extracts constraints:
   product=monitor, qty=100, max_budget=1100000, max_delivery=7, warranty_months=12

3. BuyerAgent discovers merchant catalog (product: Dell 24" Monitor, base: ₹12,000/unit)

4. NegotiationEngine creates session (state: DISCOVER → REQUEST)

5. BuyerAgent generates opening offer:
   "100 units, ₹10,800 each (₹10.8L total), 7-day delivery, upfront payment"

6. MerchantAgent evaluates against policy:
   - min_price: ₹10,500 ✓
   - 100-unit discount: 8% → floor: ₹11,040/unit... buyer asked ₹10,800 — within 8% discount: ₹11,040 * 0.92 = ₹10,157 — wait, let me re-check
   - PolicyEngine calculates: base ₹12,000 * (1 - 0.08) = ₹11,040; upfront discount: ₹11,040 * (1 - 0.02) = ₹10,819.20; minimum: ₹10,500 ✓
   - Buyer asked ₹10,800 < ₹10,819.20 — MerchantAgent counters at ₹10,820 (rounded)

7. BuyerAgent evaluates counter: ₹10,820 * 100 = ₹10,82,000 < ₹11,00,000 budget ✓ ACCEPT

8. NegotiationEngine → state: ACCEPT → triggers AgreementEngine

9. AgreementEngine creates CommercialAgreement:
   {id, product, qty:100, unit_price:10820, total:1082000, currency:INR, delivery_days:5, warranty_months:24, payment_terms:upfront, status:PENDING_VALIDATION}

10. PolicyEngine validates:
    - merchant minimum: 10820 >= 10500 ✓
    - buyer budget: 1082000 <= 1100000 ✓
    - merchant autonomous limit: 1082000 > 1000000 ✗ (Exceeds autonomous limit)
    - calculated total: 100 * 10820 = 1082000 = agreement.total ✓
    → Result: REQUIRES_HUMAN_APPROVAL

11. Agreement status set to PENDING_APPROVAL. ApprovalRequest created for Merchant. Payment is BLOCKED.

12. Merchant reviews ApprovalRequest on Dashboard and clicks "Approve". Agreement status set to APPROVED.

13. PaymentAuthLayer creates Razorpay Order:
    POST /v1/orders {amount: 108200000 (paise), currency: INR, receipt: agreement.id}
    → razorpay_order_id saved to agreement

14. Frontend displays payment instructions (Test Mode card details)

15. Test payment executed (Razorpay Checkout / Test Card)

16. WebhookProcessor receives payment.captured event:
    - Verify X-Razorpay-Signature (HMAC-SHA256)
    - Check X-Razorpay-Event-Id not already processed
    - Verify payment amount matches agreement amount
    - Update agreement status: PAID
    - Emit audit event: PAYMENT_CAPTURED

17. AuditTrail records entire flow.
```

---

## 5. Data Flow: Failure Paths

See [FAILURE_HANDLING.md](FAILURE_HANDLING.md) for all 7 failure scenarios.

---

## 6. Security Boundaries

```
NEVER:
- Store Razorpay Key Secret in source code
- Trust frontend payment state
- Allow LLM to directly call Razorpay
- Expose webhook secret
- Store LLM chain-of-thought in audit log

ALWAYS:
- Verify webhook signature on raw body before parsing
- Check X-Razorpay-Event-Id for deduplication
- Validate all LLM tool outputs against Pydantic schemas
- Use Decimal for all monetary calculations
- Validate agreement totals independently of what LLM proposed
```

---

## 7. Architectural Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| LLM produces inconsistent negotiation proposals | Medium | Pydantic schema validation on all tool outputs; retry with error feedback |
| LLM hallucinates financial figures | High | PolicyEngine recalculates all figures independently; LLM cannot inject numbers into payment |
| Razorpay webhook delivery failure | Medium | Exponential backoff by Razorpay (24h); idempotent processing; status polling fallback |
| Race condition: duplicate payment attempt | High | Database unique constraint on razorpay_order_id; idempotency key on Razorpay Order creation |
| PostgreSQL connection pool exhaustion | Low | Async SQLAlchemy + connection pool config |
| Demo environment (ngrok) instability | Medium | Prepare fallback: local webhook simulation script |
| LLM rate limiting during demo | Medium | Cache negotiation responses; pre-load demo scenario |
| Agreement state corruption | High | Database transaction wrapping agreement creation + policy validation |

---

## 8. Deployment Architecture (MVP)

```
docker-compose.yml:
  - nexora-backend (FastAPI, port 8000)
  - nexora-frontend (Vite dev server, port 3000)
  - nexora-db (PostgreSQL, port 5432)
  - [Optional] ngrok tunnel for webhook testing
```

For the demo, all services run locally. Webhooks received via ngrok tunnel (or simulated via test script).
