"""Health check endpoints."""

from fastapi import APIRouter
from datetime import datetime

from app.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.version,  # CA-022: use settings.version not hardcoded string
    }


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "LexAra API - AI-Powered Contract Analysis Engine",
        "docs": "/docs",
        "api_version": "v1"
    }
