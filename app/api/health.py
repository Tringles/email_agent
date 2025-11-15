"""Health check endpoints."""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("/")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    # TODO: Check database connection, etc.
    return {
        "status": "ready",
        "timestamp": datetime.now().isoformat(),
    }
