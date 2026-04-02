"""Health check endpoints."""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "LexRisk API - AI-Powered Contract Analysis Engine",
        "docs": "/docs",
        "api_version": "v1"
    }
