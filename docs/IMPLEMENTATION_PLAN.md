# NEXORA — Implementation Plan

**Version:** 1.0  
**Date:** August 22, 2026  
**Status:** Approved for Execution  
**Deadline:** September 5, 2026

---

## Overview

NEXORA is implemented in 16 phases. Each phase has a clear objective, defined files, APIs, database changes, implementation tasks, tests, acceptance criteria, dependencies, and risks.

**Execution Order:** Phases 0–5 must be complete before Phase 6+. Phases can overlap where explicitly noted.

---

## Phase 0 — Architecture & Planning

### Objective
Complete system design, document all decisions, and establish the source of truth for implementation.

### Files Affected
```
docs/PRD.md
docs/ARCHITECTURE.md
docs/IMPLEMENTATION_PLAN.md  ← this file
docs/AGENT_PROTOCOL.md
docs/AGREEMENT_SPEC.md
docs/POLICY_ENGINE.md
docs/PAYMENT_FLOW.md
docs/WEBHOOK_STRATEGY.md
docs/SECURITY.md
docs/FAILURE_HANDLING.md
docs/DATABASE_SCHEMA.md
docs/API_SPEC.md
docs/TESTING_STRATEGY.md
docs/DEMO_SCENARIO.md
docs/RAZORPAY_INTEGRATION_NOTES.md
README.md
.gitignore
.env.example
```

### Implementation Tasks
- [x] Define product vision and problem statement
- [x] Research Razorpay APIs (Orders, Webhooks, MCP, Agent Studio)
- [x] Define LLM/deterministic boundary
- [x] Define negotiation state machine
- [x] Define commercial agreement schema
- [x] Define policy engine rules
- [x] Define payment lifecycle
- [x] Define webhook handling strategy
- [x] Define 7 failure scenarios
- [x] Define database schema
- [x] Define REST API spec
- [x] Define testing strategy
- [x] Script 5-minute demo scenario
- [x] Create all placeholder directories and files

### Acceptance Criteria
- All docs/ files exist with complete content
- Any engineer can read docs and understand what to build
- No ambiguity about what is LLM-owned vs deterministic
- Razorpay integration notes capture all API uncertainty

### Dependencies
- None (this is Phase 0)

### Risks
- Over-documenting slows down implementation → timebox this phase to 2 days max

---

## Phase 1 — Repository & Infrastructure

### Objective
Set up the working monorepo, environment configuration, Docker Compose, and development tooling.

### Files Affected
```
.gitignore
.env.example
docker-compose.yml
backend/requirements.txt
backend/requirements-dev.txt
backend/Dockerfile
backend/app/__init__.py
backend/app/main.py           ← skeleton FastAPI app
backend/app/config.py         ← Pydantic Settings
backend/tests/__init__.py
frontend/package.json
frontend/vite.config.ts
frontend/tsconfig.json
frontend/index.html
frontend/src/main.tsx
frontend/src/App.tsx
scripts/init_db.py
```

### APIs Required
- None yet (skeleton only)

### Database Changes
- None yet

### Implementation Tasks
- [x] 1. Create `backend/app/config.py` with Pydantic `Settings` class
- [x] 2. Create FastAPI `main.py` with health check endpoint
- [x] 3. Create Docker Compose with postgres, backend, frontend services
- [x] 4. Create `.env.example` with all required keys (no values)
- [x] 5. Initialize Vite React TypeScript frontend (scaffolded)
- [x] 6. Configure CORS in FastAPI
- [x] 7. Verify `GET /health` returns `{"status": "ok"}`

### Tests
- `test_health_endpoint` → GET /health returns 200
- `test_config_loads` → Settings loads from environment

### Acceptance Criteria
- `docker-compose up` starts all three services
- `GET http://localhost:8000/health` returns 200
- Frontend loads at `http://localhost:3000`
- No hardcoded secrets

### Dependencies
- Phase 0 complete

### Risks
- Docker networking issues on Windows → docum## Phase 2 — Database

**Status: ✅ COMPLETE (August 23, 2026)**
**Migration:** `create_core_nexora_domain_models` (run: `alembic upgrade head`)

### Objective
Create the PostgreSQL schema, SQLAlchemy models, and Alembic migrations for all core entities.

### Files Created
```
backend/app/models/merchant.py            ✅ Merchant, MerchantStatus
backend/app/models/buyer.py               ✅ Buyer, BuyerStatus
backend/app/models/policy.py              ✅ Policy (merchant-level financial constraints)
backend/app/models/product.py             ✅ Product, ProductStatus
backend/app/models/negotiation.py         ✅ Negotiation, NegotiationState enum
backend/app/models/negotiation_message.py ✅ NegotiationMessage, SenderType, MessageType
backend/app/models/agreement.py           ✅ Agreement, AgreementStatus enum
backend/app/models/payment.py             ✅ Payment, PaymentStatus enum
backend/app/models/__init__.py            ✅ All models exported for Alembic discovery
backend/tests/unit/test_models.py         ✅ Pure unit tests (no DB)
backend/tests/integration/test_database_models.py ✅ DB integration tests
```

### Files Modified
```
backend/alembic/env.py    ← Updated model imports for autogenerate
docs/DATABASE_SCHEMA.md   ← Rewritten with actual implemented schema
```

### Database Changes

**8 Core Tables Implemented:**

```
merchants             — Merchant profiles (status: active|inactive|suspended)
buyers                — Buyer profiles (status: active|inactive|blocked)
policies              — Merchant financial policy (typed columns, no opaque JSON)
products              — Merchant catalog (SKU unique per-merchant, not globally)
negotiations          — Negotiation state machine (7 controlled states)
negotiation_messages  — Append-only agent exchange (JSONB payload, strict sequence)
agreements            — Canonical commercial truth (immutable commercial terms)
payments              — Razorpay order/payment mapping
```

**Not implemented yet (deferred to later phases):**
- `buyer_policies` (Phase 4)
- `audit_events` (Phase 10)
- `approval_requests` (Phase 8)
- `webhook_events` (Phase 11)
- `bulk_discount_tiers` (Phase 4)

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Policy is merchant-level, not per-product | Policy Engine operates on merchant-level constraints |
| Razorpay IDs in separate Payment table | Enforces 3-layer truth (agreed vs happened) |
| Status as controlled string enum | `suspended ≠ inactive`; CHECK constraints at DB level |
| `NegotiationMessage.sequence_number` with UNIQUE | Prevents ambiguous message ordering |
| `Agreement.negotiation_id` UNIQUE | Enforces one-negotiation→one-agreement |
| All monetary fields NUMERIC(18,2) | Never float |
| RESTRICT on financial FK deletions | Financial history cannot be silently deleted |

### Acceptance Criteria Status

- [x] Merchant model implemented
- [x] Policy model implemented
- [x] Buyer model implemented
- [x] Product model implemented
- [x] Negotiation model implemented
- [x] NegotiationMessage model implemented
- [x] Agreement model implemented
- [x] Payment model implemented
- [x] All primary keys use UUID
- [x] All money uses Decimal/Numeric(18,2)
- [x] Currency stored explicitly (CHAR(3))
- [x] Product SKU unique per merchant
- [x] Inventory cannot be negative (CHECK constraint)
- [x] Negotiation states controlled (CHECK + Python enum)
- [x] Negotiation messages have ordered sequence numbers
- [x] Agreement has unique negotiation relationship
- [x] Agreement contains canonical financial snapshot
- [x] Payment maps to Razorpay order/payment IDs
- [x] Razorpay order ID is unique
- [x] Foreign keys correctly configured
- [x] Deletion behavior protects financial history
- [x] Appropriate indexes exist
- [x] Relationships work correctly
- [ ] Alembic migration run (requires live DB)
- [ ] Integration tests run (requires live DB)

### Dependencies
- Phase 1 complete ✅

---

---

## Phase 3 — Merchant Catalog

### Objective
Implement the merchant catalog API — product listing, merchant policy configuration, and catalog retrieval for the buyer agent.

### Files Affected
```
backend/app/schemas/merchant.py
backend/app/schemas/product.py
backend/app/schemas/policy.py
backend/app/services/catalog_service.py
backend/app/api/catalog.py             ← routes
backend/app/api/__init__.py
backend/app/main.py                    ← register routes
```

### APIs Required
- `GET /api/v1/catalog` — list available products
- `GET /api/v1/catalog/{product_id}` — get product detail with policy
- `GET /api/v1/merchants/{merchant_id}/policy` — get merchant policy
- `PUT /api/v1/merchants/{merchant_id}/policy` — update merchant policy (merchant dashboard)

### Database Changes
- Read from `products`, `merchants`, `merchant_policies` (created in Phase 2)

### Pydantic Schemas

```python
class MerchantPolicySchema(BaseModel):
    merchant_id: UUID
    product_id: UUID
    base_price: Decimal
    minimum_price: Decimal          # never allow below this
    bulk_discounts: list[BulkDiscountTier]
    upfront_discount_pct: Decimal
    autonomous_limit: Decimal       # max transaction without human approval
    max_delivery_days: int
    min_warranty_months: int
    allowed_payment_terms: list[str]
    
class BulkDiscountTier(BaseModel):
    min_quantity: int
    discount_pct: Decimal           # e.g., Decimal("5.00") = 5%

class ProductSchema(BaseModel):
    id: UUID
    merchant_id: UUID
    name: str
    description: str
    base_price: Decimal
    currency: str = "INR"
    available_stock: int
```

### Implementation Tasks
1. Implement Pydantic schemas for merchant, product, policy
2. Implement `CatalogService` with methods:
   - `get_products()` → list products
   - `get_product(product_id)` → product detail
   - `get_merchant_policy(merchant_id, product_id)` → full policy
3. Implement API routes
4. Wire routes into main.py
5. Test with seeded demo data

### Tests
- `test_get_catalog_returns_products`
- `test_get_product_includes_policy`
- `test_get_merchant_policy_structure_valid`

### Acceptance Criteria
- `GET /api/v1/catalog` returns seeded Dell Monitor
- Policy includes all discount tiers and autonomous limit
- All monetary values returned as strings (not floats) for JSON precision

### Dependencies
- Phase 2 complete

### Risks
- Returning Decimal as JSON → use `model_config = {"json_encoders": {Decimal: str}}`

---

## Phase 4 — Policy Engine

**Status: ✅ COMPLETE (August 24, 2026)**

### Objective
Implement the deterministic policy engine — the most critical component in NEXORA. This must be 100% deterministic, independently testable, and never touch the LLM.

### Files Created
```
backend/app/policies/__init__.py
backend/app/policies/enums.py
backend/app/policies/models.py
backend/app/policies/engine.py
backend/tests/unit/test_policy_engine.py
```

### Policy Engine Design
The policy engine was built as a pure-Python module (`PolicyEngine.evaluate()`) that receives a `PolicyEvaluationRequest` and `PolicyEvaluationContext`.

**Precedence:** `DENY > HUMAN_APPROVAL_REQUIRED > ALLOW`

**Rules Implemented (Deterministic, Decimal-only):**
1. `AGREEMENT_TOTAL_INTEGRITY` (DENY)
2. `AGREEMENT_CURRENCY` (DENY)
3. `MERCHANT_MIN_PRICE` (DENY)
4. `MERCHANT_MAX_DISCOUNT` (DENY)
5. `MERCHANT_HUMAN_APPROVAL_OVERRIDE` (HUMAN_APPROVAL_REQUIRED)
6. `MERCHANT_AUTONOMOUS_LIMIT` (HUMAN_APPROVAL_REQUIRED)

### Acceptance Criteria Met
- [x] PolicyEngine has 0 dependencies on LLM, database, or network calls
- [x] All monetary comparisons use strict `Decimal` math
- [x] Every failed check has a structured human-readable reason
- [x] Unit tests cover all boundary conditions (exact limit, 1 paise differences)
- [x] `REQUIRES_HUMAN_APPROVAL` correctly triggered at threshold, but overwritten if a hard `DENY` is present
- [x] Documentation updated to reflect the typed database schema rather than the legacy JSON specs

### Dependencies
- Phase 2 (schemas), Phase 3 (policy schemas) — Both Complete.

---

## Phase 5 — Buyer Agent

### Objective
Implement the AI Buyer Agent — an LLM-powered agent with structured tool calling that operates within buyer constraints and cannot directly execute financial actions.

### Files Affected
```
backend/app/agents/buyer/agent.py        ← BuyerAgent class
backend/app/agents/buyer/tools.py        ← tool definitions (Pydantic)
backend/app/agents/buyer/prompts.py      ← system prompt
backend/app/agents/buyer/constraints.py  ← buyer constraint handling
backend/app/schemas/buyer.py             ← buyer schemas
backend/app/services/buyer_service.py    ← buyer session management
backend/app/api/buyer.py                 ← buyer API routes
backend/tests/unit/test_buyer_agent.py
backend/tests/integration/test_buyer_flow.py
```

### APIs Required
- `POST /api/v1/buyer/session` — create buyer session
- `POST /api/v1/buyer/session/{session_id}/message` — send message to buyer agent
- `GET /api/v1/buyer/session/{session_id}` — get session state
- `GET /api/v1/buyer/session/{session_id}/messages` — get conversation history

### Buyer Agent Tools (Pydantic schemas required for all)

```python
class DiscoverProductsTool(BaseModel):
    """Search the merchant catalog for products matching criteria"""
    query: str
    max_results: int = 5

class SubmitBuyRequestTool(BaseModel):
    """Submit a purchase request to the merchant agent"""
    product_id: UUID
    quantity: int = Field(gt=0)
    max_unit_price: Decimal = Field(gt=0)
    max_delivery_days: int = Field(gt=0, le=365)
    min_warranty_months: int = Field(ge=0)
    payment_terms: Literal["upfront", "net30", "net60"]
    message: str  # human-readable context

class SubmitCounterOfferTool(BaseModel):
    """Submit a counteroffer during active negotiation"""
    negotiation_id: UUID
    proposed_unit_price: Decimal = Field(gt=0)
    proposed_quantity: int = Field(gt=0)
    message: str

class AcceptOfferTool(BaseModel):
    """Accept the current merchant offer"""
    negotiation_id: UUID
    accepted_unit_price: Decimal
    accepted_quantity: int
    reason: str  # for audit trail

class RejectOfferTool(BaseModel):
    """Reject the current merchant offer and terminate negotiation"""
    negotiation_id: UUID
    reason: str
```

### System Prompt Design Principles
- State constraints explicitly (budget, quantity, delivery, warranty)
- Never reveal that it's an LLM
- Explain reasoning in structured form for audit trail
- Use tools for all external actions
- Never calculate prices directly — request and evaluate
- Stop at ACCEPT or REJECT — no infinite loops

### Implementation Tasks
1. Design buyer system prompt
2. Implement all buyer tools with Pydantic schemas
3. Implement `BuyerAgent.run(goal: str, constraints: BuyerConstraints)` async method
4. Implement tool dispatch: tool calls → service layer → responses
5. Implement conversation history management
6. Add validation: LLM tool calls must match schema or retry with error
7. Add buyer API routes
8. Wire buyer agent to negotiation engine

### Tests
- `test_buyer_extracts_constraints_from_goal`
- `test_buyer_tool_schemas_valid` (Pydantic validation)
- `test_buyer_cannot_exceed_budget` (policy layer blocks)
- `test_buyer_accepts_valid_offer`
- `test_buyer_rejects_offer_over_budget`
- `test_invalid_tool_args_rejected` (Failure Case 7)

### Acceptance Criteria
- Buyer agent can extract constraints from natural language
- All tool calls validated against Pydantic schemas before execution
- Invalid LLM tool arguments cause structured error, not crash (Failure Case 7)
- Buyer agent cannot initiate payment directly

### Dependencies
- Phase 3 (catalog), Phase 4 (policy engine)

### Risks
- LLM output inconsistency → robust Pydantic validation + retry logic
- Infinite negotiation loops → max_rounds limit (e.g., 10)

---

## Phase 6 — Merchant Agent

### Objective
Implement the AI Merchant Agent — LLM-powered, policy-bounded, able to evaluate buyer requests, generate offers, and request human approval when appropriate.

### Files Affected
```
backend/app/agents/merchant/agent.py
backend/app/agents/merchant/tools.py
backend/app/agents/merchant/prompts.py
backend/app/schemas/merchant_agent.py
backend/app/services/merchant_service.py
backend/app/api/merchant.py
backend/tests/unit/test_merchant_agent.py
```

### Merchant Agent Tools

```python
class EvaluateBuyRequestTool(BaseModel):
    """Evaluate a buyer request against merchant policy"""
    negotiation_id: UUID
    buyer_quantity: int
    buyer_max_unit_price: Decimal
    buyer_max_delivery_days: int
    buyer_min_warranty_months: int

class GenerateOfferTool(BaseModel):
    """Generate an offer for the buyer within policy constraints"""
    negotiation_id: UUID
    proposed_unit_price: Decimal  # must be >= minimum_price (validated by policy)
    proposed_quantity: int
    proposed_delivery_days: int
    proposed_warranty_months: int
    payment_terms: str
    message: str

class RequestHumanApprovalTool(BaseModel):
    """Escalate to human merchant for approval"""
    negotiation_id: UUID
    reason: str
    proposed_total: Decimal
    autonomous_limit: Decimal

class RejectBuyRequestTool(BaseModel):
    """Reject the buyer's request"""
    negotiation_id: UUID
    reason: str
```

### Critical Rule — Price Floor
The merchant agent's system prompt must state explicitly:
> "You MUST NEVER propose a unit_price below {minimum_price}. If the buyer requests a price below this floor, you MUST either reject or counter at the minimum price. The policy engine will independently validate this."

### Implementation Tasks
1. Design merchant system prompt with policy variables injected
2. Implement all merchant tools
3. Implement `MerchantAgent.evaluate(request: BuyRequest)` method
4. Implement offer generation with policy pre-check
5. Implement human approval escalation pathway
6. Add API routes for merchant dashboard actions

### Tests
- `test_merchant_rejects_below_minimum_price` (Failure Case 2)
- `test_merchant_applies_correct_bulk_discount`
- `test_merchant_applies_upfront_discount`
- `test_merchant_escalates_above_autonomous_limit` (Failure Case 3)
- `test_merchant_generates_valid_offer`

### Acceptance Criteria
- Merchant agent never proposes price below minimum_price
- Correct bulk discount tier applied for given quantity
- Human approval requested when total > autonomous_limit
- All offers validated by PolicyEngine before being sent to buyer

### Dependencies
- Phase 4 (policy engine), Phase 5 (buyer agent)

### Risks
- LLM ignoring minimum price in prompt → double-validated by PolicyEngine

---

## Phase 7 — Negotiation Engine

### Objective
Implement the negotiation state machine that manages the lifecycle of an AI-to-AI negotiation from discovery to agreement or rejection.

### Files Affected
```
backend/app/negotiation/engine.py         ← state machine
backend/app/negotiation/states.py         ← state enums
backend/app/negotiation/transitions.py    ← valid state transitions
backend/app/negotiation/session.py        ← NegotiationSession model
backend/app/schemas/negotiation.py
backend/app/services/negotiation_service.py
backend/app/api/negotiation.py
backend/tests/unit/test_negotiation_engine.py
backend/tests/integration/test_negotiation_flow.py
```

### State Machine

```
States:
  DISCOVER       - Buyer searching, no active negotiation
  REQUEST        - Buyer has submitted purchase request
  OFFER          - Merchant has made an offer
  COUNTER_OFFER  - Buyer or merchant has counteroffered
  ACCEPT         - One party accepted → triggers AgreementEngine
  REJECT         - One party rejected → terminal
  EXPIRE         - Time limit exceeded → terminal
  AGREEMENT_CREATED - Agreement generated → negotiation complete

Valid Transitions:
  DISCOVER → REQUEST
  REQUEST → OFFER
  REQUEST → REJECT
  OFFER → ACCEPT
  OFFER → COUNTER_OFFER
  OFFER → REJECT
  COUNTER_OFFER → ACCEPT
  COUNTER_OFFER → COUNTER_OFFER (max rounds limit)
  COUNTER_OFFER → REJECT
  ACCEPT → AGREEMENT_CREATED
  * → EXPIRE (timeout)
```

### APIs Required
- `POST /api/v1/negotiations` — start negotiation (internal, triggered by buyer agent)
- `GET /api/v1/negotiations/{id}` — get negotiation state
- `GET /api/v1/negotiations/{id}/messages` — get message history
- `POST /api/v1/negotiations/{id}/message` — submit message (agent or human)

### Implementation Tasks
1. Implement `NegotiationState` enum
2. Implement transition table with guards
3. Implement `NegotiationSession` with message tracking
4. Implement `NegotiationEngine.transition(session, new_state, payload)` with validation
5. Implement max_rounds guard (default: 10)
6. Implement timeout: negotiations expire after 30 minutes
7. Wire buyer and merchant agents into negotiation lifecycle
8. Store all messages with timestamps and agent attribution

### Tests
- `test_valid_transitions`
- `test_invalid_transitions_blocked`
- `test_max_rounds_terminates`
- `test_expired_negotiation_cannot_transition`
- `test_accept_triggers_agreement_creation`

### Acceptance Criteria
- Invalid state transitions raise `InvalidTransitionError`
- Negotiations expire after 30 minutes
- Max 10 rounds before auto-rejection
- Every message stored with agent_id, timestamp, content
- ACCEPT state immediately triggers AgreementEngine

### Dependencies
- Phase 5, Phase 6

### Risks
- Async race condition if both agents respond simultaneously → use DB locking / pessimistic lock on negotiation session

---

## Phase 8 — Agreement Engine

### Objective
Convert an accepted negotiation into a canonical, immutable Commercial Agreement that becomes the single source of truth for the transaction.

### Files Affected
```
backend/app/agreements/engine.py          ← AgreementEngine
backend/app/agreements/validator.py       ← agreement schema validation
backend/app/schemas/agreement.py          ← CommercialAgreement schema
backend/app/models/agreement.py           ← updated ORM model
backend/app/api/agreements.py             ← API routes
backend/tests/unit/test_agreement_engine.py
```

### Commercial Agreement Schema

```python
class CommercialAgreement(BaseModel):
    id: UUID
    merchant_id: UUID
    buyer_id: UUID
    negotiation_id: UUID
    product_id: UUID
    product_name: str
    quantity: int
    unit_price: Decimal       # exact negotiated price
    total_amount: Decimal     # unit_price * quantity (Decimal multiplication)
    currency: str             # "INR"
    delivery_days: int
    warranty_months: int
    payment_terms: str        # "upfront" | "net30" | "net60"
    payment_reference: str | None    # Razorpay order_id (set after auth)
    created_at: datetime
    expires_at: datetime      # agreement validity window (e.g., 24h)
    status: AgreementStatus
    policy_validation_result: PolicyResult | None  # set after validation

class AgreementStatus(str, Enum):
    PENDING_VALIDATION  = "PENDING_VALIDATION"
    VALIDATED           = "VALIDATED"        # policy passed
    VALIDATION_FAILED   = "VALIDATION_FAILED" # policy blocked
    PENDING_APPROVAL    = "PENDING_APPROVAL" # awaiting human
    APPROVED            = "APPROVED"         # human approved
    PAYMENT_INITIATED   = "PAYMENT_INITIATED"
    PAYMENT_CAPTURED    = "PAYMENT_CAPTURED"
    PAYMENT_FAILED      = "PAYMENT_FAILED"
    EXPIRED             = "EXPIRED"
    CANCELLED           = "CANCELLED"
```

### Immutability Guarantee
Once `status` transitions past `PENDING_VALIDATION`, the core financial fields (unit_price, quantity, total_amount) are LOCKED. Any attempt to modify them must raise an `AgreementImmutableError`.

### Implementation Tasks
1. Implement `AgreementEngine.create_from_negotiation(session)` method
2. Recalculate total_amount independently: `Decimal(unit_price) * Decimal(quantity)`
3. Set status = PENDING_VALIDATION
4. Trigger PolicyEngine.validate_agreement()
5. If PASS → status = VALIDATED
6. If FAIL → status = VALIDATION_FAILED, log reason
7. If REQUIRES_HUMAN_APPROVAL → status = PENDING_APPROVAL, create ApprovalRequest
8. Implement API routes for agreement retrieval
9. Implement agreement viewer for frontend

### Tests
- `test_agreement_created_from_negotiation`
- `test_total_recalculated_independently`
- `test_agreement_immutable_after_validation`
- `test_validation_fail_blocks_payment`
- `test_approval_required_creates_approval_request`

### Acceptance Criteria
- Agreement total always independently recalculated (never trusted from negotiation)
- Agreement cannot be modified after VALIDATED
- Validation failure produces human-readable reason
- Agreement ID is globally unique (UUID v4)

### Dependencies
- Phase 4 (policy engine), Phase 7 (negotiation engine)

### Risks
- Clock skew on expires_at → use UTC everywhere

---

## Phase 9 — Razorpay Integration

### Objective
Integrate Razorpay Test Mode to create orders and process payments. This is the critical payment path.

### Files Affected
```
backend/app/payments/razorpay_client.py   ← Razorpay SDK wrapper
backend/app/payments/payment_service.py   ← PaymentService
backend/app/payments/auth_layer.py        ← PaymentAuthorizationLayer
backend/app/schemas/payment.py            ← payment schemas
backend/app/api/payments.py               ← payment API routes
backend/tests/integration/test_payment_flow.py
```

### Razorpay APIs Used

#### Create Order
```
POST https://api.razorpay.com/v1/orders
Auth: Basic (key_id:key_secret)
Body: {
  "amount": 108200000,     # in paise (₹10,82,000 * 100)
  "currency": "INR",
  "receipt": "agreement_<uuid>",
  "notes": {
    "agreement_id": "<uuid>",
    "merchant_id": "<uuid>",
    "buyer_id": "<uuid>",
    "product": "Dell 24\" Monitor"
  }
}
Response: {
  "id": "order_<razorpay_id>",
  "entity": "order",
  "amount": 108200000,
  "currency": "INR",
  "status": "created",
  ...
}
```

#### Payment Verification (signature)
```
Payload: razorpay_order_id + "|" + razorpay_payment_id
Signature: HMAC-SHA256(payload, key_secret)
Compare: signature == razorpay_signature (from frontend)
```

### PaymentAuthorizationLayer Design

```python
class PaymentAuthorizationLayer:
    async def authorize(
        self,
        agreement: CommercialAgreement,
        merchant_policy: MerchantPolicySchema,
        buyer_policy: BuyerPolicySchema,
    ) -> PaymentAuthorizationResult:
        
        # Step 1: Re-validate agreement (defense in depth)
        policy_result = self.policy_engine.validate_agreement(
            agreement, merchant_policy, buyer_policy
        )
        if policy_result.decision == PolicyDecision.FAIL:
            return PaymentAuthorizationResult(
                authorized=False,
                reason=policy_result.blocking_reason
            )
        
        # Step 2: Check human approval if required
        if policy_result.decision == PolicyDecision.REQUIRES_HUMAN_APPROVAL:
            # Do not proceed to Razorpay — wait for human
            return PaymentAuthorizationResult(
                authorized=False,
                requires_human_approval=True,
                reason=f"Transaction exceeds autonomous limit"
            )
        
        # Step 3: Convert amount to paise (integer, Decimal)
        amount_paise = int(agreement.total_amount * 100)
        
        # Step 4: Create Razorpay Order
        razorpay_order = await self.razorpay_client.create_order(
            amount=amount_paise,
            currency=agreement.currency,
            receipt=f"agreement_{agreement.id}",
            notes={...}
        )
        
        # Step 5: Save razorpay_order_id to agreement
        await self.agreement_service.set_payment_reference(
            agreement.id, razorpay_order["id"]
        )
        
        return PaymentAuthorizationResult(
            authorized=True,
            razorpay_order_id=razorpay_order["id"],
            amount_paise=amount_paise
        )
```

### Failure: Payment Amount Mismatch (Failure Case 1)
```python
# In WebhookProcessor after payment.captured event:
captured_amount = event["payload"]["payment"]["entity"]["amount"]
expected_amount = int(agreement.total_amount * 100)
if captured_amount != expected_amount:
    # BLOCK — do not mark agreement as PAID
    audit_event(action="PAYMENT_AMOUNT_MISMATCH", ...)
    raise PaymentAmountMismatchError(
        f"Expected {expected_amount} paise, got {captured_amount}"
    )
```

### Implementation Tasks
1. Create `RazorpayClient` wrapper around `razorpay` Python SDK
2. Implement `create_order(amount, currency, receipt, notes)` 
3. Implement `verify_payment_signature(order_id, payment_id, signature)` using HMAC-SHA256
4. Implement `PaymentAuthorizationLayer` with defense-in-depth validation
5. Implement amount paise conversion (Decimal → int, exact)
6. Add API endpoints for payment initiation and verification
7. Add API endpoint to return Razorpay Key ID to frontend (never Key Secret)
8. Test with Razorpay Test Mode card: 4111 1111 1111 1111

### Tests
- `test_payment_amount_converts_correctly_to_paise`
- `test_payment_blocked_if_policy_fails` (Failure Case 1)
- `test_payment_amount_mismatch_blocked` (Failure Case 1)
- `test_human_approval_required_blocks_payment` (Failure Case 3)
- `test_razorpay_order_created_with_correct_amount`

### Acceptance Criteria
- Razorpay Key Secret NEVER returned to frontend
- Payment amount verified against agreement before Razorpay order creation
- Payment amount verified again on webhook (double validation)
- All amounts use paise (integer) with Decimal-safe conversion
- Failed payment leaves agreement in PAYMENT_FAILED state (not corrupted)

### Dependencies
- Phase 8 (agreement engine), Phase 4 (policy engine)
- Razorpay Test Mode account credentials

### Risks
- `amount_paise` must be integer — floating point rounding could cause ₹0.01 errors → use `int(Decimal(...) * 100)` always
- Razorpay API downtime during demo → prepare recorded demo fallback

---

## Phase 10 — Webhooks

### Objective
Implement idempotent, signature-verified webhook processing for all Razorpay events.

### Files Affected
```
backend/app/webhooks/processor.py        ← WebhookProcessor
backend/app/webhooks/handlers/
    payment_captured.py
    payment_failed.py
    order_paid.py
backend/app/models/webhook_event.py      ← idempotency table
backend/app/api/webhooks.py              ← webhook endpoint
backend/tests/integration/test_webhooks.py
```

### Webhook Endpoint Design

```python
@router.post("/api/v1/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    event_id = request.headers.get("X-Razorpay-Event-Id")
    
    # Step 1: Verify signature (BEFORE parsing body)
    if not verify_webhook_signature(raw_body, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")  # Failure Case 6
    
    # Step 2: Idempotency check
    if await is_event_already_processed(db, event_id):
        return {"status": "already_processed"}  # Failure Case 4
    
    # Step 3: Parse event
    event = json.loads(raw_body)
    
    # Step 4: Dispatch to handler
    await process_webhook_event(db, event)
    
    # Step 5: Mark event as processed
    await mark_event_processed(db, event_id)
    
    # Step 6: Return 200 immediately
    return {"status": "ok"}
```

### Webhook Signature Verification

```python
import hmac
import hashlib

def verify_webhook_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    """
    Razorpay webhook signature: HMAC-SHA256 of raw_body with webhook_secret
    CRITICAL: Use raw_body (bytes), never parsed JSON
    """
    expected = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

### Events to Handle

| Event | Handler | Action |
|-------|---------|--------|
| `payment.captured` | `handle_payment_captured` | Mark agreement PAID, emit audit |
| `payment.failed` | `handle_payment_failed` | Mark agreement PAYMENT_FAILED, emit audit |
| `order.paid` | `handle_order_paid` | Secondary confirmation |
| Unknown | `handle_unknown` | Log warning, return 200 |

### Implementation Tasks
1. Implement signature verification (raw body, HMAC-SHA256)
2. Implement idempotency: `WebhookEvent` table with `event_id` unique constraint
3. Implement event dispatch to handlers
4. Implement `payment.captured` handler with amount verification
5. Implement `payment.failed` handler
6. Always return 200 within 5 seconds (async processing)
7. Handle out-of-order events (e.g., payment.captured without order in DB)

### Tests
- `test_valid_signature_processes_event` 
- `test_invalid_signature_rejected` (Failure Case 6)
- `test_duplicate_event_skipped` (Failure Case 4)
- `test_payment_captured_updates_agreement`
- `test_payment_failed_sets_correct_status` (Failure Case 5)
- `test_unknown_event_returns_200`
- `test_out_of_order_event_handled`

### Acceptance Criteria
- Invalid signature → 400, no processing, audit event
- Duplicate event → 200, no duplicate processing
- Payment amount verified on webhook (second check)
- Agreement never marked PAID if amount doesn't match
- All webhook events logged to webhook_events table

### Dependencies
- Phase 9 (payment service)

### Risks
- ngrok required for local webhook testing → document setup

---

## Phase 11 — Audit Trail

### Objective
Implement the immutable, structured audit trail that records every agent decision, policy check, and financial action.

### Files Affected
```
backend/app/audit/trail.py          ← AuditTrail service
backend/app/audit/events.py         ← event type definitions
backend/app/schemas/audit.py        ← AuditEvent schema
backend/app/api/audit.py            ← audit API routes
backend/tests/unit/test_audit.py
```

### Audit Event Schema

```python
class AuditEvent(BaseModel):
    id: UUID
    timestamp: datetime              # UTC, immutable
    session_id: UUID | None          # negotiation session
    agreement_id: UUID | None
    agent_id: str                    # "buyer_agent" | "merchant_agent" | "system"
    agent_type: AgentType
    action: AuditAction
    input_summary: str               # brief description of input
    decision: str                    # PASS | FAIL | BLOCKED | etc.
    policy_checked: str | None       # which rule was checked
    policy_result: str | None        # PASS | FAIL | REQUIRES_HUMAN_APPROVAL
    razorpay_reference: str | None   # razorpay order/payment id
    result: str                      # human-readable outcome
    failure_reason: str | None       # if failed

class AuditAction(str, Enum):
    NEGOTIATION_STARTED = "NEGOTIATION_STARTED"
    OFFER_GENERATED = "OFFER_GENERATED"
    COUNTEROFFER_SUBMITTED = "COUNTEROFFER_SUBMITTED"
    OFFER_ACCEPTED = "OFFER_ACCEPTED"
    OFFER_REJECTED = "OFFER_REJECTED"
    AGREEMENT_CREATED = "AGREEMENT_CREATED"
    POLICY_VALIDATED = "POLICY_VALIDATED"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    PAYMENT_AUTHORIZED = "PAYMENT_AUTHORIZED"
    PAYMENT_BLOCKED = "PAYMENT_BLOCKED"
    PAYMENT_CAPTURED = "PAYMENT_CAPTURED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_AMOUNT_MISMATCH = "PAYMENT_AMOUNT_MISMATCH"
    HUMAN_APPROVAL_REQUESTED = "HUMAN_APPROVAL_REQUESTED"
    HUMAN_APPROVED = "HUMAN_APPROVED"
    HUMAN_REJECTED = "HUMAN_REJECTED"
    WEBHOOK_RECEIVED = "WEBHOOK_RECEIVED"
    WEBHOOK_DUPLICATE = "WEBHOOK_DUPLICATE"
    WEBHOOK_INVALID_SIGNATURE = "WEBHOOK_INVALID_SIGNATURE"
    INVALID_TOOL_ARGS = "INVALID_TOOL_ARGS"
```

### Implementation Tasks
1. Implement `AuditTrail.record(event: AuditEvent)` — append-only
2. Make audit_events table append-only at DB level (no UPDATE/DELETE triggers)
3. Implement API: `GET /api/v1/audit?agreement_id=&session_id=&limit=50`
4. Implement audit event emission at every financial decision point
5. Ensure LLM chain-of-thought is NOT stored (only structured decisions)

### Acceptance Criteria
- Every financial action produces an audit event
- All 7 failure cases produce audit events with failure_reason
- Audit log is never modified after write
- Audit events visible in merchant dashboard

### Dependencies
- Phases 4–10 (each phase emits audit events)

---

## Phase 12 — Human Approval System

### Objective
Implement the human-in-the-loop approval system for transactions exceeding the merchant's autonomous limit.

### Files Affected
```
backend/app/models/approval.py          ← ApprovalRequest model
backend/app/services/approval_service.py
backend/app/api/approvals.py            ← API routes
frontend/src/features/approvals/        ← approval UI
```

### APIs Required
- `GET /api/v1/approvals` — list pending approvals
- `POST /api/v1/approvals/{id}/approve` — merchant approves
- `POST /api/v1/approvals/{id}/reject` — merchant rejects

### Implementation Tasks
1. Implement `ApprovalRequest` model with status (PENDING | APPROVED | REJECTED | EXPIRED)
2. Implement `ApprovalService.create_request(agreement_id, reason)`
3. Implement approval/rejection handlers (trigger payment authorization on approval)
4. Implement 24-hour auto-expiry for pending approvals
5. Implement frontend approval panel with notification badge

### Acceptance Criteria
- Transactions above ₹10L pause and await human approval
- Merchant dashboard shows all pending approvals
- Approved → payment proceeds immediately
- Rejected → agreement cancelled, audit event logged
- Expired → agreement cancelled after 24 hours

### Dependencies
- Phase 8 (agreement engine), Phase 9 (payment service)

---

## Phase 13 — Frontend

### Objective
Build the React/TypeScript/Vite frontend with two primary views: Buyer Chat Interface and Merchant Dashboard.

### Files Affected
```
frontend/src/
  App.tsx
  main.tsx
  index.css                          ← design system
  components/
    Layout.tsx
    Sidebar.tsx
    Badge.tsx
    StatusPill.tsx
    Spinner.tsx
    AuditEventRow.tsx
    NegotiationMessage.tsx
  pages/
    BuyerPage.tsx
    MerchantDashboard.tsx
    AgreementDetail.tsx
    AuditLog.tsx
    ApprovalsPage.tsx
  features/
    buyer/BuyerChat.tsx              ← conversational UI
    merchant/PolicyConfig.tsx
    merchant/NegotiationList.tsx
    merchant/RevenueStats.tsx
    negotiation/NegotiationTimeline.tsx
    agreements/AgreementCard.tsx
    payments/PaymentStatus.tsx
    approvals/ApprovalCard.tsx
    audit/AuditEventList.tsx
  api/
    client.ts                        ← typed API client
    buyer.ts
    merchant.ts
    negotiations.ts
    agreements.ts
    payments.ts
    audit.ts
  hooks/
    useNegotiationPolling.ts
    useAuditEvents.ts
  types/
    index.ts                         ← shared TypeScript types
```

### Design System
- Dark mode, glassmorphism panels
- Primary: electric blue `#3B82F6`, accent: indigo gradient
- Monospace font for prices and agreement fields
- Real-time negotiation message feed (polling every 2s)
- Status pills: colored by state (green=PAID, yellow=PENDING, red=FAILED/BLOCKED)

### Key Pages
1. **Buyer Chat** — Natural language input → real-time negotiation timeline
2. **Merchant Dashboard** — Stats + active negotiations + pending approvals + audit log
3. **Agreement Detail** — Full commercial agreement view with policy result
4. **Audit Log** — Filterable event table

### Razorpay Frontend Integration
- Load Razorpay Checkout script
- Create order via backend, get `razorpay_order_id`
- Launch checkout with key_id + order_id (never key_secret)
- On payment success: send `razorpay_payment_id` + `razorpay_signature` to backend for verification

### Implementation Tasks
1. Initialize Vite + React + TypeScript project
2. Create design system in `index.css`
3. Build Buyer Chat with message bubbles, agent attribution, policy check indicators
4. Build Merchant Dashboard with real-time negotiation list
5. Build Agreement Detail page
6. Build Approval Panel
7. Build Audit Log viewer
8. Implement Razorpay Checkout flow

### Dependencies
- Phases 5–12 (all backend features)

---

## Phase 14 — Failure Testing

### Objective
Explicitly implement, test, and document all 7 failure scenarios. These must be demonstrable in the 5-minute demo.

### Failure Scenarios

| # | Scenario | Trigger | Expected |
|---|----------|---------|----------|
| F1 | Payment amount mismatch | Tamper payment amount in webhook | BLOCK, audit event |
| F2 | Price below merchant minimum | Buyer requests below floor | PolicyEngine FAIL |
| F3 | Exceeds autonomous limit | Transaction > ₹10L | REQUIRES_HUMAN_APPROVAL |
| F4 | Duplicate webhook | Replay same X-Razorpay-Event-Id | Silently skip, 200 |
| F5 | Payment failure | Razorpay payment.failed event | PAYMENT_FAILED state |
| F6 | Invalid webhook signature | Wrong/missing signature | 400 REJECTED |
| F7 | Invalid tool args | LLM produces malformed tool call | Schema validation error, retry |

### Files Affected
```
backend/tests/integration/test_failure_scenarios.py
scripts/simulate_failures.py    ← demo helper scripts
docs/FAILURE_HANDLING.md        ← complete documentation
```

### Implementation Tasks
1. Write integration tests for all 7 failure cases
2. Implement `scripts/simulate_failures.py` with test helpers:
   - `simulate_tampered_webhook(amount)`
   - `simulate_invalid_signature()`
   - `simulate_duplicate_event(event_id)`
3. Verify each failure produces the correct audit event
4. Document demo steps for each failure case

### Acceptance Criteria
- All 7 failure tests pass
- Each failure produces a structured audit event
- No failure crashes the system (graceful handling only)
- Demo script can trigger each failure on demand

---

## Phase 15 — Deployment

### Objective
Package NEXORA for reliable demo deployment.

### Files Affected
```
docker-compose.yml
backend/Dockerfile
frontend/Dockerfile
.env.example
scripts/demo_setup.sh
scripts/demo_reset.sh
README.md
```

### Implementation Tasks
1. Finalize docker-compose.yml with all services
2. Add database volume persistence
3. Create `scripts/demo_reset.sh` to reset state between demos
4. Create `scripts/demo_setup.sh` to seed fresh demo data
5. Configure ngrok for webhook testing (or Razorpay dashboard override URL)
6. Write deployment README section
7. Test full demo flow end-to-end in Docker

### Acceptance Criteria
- `docker-compose up` brings up full system
- Demo reset script works
- End-to-end flow completes in < 5 minutes
- All 7 failure scenarios demonstrable without code changes

---

## Phase 16 — Demo Preparation

### Objective
Script and rehearse the 5-minute demo. Create pitch video. Finalize documentation.

### Deliverables
- 5-minute screen recording (demo video)
- Public GitHub repository (clean, well-documented)
- `docs/DEMO_SCENARIO.md` (step-by-step demo script)
- Architecture diagram (visual)
- README with quick-start instructions

### Demo Structure (5 minutes)
1. **0:00–0:30** — Problem statement: "In an agentic future, who negotiates the deal?"
2. **0:30–1:30** — Happy path: Buyer says "Buy 100 monitors under ₹11L" → full flow to PAID
3. **1:30–2:30** — Policy engine failure: Buyer tries ₹9,000/unit → BLOCKED
4. **2:30–3:30** — Human approval: ₹15L transaction → escalation → merchant approves
5. **3:30–4:30** — Webhook failures: invalid signature rejected, duplicate skipped
6. **4:30–5:00** — Architecture summary: "LLMs propose, deterministic systems decide"

---

## MVP Timeline

| Week | Dates | Phases |
|------|-------|--------|
| Week 1 | Aug 22–28 | 0 (complete), 1, 2, 3 |
| Week 2 | Aug 29–Sep 1 | 4, 5, 6, 7, 8 |
| Week 3 | Sep 2–4 | 9, 10, 11, 12, 13 |
| Final Day | Sep 5 | 14, 15, 16 |

---

## Engineering Rules (Enforced Throughout)

1. Use `Decimal` not `float` for all monetary values
2. All LLM tool outputs validated against Pydantic schemas before execution
3. Policy engine has zero LLM dependencies
4. Payment authorization always runs policy engine — no bypass
5. Webhook signature verified before parsing body
6. `X-Razorpay-Event-Id` checked for all events
7. No secrets in source code — `.env` only
8. Frontend never makes direct Razorpay API calls with key_secret
9. Frontend payment state never trusted — always verify via webhook/API
10. Every financial action produces an audit event
