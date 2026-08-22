# NEXORA — Planning Complete: Architecture Summary

**Date:** August 22, 2026  
**Status:** Phase 0 Complete — Ready for Implementation

---

## ✅ Files Created

### Root
- [README.md](file:///C:/Users/Ekaansh/OneDrive/Desktop/AB/projects/NEXORA/README.md)
- [.env.example](file:///C:/Users/Ekaansh/OneDrive/Desktop/AB/projects/NEXORA/.env.example)
- [.gitignore](file:///C:/Users/Ekaansh/OneDrive/Desktop/AB/projects/NEXORA/.gitignore)
- [docker-compose.yml](file:///C:/Users/Ekaansh/OneDrive/Desktop/AB/projects/NEXORA/docker-compose.yml)

### Documentation (15 files)
| File | Purpose |
|------|---------|
| [PRD.md](file:///C:/Users/Ekaansh/OneDrive/Desktop/AB/projects/NEXORA/docs/PRD.md) | Product requirements |
| [ARCHITECTURE.md](file:///C:/Users/Ekaansh/OneDrive/Desktop/AB/projects/NEXORA/docs/ARCHITECTURE.md) | System design + component map |
| [IMPLEMENTATION_PLAN.md](file:///C:/Users/Ekaansh/OneDrive/Desktop/AB/projects/NEXORA/docs/IMPLEMENTATION_PLAN.md) | 16-phase plan with full spec per phase |
| [AGENT_PROTOCOL.md](file:///C:/Users/Ekaansh/OneDrive/Desktop/AB/projects/NEXORA/docs/AGENT_PROTOCOL.md) | All tool schemas + system prompts |
| [AGREEMENT_SPEC.md](file:///C:/Users/Ekaansh/OneDrive/Desktop/AB/projects/NEXORA/docs/AGREEMENT_SPEC.md) | Commercial agreement schema + lifecycle |
| [POLICY_ENGINE.md](file:///C:/Users/Ekaansh/OneDrive/Desktop/AB/projects/NEXORA/docs/POLICY_ENGINE.md) | Deterministic rule engine spec |
| [PAYMENT_FLOW.md](file:///C:/Users/Ekaansh/OneDrive/Desktop/AB/projects/NEXORA/docs/PAYMENT_FLOW.md) | Razorpay payment lifecycle |
| [WEBHOOK_STRATEGY.md](file:///C:/Users/Ekaansh/OneDrive/Desktop/AB/projects/NEXORA/docs/WEBHOOK_STRATEGY.md) | Idempotent webhook handling |
| [FAILURE_HANDLING.md](file:///C:/Users/Ekaansh/OneDrive/Desktop/AB/projects/NEXORA/docs/FAILURE_HANDLING.md) | All 7 failure scenarios with code |
| [DATABASE_SCHEMA.md](file:///C:/Users/Ekaansh/OneDrive/Desktop/AB/projects/NEXORA/docs/DATABASE_SCHEMA.md) | Complete SQL schema |
| [API_SPEC.md](file:///C:/Users/Ekaansh/OneDrive/Desktop/AB/projects/NEXORA/docs/API_SPEC.md) | REST API spec |
| [TESTING_STRATEGY.md](file:///C:/Users/Ekaansh/OneDrive/Desktop/AB/projects/NEXORA/docs/TESTING_STRATEGY.md) | Testing approach + test cases |
| [DEMO_SCENARIO.md](file:///C:/Users/Ekaansh/OneDrive/Desktop/AB/projects/NEXORA/docs/DEMO_SCENARIO.md) | 5-minute demo script |
| [SECURITY.md](file:///C:/Users/Ekaansh/OneDrive/Desktop/AB/projects/NEXORA/docs/SECURITY.md) | Security rules |
| [RAZORPAY_INTEGRATION_NOTES.md](file:///C:/Users/Ekaansh/OneDrive/Desktop/AB/projects/NEXORA/docs/RAZORPAY_INTEGRATION_NOTES.md) | Verified API notes + open questions |

### Backend Skeleton
- `backend/app/main.py` — FastAPI app skeleton
- `backend/app/config.py` — Pydantic Settings
- `backend/app/[all modules]/__init__.py` — package stubs
- `backend/requirements.txt` + `requirements-dev.txt`
- `backend/Dockerfile`

### Frontend Skeleton
- `frontend/package.json`
- `frontend/src/main.tsx`
- `frontend/src/types/index.ts` — complete TypeScript types

### Data + Scripts
- `data/seed/demo_merchant.json`
- `data/seed/demo_buyer.json`
- `scripts/demo_setup.py`
- `scripts/simulate_failures.py`

---

## Architecture Summary

### The Core Principle
```
LLMs propose. Deterministic systems decide.
```

### The Boundary (enforced in code)
```
─────────────────────────────────────────────────────────
AI LAYER (LLM)           │  DETERMINISTIC LAYER
─────────────────────────────────────────────────────────
✓ Understand intent      │  ✓ Calculate prices
✓ Generate proposals     │  ✓ Validate discounts
✓ Evaluate trade-offs    │  ✓ Verify agreement totals
✓ Request tool calls     │  ✓ Enforce spending limits
✓ Explain decisions      │  ✓ Call Razorpay
✗ Call Razorpay          │  ✗ Generate proposals
✗ Calculate financials   │  ✗ Understand language
─────────────────────────────────────────────────────────
```

### Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| PolicyEngine has zero LLM dependency | Financial rules must be unit-testable, deterministic |
| Webhook verified before body parsed | Defense against signature bypass attacks |
| `Decimal` not `float` everywhere | Paise-precision requirement; float arithmetic is unsafe |
| Agreement total independently recalculated | LLM cannot inject false totals into payment |
| `X-Razorpay-Event-Id` for idempotency | Razorpay retries; exactly-once semantics required |
| Human approval as a first-class state | Some transactions need merchant review |
| Audit trail is append-only | Immutable evidence of agent decisions |
| Monolith (not microservices) | Simpler, demonstrable, no network overhead for demo |
| Test Mode only | Cannot use real money in buildathon context |

---

## MVP Scope Summary

**What works end-to-end in the demo:**
1. Buyer types natural-language goal → AI buyer agent activates
2. AI buyer negotiates with AI merchant → 1-3 rounds
3. Negotiation reaches agreement → commercial agreement created
4. Policy engine validates → all 7+ checks run
5. Razorpay Order created → Checkout displayed
6. Test payment completed → webhook received + verified
7. Agreement marked PAID → audit trail complete
8. Merchant dashboard shows full history

**What is deliberately demonstrated as failures:**
1. Price below minimum → policy blocked
2. Exceeds autonomous limit → human approval required
3. Invalid webhook signature → 400 rejected
4. Duplicate webhook → silently skipped
5. Payment amount mismatch → blocked
6. Invalid LLM tool args → schema validation, retry

---

## Biggest Risks

| Risk | Mitigation |
|------|-----------|
| LLM slow/unavailable during demo | DEMO_MODE=cached uses pre-recorded responses |
| Webhook not arriving (ngrok) | `simulate_webhook.py` sends signed event locally |
| Float precision errors | All Decimal, all the time — enforced in code |
| Race condition on agreement mutation | DB-level locking + status transitions via service only |
| Razorpay API changes | All Razorpay behavior documented in RAZORPAY_INTEGRATION_NOTES.md |
| Time pressure (Sept 5) | Policy engine is Phase 4 — done early, tested thoroughly |

---

## Razorpay Dependencies

| Component | API | Status |
|-----------|-----|--------|
| Payment creation | Orders API `POST /v1/orders` | Confirmed, stable |
| Payment verification | HMAC-SHA256(`order_id|payment_id`, key_secret) | Confirmed |
| Webhook events | `payment.captured`, `payment.failed` | Confirmed |
| Webhook security | HMAC-SHA256(raw_body, webhook_secret) | Confirmed |
| Idempotency | `X-Razorpay-Event-Id` header | Confirmed |
| Test mode | Test cards, sandbox environment | Confirmed |

---

## Recommended Implementation Order

```
Week 1 (Aug 22–28):
  ✅ Phase 0 — Architecture (DONE)
  → Phase 1 — Repository + infrastructure (next)
  → Phase 2 — Database schema + models
  → Phase 3 — Merchant catalog API

Week 2 (Aug 29–Sep 1):
  → Phase 4 — Policy engine (HIGHEST PRIORITY — test everything)
  → Phase 5 — Buyer agent
  → Phase 6 — Merchant agent
  → Phase 7 — Negotiation engine
  → Phase 8 — Agreement engine

Week 3 (Sep 2–4):
  → Phase 9  — Razorpay integration
  → Phase 10 — Webhooks
  → Phase 11 — Audit trail
  → Phase 12 — Human approvals
  → Phase 13 — Frontend

Final Day (Sep 5):
  → Phase 14 — Failure testing
  → Phase 15 — Deployment
  → Phase 16 — Demo preparation
```

---

## First Concrete Coding Task

**START HERE: Phase 1 — Repository + Infrastructure**

1. Set up FastAPI with health endpoint
2. Configure Pydantic Settings from `.env`
3. Create Alembic migration setup
4. Verify `GET /health` returns 200
5. Verify CORS works from frontend origin

Then immediately move to **Phase 4 — Policy Engine**, because:
- It has zero external dependencies
- It can be built and tested before the database
- Having it solid early de-risks the entire financial layer
- 40+ unit tests give you confidence throughout the rest of the build

```python
# The first real test you should write:
def test_policy_engine_blocks_price_below_minimum():
    engine = PolicyEngine()
    result = engine.check_min_price(
        unit_price=Decimal("9500.00"),
        min_price=Decimal("10500.00")
    )
    assert not result.passed
    assert "9500" in result.reason
    assert "10500" in result.reason
```

If this test passes cleanly, NEXORA has its financial safety foundation.
