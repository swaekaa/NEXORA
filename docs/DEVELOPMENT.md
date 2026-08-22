# NEXORA — Developer Guide

**Phase 1 — Repository + Infrastructure**  
**Last updated:** August 23, 2026

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | `python --version` |
| Docker | 24+ | `docker --version` |
| Docker Compose | v2 | `docker compose version` |
| Git | any | — |

---

## Quick Start (Docker — Recommended)

```bash
# 1. Clone
git clone https://github.com/swaekaa/NEXORA.git
cd NEXORA

# 2. Configure environment
cp .env.example .env
# Edit .env — at minimum, DATABASE_URL is pre-filled for Docker use

# 3. Start database + backend
docker compose up --build

# 4. Verify
curl http://localhost:8000/health
# Expected: {"status": "ok", "service": "nexora-api", ...}
```

---

## Local Development (Without Docker)

### 1. Start PostgreSQL

```bash
# Start only the database container
docker compose up db -d

# Verify it's running
docker compose ps
```

### 2. Set Up Python Environment

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (macOS/Linux)
source .venv/bin/activate

# Install all dependencies (including dev tools)
pip install -r requirements-dev.txt
```

### 3. Configure Environment

```bash
# From the project root
cp .env.example .env
```

For local dev (backend on host, DB in Docker), `.env` should have:
```
DATABASE_URL=postgresql+asyncpg://nexora:nexora_password@localhost:5432/nexora
ENVIRONMENT=development
LOG_LEVEL=INFO
```

The other secrets (Razorpay, LLM) are only needed in later phases and can be left as placeholders.

### 4. Run Database Migrations

```bash
cd backend
alembic upgrade head
```

Phase 1 has no models yet, so this creates the `alembic_version` tracking table only.

### 5. Start the Backend

```bash
cd backend
uvicorn app.main:app --reload
```

The API is now at `http://localhost:8000`.

### 6. Verify

```bash
# Liveness
curl http://localhost:8000/health

# Readiness (checks DB connection)
curl http://localhost:8000/health/ready

# Interactive API docs
open http://localhost:8000/docs
```

---

## Running Tests

```bash
cd backend

# All tests (some integration tests need DB running)
pytest

# Unit tests only (no DB required)
pytest tests/unit/

# With coverage report
pytest tests/unit/ --cov=app --cov-report=term-missing

# A specific test file
pytest tests/unit/test_phase1.py -v

# A specific test class
pytest tests/unit/test_phase1.py::TestHealthLiveness -v
```

### What Phase 1 Tests Cover

| Test Class | Tests |
|------------|-------|
| `TestAppStartup` | App factory creates valid FastAPI instance, OpenAPI schema |
| `TestHealthLiveness` | GET /health — status, fields, request-id header |
| `TestHealthReadiness` | GET /health/ready — 200 or 503 (never crashes) |
| `TestOpenAPI` | /openapi.json, /docs, /redoc |
| `TestExceptionHandling` | NexoraError → structured JSON, 404 for unknown routes |
| `TestConfiguration` | Settings load correctly, types are valid |

---

## Project Structure

```
NEXORA/
├── backend/
│   ├── alembic/                ← Database migration scripts
│   │   ├── env.py              ← Migration environment (reads from settings)
│   │   ├── script.py.mako      ← Migration template
│   │   └── versions/           ← Migration files (added per phase)
│   ├── app/
│   │   ├── main.py             ← FastAPI app factory + middleware + handlers
│   │   ├── config.py           ← Pydantic Settings (all config here)
│   │   ├── logging_config.py   ← Structured logging setup
│   │   ├── exceptions.py       ← Domain exception hierarchy
│   │   ├── api/
│   │   │   └── health.py       ← /health + /health/ready endpoints
│   │   ├── database/
│   │   │   ├── base.py         ← SQLAlchemy Base + column helpers
│   │   │   └── connection.py   ← Engine, session factory, get_db dependency
│   │   ├── models/             ← ORM models (added Phase 2+)
│   │   ├── schemas/            ← Pydantic schemas (added Phase 2+)
│   │   ├── policies/           ← Policy engine (Phase 4)
│   │   ├── agents/             ← LLM agents (Phase 5-6)
│   │   ├── negotiation/        ← Negotiation state machine (Phase 7)
│   │   ├── agreements/         ← Agreement engine (Phase 8)
│   │   ├── payments/           ← Razorpay integration (Phase 9)
│   │   ├── webhooks/           ← Webhook processor (Phase 10)
│   │   ├── audit/              ← Audit trail (Phase 11)
│   │   └── services/           ← Business logic services
│   ├── tests/
│   │   ├── conftest.py         ← Shared fixtures (app, client)
│   │   ├── unit/               ← No external dependencies
│   │   │   └── test_phase1.py
│   │   └── integration/        ← Requires live DB
│   ├── alembic.ini             ← Alembic config (no credentials here)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── requirements-dev.txt
├── docs/                       ← Architecture and planning documents
├── .env.example                ← Template (copy to .env)
├── .gitignore
├── docker-compose.yml
└── README.md
```

---

## Adding a New API Route (Pattern)

```python
# backend/app/api/example.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db

router = APIRouter(tags=["example"])

@router.get("/example/{item_id}")
async def get_example(item_id: str, db: AsyncSession = Depends(get_db)):
    ...
```

```python
# backend/app/main.py — in _register_routers()
from app.api.example import router as example_router
app.include_router(example_router, prefix="/api/v1")
```

---

## Adding a Database Migration (Pattern)

```bash
# After adding/modifying a model in app/models/
cd backend

# Generate migration script
alembic revision --autogenerate -m "add_merchant_table"

# Review the generated file in alembic/versions/
# Then apply it
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

**Remember:** Import new models in `alembic/env.py` so autogenerate sees them.

---

## Environment Variables Reference

| Variable | Required | Default | Phase |
|----------|----------|---------|-------|
| `APP_NAME` | No | NEXORA | 1 |
| `APP_VERSION` | No | 0.1.0 | 1 |
| `ENVIRONMENT` | No | development | 1 |
| `DEBUG` | No | false | 1 |
| `LOG_LEVEL` | No | INFO | 1 |
| `DATABASE_URL` | **Yes** | (postgres DSN) | 1 |
| `DB_POOL_SIZE` | No | 10 | 1 |
| `DB_MAX_OVERFLOW` | No | 20 | 1 |
| `DB_ECHO` | No | false | 1 |
| `CORS_ORIGINS` | No | localhost:3000,5173 | 1 |
| `RAZORPAY_KEY_ID` | Phase 9 | — | 9 |
| `RAZORPAY_KEY_SECRET` | Phase 9 | — | 9 |
| `RAZORPAY_WEBHOOK_SECRET` | Phase 10 | — | 10 |
| `LLM_API_KEY` | Phase 5 | — | 5 |

---

## Common Issues

### `asyncpg` fails to import
```
ModuleNotFoundError: No module named 'asyncpg'
```
**Fix:** `pip install -r requirements.txt` (asyncpg requires C compilation — needs gcc)

### Database connection refused
```
sqlalchemy.exc.OperationalError: ... Connection refused
```
**Fix:** Ensure PostgreSQL is running — `docker compose up db -d`

### `alembic upgrade head` fails with "no module named psycopg2"
Alembic's offline mode uses psycopg2 DSN. For online mode (the default), asyncpg is used.
**Fix:** Install psycopg2-binary if you need offline mode: `pip install psycopg2-binary`

### Port 5432 already in use
**Fix:** Stop local PostgreSQL service or change the host port in `docker-compose.yml`.

---

## Code Style

- **Type hints:** All public functions must be type-annotated
- **Docstrings:** All modules and public classes/functions
- **Monetary values:** Always `Decimal`, never `float`
- **No business logic in route handlers** — routes call services, services do logic
- **No circular imports** — import order: config → exceptions → database → services → api
