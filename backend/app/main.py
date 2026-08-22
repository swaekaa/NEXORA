"""
NEXORA Backend — FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(
    title="NEXORA API",
    description="The agreement layer for AI commerce",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "service": "nexora-backend",
    }


# TODO (Phase 1+): Register API routers here
# from app.api import catalog, buyer, negotiations, agreements, payments, webhooks, audit, approvals, merchant
# app.include_router(catalog.router, prefix="/api/v1", tags=["catalog"])
# app.include_router(buyer.router, prefix="/api/v1", tags=["buyer"])
# ... etc
