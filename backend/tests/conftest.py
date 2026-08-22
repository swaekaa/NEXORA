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
# This ensures settings are loaded with test values, not real credentials.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://nexora:nexora_password@localhost:5432/nexora_test")
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
