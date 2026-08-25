# NEXORA — The Agreement Layer for AI Commerce

> *"The agreement layer for AI commerce."*

[![Razorpay AI Buildathon 2026](https://img.shields.io/badge/Razorpay-AI%20Buildathon%202026-blue)](https://razorpay.com/buildathon/)
[![Track](https://img.shields.io/badge/Track-AI%20Growth%20%26%20Agentic%20Commerce-green)]()
[![Phase](https://img.shields.io/badge/Phase-1%20Complete-brightgreen)]()
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688)]()

---

## What Is NEXORA?

NEXORA is the missing infrastructure layer for autonomous AI commerce. It enables AI buyer agents and AI merchant agents to **negotiate**, **agree**, and **pay** — entirely autonomously — within strict, deterministic economic policies.

### The Core Flow

```
AI Buyer Agent
      ↓
AI-to-AI Negotiation   ← LLM-powered, policy-bounded
      ↓
Commercial Agreement   ← structured, canonical, immutable
      ↓
Policy Engine          ← 100% deterministic, no LLM
      ↓
Payment Authorization
      ↓
Razorpay (Test Mode)
      ↓
Webhook Verification   ← HMAC-SHA256, idempotent
      ↓
Settlement + Audit Trail
```

### The Foundational Principle

```
LLMs propose.  Deterministic systems decide.
```

NEXORA is **not** "LLM calls payment API."  
NEXORA **is** "LLM-powered agents operating inside deterministic economic policy boundaries."

---

## Problem Statement

In an agentic future, AI systems will negotiate and execute commercial transactions autonomously. Today's payment infrastructure has no answer for:

- How does an AI buyer negotiate with an AI seller?
- How does a merchant define what its AI agent is allowed to agree to?
- How do we prevent an LLM from hallucinating financial terms?
- How do we verify that the final payment matches what was agreed?
- How do we audit every agent decision?

NEXORA answers all of these.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.11+ · FastAPI · uvicorn |
| **Config** | Pydantic Settings |
| **Database** | PostgreSQL 15 · SQLAlchemy 2 (async) · Alembic |
| **Payments** | Razorpay Test Mode (Orders API + Webhooks) |
| **AI Agents** | LLM with structured tool calling (Phase 5+) |
| **Frontend** | React · TypeScript · Vite (Phase 13) |
| **Dev Tooling** | Docker · Docker Compose · pytest |

---

## Implementation Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 0 | Architecture & Planning | ✅ Complete |
| Phase 1 | Repository + Infrastructure | ✅ Complete |
| Phase 2 | Database Schema + Models | ✅ Complete |
| Phase 3 | Merchant Catalog API | ✅ Complete |
| Phase 4 | Policy Engine | ✅ Complete |
| Phase 5 | Buyer Agent | ✅ Complete |
| Phase 6 | Merchant Agent | 🔜 Next |
| Phase 7 | Negotiation Engine | ⬜ Pending |
| Phase 8 | Agreement Engine | ⬜ Pending |
| Phase 9 | Razorpay Integration | ⬜ Pending |
| Phase 10 | Webhooks | ⬜ Pending |
| Phase 11 | Audit Trail | ⬜ Pending |
| Phase 12 | Human Approvals | ⬜ Pending |
| Phase 13 | Frontend | ⬜ Pending |
| Phase 14 | Failure Testing | ⬜ Pending |
| Phase 15 | Deployment | ⬜ Pending |
| Phase 16 | Demo Preparation | ⬜ Pending |

---

## Quick Start

### Option A — Docker (recommended)

```bash
git clone https://github.com/swaekaa/NEXORA.git
cd NEXORA

cp .env.example .env
# Edit .env if needed (defaults work for Docker)

docker compose up --build
```

**Verify:**
```bash
curl http://localhost:8000/health
# {"status":"ok","service":"nexora-api","version":"0.1.0",...}
```

### Option B — Local Development

```bash
# Start PostgreSQL only
docker compose up db -d

cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements-dev.txt

# Configure env
cp ../.env.example ../.env
# Update DATABASE_URL to use localhost:5432

# Run migrations (creates alembic tracking table)
alembic upgrade head

# Start server with hot-reload
uvicorn app.main:app --reload
```

---

## API Endpoints (Phase 1)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe — returns immediately |
| `GET` | `/health/ready` | Readiness probe — verifies DB connection |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc UI |
| `GET` | `/openapi.json` | OpenAPI schema |

---

## Running Tests

```bash
cd backend

# All unit tests (no database required)
pytest tests/unit/ -v

# With coverage
pytest tests/unit/ --cov=app --cov-report=term-missing

# Full suite (requires DB)
pytest -v
```

---

## Environment Variables

Copy `.env.example` to `.env`. Required variables:

| Variable | Phase Required | Description |
|----------|---------------|-------------|
| `DATABASE_URL` | 1 | PostgreSQL async DSN |
| `RAZORPAY_KEY_ID` | 9 | Razorpay Test Mode Key ID |
| `RAZORPAY_KEY_SECRET` | 9 | Razorpay Key Secret (never send to frontend) |
| `RAZORPAY_WEBHOOK_SECRET` | 10 | Separate webhook signing secret |
| `LLM_API_KEY` | 5 | OpenAI / Anthropic API key |

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for full reference.

---

## Documentation

| Document | Description |
|----------|-------------|
| [DEVELOPMENT.md](docs/DEVELOPMENT.md) | Setup, testing, patterns, troubleshooting |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design + component map |
| [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) | 16-phase build plan |
| [AGENT_PROTOCOL.md](docs/AGENT_PROTOCOL.md) | AI agent tool schemas + system prompts |
| [AGREEMENT_SPEC.md](docs/AGREEMENT_SPEC.md) | Commercial agreement schema |
| [POLICY_ENGINE.md](docs/POLICY_ENGINE.md) | Deterministic rule engine spec |
| [PAYMENT_FLOW.md](docs/PAYMENT_FLOW.md) | Razorpay payment lifecycle |
| [WEBHOOK_STRATEGY.md](docs/WEBHOOK_STRATEGY.md) | Idempotent webhook handling |
| [FAILURE_HANDLING.md](docs/FAILURE_HANDLING.md) | All 7 failure scenarios |
| [DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) | Complete SQL schema |
| [API_SPEC.md](docs/API_SPEC.md) | REST API reference |
| [TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) | Testing approach |
| [DEMO_SCENARIO.md](docs/DEMO_SCENARIO.md) | 5-minute demo script |
| [RAZORPAY_INTEGRATION_NOTES.md](docs/RAZORPAY_INTEGRATION_NOTES.md) | Verified Razorpay API notes |
| [SECURITY.md](docs/SECURITY.md) | Security rules |

---

## Buildathon Context

- **Event:** Razorpay AI Buildathon 2026
- **Track:** AI Growth & Agentic Commerce
- **Deadline:** September 5, 2026
- **Deliverable:** Working prototype + 5-minute pitch video + architecture docs

---

## License

MIT
