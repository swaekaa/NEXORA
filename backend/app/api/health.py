"""
NEXORA — Health Router

GET /health  — lightweight liveness check (no DB required)
GET /health/ready — full readiness check (verifies DB connection)

Separating liveness from readiness follows Kubernetes conventions and
allows load balancers to make informed decisions.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import settings
from app.database.connection import check_db_connectivity

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Liveness check",
    response_description="Service is alive",
)
async def health_liveness() -> dict:
    """
    Liveness probe — returns immediately without touching external dependencies.
    A load balancer that receives 200 here knows the process is running.
    """
    return {
        "status": "ok",
        "service": "nexora-api",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }


@router.get(
    "/health/ready",
    summary="Readiness check",
    response_description="Service is ready to accept traffic",
)
async def health_readiness() -> dict:
    """
    Readiness probe — verifies that all critical dependencies are reachable.
    Returns 200 if ready, 503 if the database cannot be reached.
    """
    from fastapi import HTTPException

    db_ok = await check_db_connectivity()

    if not db_ok:
        logger.error("Readiness check failed: database unreachable")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "service": "nexora-api",
                "db": "unreachable",
            },
        )

    return {
        "status": "ready",
        "service": "nexora-api",
        "version": settings.APP_VERSION,
        "db": "connected",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }
