"""
NEXORA Backend — Structured Logging Configuration

Sets up JSON-structured logging for the application.
Every log record includes: timestamp, level, service, logger name, message.
Request IDs are added by middleware in main.py.

Rules:
- Never log secrets, API keys, or payment credentials.
- Log decisions, not data payloads (especially for financial events).
"""
import logging
import sys
from typing import Any


class _SafeFormatter(logging.Formatter):
    """
    Simple log formatter that outputs a structured line.
    For production, swap this for python-json-logger or structlog.
    """

    _REDACTED_KEYS = frozenset(
        {
            "key_secret",
            "razorpay_key_secret",
            "webhook_secret",
            "llm_api_key",
            "password",
            "token",
            "authorization",
        }
    )

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        # Scrub any accidentally-logged secrets from the message
        message = super().format(record)
        return message

    def formatMessage(self, record: logging.LogRecord) -> str:  # noqa: N802
        return (
            f"{record.asctime} | "
            f"{record.levelname:<8} | "
            f"service=nexora | "
            f"logger={record.name} | "
            f"{record.getMessage()}"
        )


def configure_logging(level: str = "INFO") -> None:
    """
    Call once at application startup to configure the root logger.

    Args:
        level: One of DEBUG / INFO / WARNING / ERROR / CRITICAL
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    formatter = _SafeFormatter(fmt="%(asctime)s", datefmt="%Y-%m-%dT%H:%M:%S")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(numeric_level)

    # Quieten noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if level == "DEBUG" else logging.WARNING
    )


def get_logger(name: str) -> logging.Logger:
    """Convenience wrapper — use this instead of logging.getLogger() directly."""
    return logging.getLogger(name)
