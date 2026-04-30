"""Health check endpoints."""

import time
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text

from app.config import settings
from app.database.session import engine

router = APIRouter()

# Captured at import so /status can report process uptime.
_STARTED_MONOTONIC = time.monotonic()
_STARTED_AT_ISO = datetime.now(timezone.utc).isoformat()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@router.get("/status")
async def status():
    """Service status: version, uptime, environment, and dependency checks."""
    db_status = "ok"
    db_error: str | None = None
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = "error"
        db_error = str(exc)

    db_check: dict = {"status": db_status}
    if db_error:
        db_check["error"] = db_error

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "service": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "started_at": _STARTED_AT_ISO,
        "uptime_seconds": round(time.monotonic() - _STARTED_MONOTONIC, 3),
        "checks": {
            "database": db_check,
        },
    }


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "LexAra API - AI-Powered Contract Analysis Engine",
        "docs": "/docs",
        "api_version": "v1"
    }
