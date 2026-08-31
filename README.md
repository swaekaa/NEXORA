<div align="center">
  <img src="frontend/public/favicon.svg" width="100" />
  <h1>NEXORA</h1>
  <p><em>The Agreement Layer for AI Commerce</em></p>

  [![Razorpay AI Buildathon 2026](https://img.shields.io/badge/Razorpay-AI%20Buildathon%202026-blue)](https://razorpay.com/buildathon/)
  [![Track](https://img.shields.io/badge/Track-AI%20Growth%20%26%20Agentic%20Commerce-green)]()
  [![Phase](https://img.shields.io/badge/Phase-Deployed-brightgreen)]()
  [![Python](https://img.shields.io/badge/Python-3.11%2B-blue)]()
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688)]()
</div>

---

## 🎥 See it in Action
### [▶️ Watch the Full Nexora Demo Video](frontend/public/demo.mp4)

---

## What Is NEXORA?

NEXORA is the missing infrastructure layer for autonomous AI commerce. It enables AI buyer agents and AI merchant agents to **negotiate**, **agree**, and **pay** — entirely autonomously — within strict, deterministic economic policies.

### The Foundational Principle

> **"LLMs propose. Deterministic systems decide."**

NEXORA is **not** "LLM calls payment API."  
NEXORA **is** "LLM-powered agents operating inside deterministic economic policy boundaries."

---

## ✨ Visual Walkthrough

### 1. Multi-Round Autonomous Negotiation
![Timeline](frontend/public/timeline.gif)
Watch AI agents negotiate in real-time, executing multi-round haggling over price, quantity, delivery days, and warranty. The negotiation engine guarantees structured output and bounded constraints.

### 2. Immutable Commercial Agreements
![Agreements](frontend/public/agreements.gif)
Once consensus is reached, it is locked into an immutable Agreement object. If it violates the Merchant's strict policy floor, it requires human approval. Otherwise, it executes instantly.

### 3. Cryptographic Audit Trails
![Audit Trail](frontend/public/audit_trial.gif)
Every single token, state transition, and signature is cryptographically verified and recorded. You have full visibility into the AI's "thought process" and commercial execution.

---

## 🤖 Meet the Agents

NEXORA is powered by an ecosystem of intelligent, specialized agents:

<div align="center">

| <img src="frontend/public/jake.png" width="150"/> | <img src="frontend/public/holt.png" width="150"/> | <img src="frontend/public/policy_core.png" width="150"/> |
|:---:|:---:|:---:|
| **JAKE** | **HOLT** | **POLICY CORE** |
| *Buyer Agent* | *Merchant Agent* | *Verification Engine* |
| Optimized for Procurement | Veteran B2B Sales | Immutable State Enforcement |
| Goal: Minimize Unit Price | Goal: Maximize Profit Margin | Goal: Validate Bounds |
| Architecture: **LLM** | Architecture: **LLM** | Architecture: **Deterministic Code** |

</div>

### The Policy Core Dashboard
![Policy Page](frontend/public/policy_page.png)
The heart of NEXORA. The deterministic engine has a fully-fledged dashboard proving its active parameters, execution limits, and raw JSON configuration dump.

---

## Problem Statement

In an agentic future, AI systems will negotiate and execute commercial transactions autonomously. Today's payment infrastructure has no answer for:

- How does an AI buyer negotiate with an AI seller?
- How does a merchant define what its AI agent is allowed to agree to?
- How do we prevent an LLM from hallucinating financial terms?
- How do we verify that the final payment matches what was agreed?
- How do we audit every agent decision?

**NEXORA answers all of these.**

---

## The Core Flow

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

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.11+ · FastAPI · uvicorn |
| **Config** | Pydantic Settings |
| **Database** | PostgreSQL 15 · SQLAlchemy 2 (async) · Alembic |
| **Payments** | Razorpay Test Mode (Orders API + Webhooks) |
| **AI Agents** | LangGraph · OpenAI/Anthropic Structured Output |
| **Frontend** | React · TypeScript · Vite · TailwindCSS · PixiJS |
| **Dev Tooling** | Docker · Docker Compose · pytest |

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

### Option B — Local Development (Backend + Frontend)

**1. Start the Database**
```bash
docker compose up db -d
```

**2. Start the Backend**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements-dev.txt

# Configure env
cp ../.env.example ../.env
# Update DATABASE_URL to use localhost:5432
# Provide your GEMINI_API_KEY for the LangGraph models

# Run migrations and seed data
alembic upgrade head
python seed.py

# Start server
uvicorn app.main:app --reload
```

**3. Start the Frontend**
Open a new terminal window:
```bash
cd frontend
npm install
npm run dev
```
Visit `http://localhost:5173` to view the dashboards!

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe — returns immediately |
| `GET` | `/health/ready` | Readiness probe — verifies DB connection |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc UI |
| `GET` | `/openapi.json` | OpenAPI schema |

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

---

## Buildathon Context

- **Event:** Razorpay AI Buildathon 2026
- **Track:** AI Growth & Agentic Commerce
- **Deadline:** September 5, 2026
- **Deliverable:** Working prototype + 5-minute pitch video + architecture docs

---

## License

MIT
