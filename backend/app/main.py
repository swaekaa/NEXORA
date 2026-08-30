"""
NEXORA Backend — FastAPI Application

Application factory pattern: create_app() builds and configures the FastAPI
instance. The module-level `app` variable is what uvicorn runs.

Startup lifecycle:
  1. configure_logging()
  2. Database engine is already created at import (connection.py)
  3. Routers registered

Shutdown lifecycle:
  1. engine.dispose() — releases all DB pool connections
"""
from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager # Reloading for new API key
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.exceptions import NexoraError
from app.logging_config import configure_logging

logger = logging.getLogger(__name__)


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    """
    Manage application startup and shutdown.

    Startup:
        - Configure logging
        - Log configuration summary (without secrets)

    Shutdown:
        - Dispose database connection pool
    """
    # ── Startup ──────────────────────────────────────────────────────────────
    configure_logging(settings.LOG_LEVEL)

    logger.info(
        "NEXORA starting | service=nexora-api version=%s env=%s",
        settings.APP_VERSION,
        settings.ENVIRONMENT,
    )
    logger.info(
        "Database pool | size=%s max_overflow=%s",
        settings.DB_POOL_SIZE,
        settings.DB_MAX_OVERFLOW,
    )

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    from app.database.connection import engine

    await engine.dispose()
    logger.info("NEXORA shutdown complete — DB pool released")


# ── Application Factory ────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """
    Build and configure the FastAPI application.
    Returns a fully configured app instance.
    """
    app = FastAPI(
        title="NEXORA API",
        description=(
            "The agreement layer for AI commerce. "
            "Enables autonomous AI buyer and merchant agents to negotiate, "
            "agree, and pay — within strict deterministic economic policies."
        ),
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    _register_middleware(app)
    _register_exception_handlers(app)
    _register_routers(app)

    return app


# ── Middleware ─────────────────────────────────────────────────────────────────

def _register_middleware(app: FastAPI) -> None:
    """Register all middleware in the correct order (outermost first)."""

    # ── Request ID Middleware ─────────────────────────────────────────────────
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next: Any) -> Any:
        """
        Attach a unique request_id to every request.
        Logged with every log statement in the request context.
        """
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        request.state.start_time = time.monotonic()

        response = await call_next(request)

        duration_ms = (time.monotonic() - request.state.start_time) * 1000
        logger.info(
            "request | id=%s method=%s path=%s status=%s duration_ms=%.1f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        response.headers["X-Request-Id"] = request_id
        return response

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# ── Exception Handlers ─────────────────────────────────────────────────────────

def _register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers that convert exceptions to JSON responses."""

    @app.exception_handler(NexoraError)
    async def nexora_error_handler(request: Request, exc: NexoraError) -> JSONResponse:
        """
        Convert any NexoraError subclass to a structured JSON error response.
        The error code and HTTP status are derived from the exception class.
        """
        logger.warning(
            "domain error | code=%s message=%s path=%s",
            exc.code,
            exc.message,
            request.url.path,
        )
        return JSONResponse(
            status_code=exc.http_status,
            content=exc.to_dict(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Catch-all for unexpected exceptions.
        Logs the full traceback but returns a generic message to the client
        (never expose internal details in production).
        """
        logger.exception(
            "unhandled exception | path=%s | %s: %s",
            request.url.path,
            type(exc).__name__,
            exc,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again.",
            },
        )


# ── Routers ────────────────────────────────────────────────────────────────────

def _register_routers(app: FastAPI) -> None:
    """
    Register all API routers.

    Phase 1: /health only.
    Phase 3: Merchant Catalog (products + policies).
    Later phases add their routers here as they are implemented.
    """
    from app.api.health import router as health_router

    # Health endpoints (no /api/v1 prefix — these are infra-level)
    app.include_router(health_router)

    # ── Phase 3: Merchant Catalog ─────────────────────────────────────────────
    from app.api.catalog import router as catalog_router
    app.include_router(catalog_router, prefix="/api/v1")

    # ── Future routers (uncomment as phases are completed) ────────────────────
    # Phase 5:  from app.api.buyer import router as buyer_router
    #           app.include_router(buyer_router, prefix="/api/v1")
    # Phase 7:  
    from app.api.v1.endpoints import payments, webhooks, inventory, approvals, audit, buyers_agent, merchants_agent, negotiations, agreements
    
    app.include_router(payments.router, prefix="/api/v1")
    app.include_router(webhooks.router, prefix="/api/v1")
    app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["Inventory"])
    app.include_router(negotiations.router, prefix="/api/v1")
    app.include_router(agreements.router, prefix="/api/v1")
    
    # Phase 10: Buyer Agent API
    app.include_router(buyers_agent.router, prefix="/api/v1")
    
    # Phase 11: Merchant Agent API
    app.include_router(merchants_agent.router, prefix="/api/v1")
    
    # Phase 9: Approvals and Audit
    app.include_router(approvals.router, prefix="/api/v1/merchants", tags=["Approvals"])
    app.include_router(audit.router, prefix="/api/v1", tags=["Audit"])
    
    # Phase 8:  from app.api.agreements import router as agreements_router
    #           app.include_router(agreements_router, prefix="/api/v1")


# ── Module-level app instance ──────────────────────────────────────────────────

app: FastAPI = create_app()
