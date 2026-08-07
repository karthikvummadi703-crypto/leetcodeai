"""
Health-check endpoint.

GET /health — Returns application health status.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health():
    """Application health check."""
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        environment=settings.app_env,
        version="0.1.0",
    )
