"""
Cache management endpoints.
Provides cache clearing functionality matching the original implementation.
"""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status

from dependencies import SettingsDep, validate_canvas_credentials
from models import CanvasCredentials
from services.cache import clear_all_caches, get_cache_stats

router = APIRouter(
    prefix="/api/cache",
    tags=["cache"],
    responses={404: {"description": "Not found"}},
)


@router.post("/clear")
async def clear_cache(
    request: CanvasCredentials,
    settings: SettingsDep,
) -> Dict[str, Any]:
    """
    Clear cache for improved performance - useful for TAs to refresh data.
    Validates credentials before allowing cache clear (matching original behavior).
    """
    try:
        # Validate credentials before allowing cache clear (security measure)
        await validate_canvas_credentials(
            str(request.base_url), request.api_token, settings
        )

        # Clear all caches
        stats = clear_all_caches()

        return {
            "message": "Cache cleared successfully",
            "timestamp": datetime.utcnow().isoformat(),
            "statistics": stats,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing cache: {str(e)}",
        )


@router.get("/stats")
async def get_cache_statistics(
    settings: SettingsDep,
) -> Dict[str, Any]:
    """
    Get cache statistics for monitoring and debugging.
    """
    try:
        stats = get_cache_stats()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "caching_enabled": settings.enable_caching,
            "ttl_settings": {
                "ta_groups": settings.ta_cache_ttl,
                "assignment_stats": settings.assignment_cache_ttl,
            },
            "cache_stats": stats,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving cache statistics: {str(e)}",
        )