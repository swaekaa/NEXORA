"""
NEXORA Backend — Application Configuration

All settings are loaded from environment variables (or a .env file).
No secrets are hardcoded here. See .env.example for required keys.

Usage:
    from app.config import settings
    print(settings.APP_NAME)
"""
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Look for .env in current dir (backend) and parent dir (NEXORA root)
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Extra fields in .env are ignored, not an error
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    APP_NAME: str = "NEXORA"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "production", "test"] = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ── Database ──────────────────────────────────────────────────────────────
    # Full async DSN: postgresql+asyncpg://user:password@host:port/dbname
    DATABASE_URL: str = "postgresql+asyncpg://nexora:nexora_password@localhost:5432/nexora"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_ECHO: bool = False  # Set True for SQL query logging (noisy)

    # ── Razorpay ──────────────────────────────────────────────────────────────
    # These are optional at Phase 1 (Razorpay integration is Phase 9).
    # Required fields are enforced when those modules are initialised.
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # ── LLM (Phase 5+) ────────────────────────────────────────────────────────
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_DEPLOYMENT_NAME: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "*",
    ]

    # ── Agent Behaviour (Phase 5+) ────────────────────────────────────────────
    MAX_NEGOTIATION_ROUNDS: int = 10
    NEGOTIATION_TIMEOUT_MINUTES: int = 30
    MAX_TOOL_RETRIES: int = 3
    NEGOTIATION_DEMO_MIN_ROUNDS: int = 3  # Force minimum 3 rounds for realism in demo


    # ── Inventory (Phase 8) ───────────────────────────────────────────────────
    INVENTORY_RESERVATION_TTL_MINUTES: int = 15

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}, got {v!r}")
        return upper

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_test(self) -> bool:
        return self.ENVIRONMENT == "test"


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached Settings instance.
    Use get_settings() for dependency injection in FastAPI routes.
    The module-level `settings` singleton is available for non-DI usage.
    """
    return Settings()


# Module-level singleton — use this for imports outside of DI context
settings: Settings = get_settings()
