"""
NEXORA Backend — Application Configuration
Uses Pydantic Settings for environment variable loading.
All secrets must be provided via .env file — never hardcoded.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import list


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ───────────────────────────────────────────────
    APP_NAME: str = "NEXORA"
    ENVIRONMENT: str = "development"  # development | production
    DEBUG: bool = False

    # ── Database ──────────────────────────────────────────────────
    DATABASE_URL: str  # e.g. postgresql+asyncpg://user:pass@localhost:5432/nexora
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # ── Razorpay ──────────────────────────────────────────────────
    # IMPORTANT: KEY_ID and WEBHOOK_SECRET are different credentials
    RAZORPAY_KEY_ID: str          # rzp_test_xxxx (safe to send to frontend)
    RAZORPAY_KEY_SECRET: str      # NEVER send to frontend
    RAZORPAY_WEBHOOK_SECRET: str  # Configure in Razorpay Dashboard → Settings → Webhooks
    RAZORPAY_TEST_MODE: bool = True

    # ── LLM ───────────────────────────────────────────────────────
    LLM_PROVIDER: str = "openai"  # openai | anthropic
    LLM_MODEL: str = "gpt-4o"
    LLM_API_KEY: str

    # ── Agent Defaults ────────────────────────────────────────────
    MAX_NEGOTIATION_ROUNDS: int = 10
    NEGOTIATION_TIMEOUT_MINUTES: int = 30
    MAX_TOOL_RETRIES: int = 3
    DEFAULT_AUTONOMOUS_LIMIT: float = 1_000_000.00  # ₹10,00,000

    # ── CORS ──────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ── Demo Mode ─────────────────────────────────────────────────
    # Set DEMO_MODE=cached to use pre-recorded agent responses (demo fallback)
    DEMO_MODE: str = "live"  # live | cached


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
