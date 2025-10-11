"""
Health check and system status endpoints.
Following FastAPI best practices for monitoring and status checks.
"""

from datetime import datetime

from fastapi import APIRouter

from dependencies import SettingsDep
from models import HealthResponse


router = APIRouter(
    tags=["health"],
    responses={200: {"description": "Service is healthy"}},
)


@router.get("/api/health", response_model=HealthResponse)
async def health_check(settings: SettingsDep) -> HealthResponse:
    """
    Health check endpoint for monitoring service availability.

    Returns basic service information and current timestamp.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version=settings.app_version,
        canvas_api_version=settings.canvas_api_version,
    )


@router.get("/health", response_model=HealthResponse)
async def root_health_check(settings: SettingsDep) -> HealthResponse:
    """Alternative health check endpoint at root level."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version=settings.app_version,
        canvas_api_version=settings.canvas_api_version,
    )
