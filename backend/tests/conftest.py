"""
NEXORA Test Configuration — conftest.py

Shared fixtures available to ALL tests (unit + integration).

Key fixtures:
  - `override_settings`: injects test-safe environment variables
  - `client`: async HTTPX test client for FastAPI
  - `test_app`: the FastAPI app with test settings applied

Database fixtures (integration tests only) are in:
    tests/integration/conftest.py
"""
from __future__ import annotations

import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# ── Set test environment BEFORE importing app modules ─────────────────────────
# Force ENVIRONMENT=test FIRST, before loading .env, so it cannot be overridden
os.environ["ENVIRONMENT"] = "test"

from dotenv import load_dotenv
# Load real .env from root so we get the Neon DB URL (since we don't have local Postgres)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), "../.env"))

# This ensures settings are loaded with test values, not real credentials.
# Note: setdefault does NOT overwrite keys already set above (ENVIRONMENT)
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("RAZORPAY_KEY_ID", "rzp_test_PLACEHOLDER")
os.environ.setdefault("RAZORPAY_KEY_SECRET", "test_secret_PLACEHOLDER")
os.environ.setdefault("RAZORPAY_WEBHOOK_SECRET", "test_webhook_secret_PLACEHOLDER")
os.environ.setdefault("LLM_API_KEY", "test_llm_key_PLACEHOLDER")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("LOG_LEVEL", "WARNING")  # Keep test output clean


@pytest.fixture(scope="session")
def app():
    """
    Create a single FastAPI app instance for the entire test session.
    Uses the lru_cache-busted settings loaded from os.environ above.
    """
    # Clear any cached settings so test env vars take effect
    from app.config import get_settings
    get_settings.cache_clear()

    from app.main import create_app
    return create_app()


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client that talks to the test FastAPI app in-process.
    No real HTTP port is opened.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac


@pytest_asyncio.fixture(scope="session", autouse=True)
async def cleanup_database_pool():
    """
    Gracefully dispose the global database engine pool at the end of the test session.
    This prevents 'RuntimeError: Event loop is closed' caused by asyncpg 
    trying to clean up connections after the pytest event loop is shut down.
    """
    yield
    from app.database.connection import engine
    await engine.dispose()


@pytest.fixture(scope="session")
def event_loop():
    """
    Force pytest-asyncio to use a single event loop for the entire test session.
    Because our database engine (pool) is created globally, if the event loop
    closes between tests, asyncpg background tasks will crash.
    """
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
