"""
FastAPI dependency functions following best practices.
Provides reusable dependencies for Canvas client, credentials validation, and common parameters.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Annotated, Optional

from canvasapi import Canvas
from canvasapi.exceptions import CanvasException, InvalidAccessToken
from fastapi import Depends, HTTPException, status

from config import Settings, get_settings

logger = logging.getLogger(__name__)

# Thread pool executors for Canvas API calls
thread_pool_executor = None
assignment_thread_pool_executor = None


def get_thread_pool(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ThreadPoolExecutor:
    """
    Get or create a thread pool executor for Canvas API calls.
    Uses settings-based configuration for max workers.
    """
    global thread_pool_executor
    if thread_pool_executor is None:
        thread_pool_executor = ThreadPoolExecutor(
            max_workers=settings.thread_pool_max_workers
        )
    return thread_pool_executor


def get_assignment_thread_pool(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ThreadPoolExecutor:
    """
    Get or create an optimized thread pool for assignment processing.
    Uses a smaller max_workers count (3) optimized for Canvas API rate limits.
    This matches the original performance optimization.
    """
    global assignment_thread_pool_executor
    if assignment_thread_pool_executor is None:
        assignment_thread_pool_executor = ThreadPoolExecutor(
            max_workers=settings.assignment_thread_pool_max_workers
        )
    return assignment_thread_pool_executor


async def validate_canvas_credentials(
    base_url: str, api_token: str, settings: Annotated[Settings, Depends(get_settings)]
) -> Canvas:
    """
    Validate Canvas credentials and return Canvas client.

    Args:
        base_url: Canvas base URL
        api_token: Canvas API token
        settings: Application settings

    Returns:
        Canvas client instance

    Raises:
        HTTPException: If credentials are invalid or Canvas API is unreachable
    """
    try:
        # Create Canvas client
        canvas = Canvas(str(base_url), api_token)

        # Test the connection by getting current user
        executor = get_thread_pool(settings)
        loop = asyncio.get_event_loop()

        user = await loop.run_in_executor(executor, lambda: canvas.get_current_user())

        logger.info(f"Successfully validated Canvas credentials for user: {user.name}")
        return canvas

    except InvalidAccessToken as e:
        logger.error(f"Invalid Canvas access token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Canvas API token. Please check your credentials.",
        )
    except CanvasException as e:
        logger.error(f"Canvas API error during validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Canvas API error: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error during Canvas validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect to Canvas: {str(e)}",
        )


class CanvasCredentials:
    """Dependency class for Canvas credentials with validation."""

    def __init__(self, base_url: str, api_token: str) -> None:
        self.base_url = base_url
        self.api_token = api_token


async def get_validated_canvas_client(
    credentials: CanvasCredentials, settings: Annotated[Settings, Depends(get_settings)]
) -> Canvas:
    """
    Dependency that validates Canvas credentials and returns client.

    Args:
        credentials: Canvas credentials
        settings: Application settings

    Returns:
        Validated Canvas client
    """
    return await validate_canvas_credentials(
        credentials.base_url, credentials.api_token, settings
    )


class CommonQueryParams:
    """Common query parameters for pagination and filtering."""

    def __init__(
        self, skip: int = 0, limit: int = 100, q: Optional[str] = None
    ) -> None:
        self.skip = skip
        self.limit = max(1, min(limit, 1000))  # Ensure reasonable limits
        self.q = q


class CourseListParams:
    """Parameters for course list requests."""

    def __init__(self, course_ids: list[str]) -> None:
        if not course_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one course_id is required",
            )
        self.course_ids = course_ids


# Type aliases for cleaner dependency injection
SettingsDep = Annotated[Settings, Depends(get_settings)]
ThreadPoolDep = Annotated[ThreadPoolExecutor, Depends(get_thread_pool)]
AssignmentThreadPoolDep = Annotated[
    ThreadPoolExecutor, Depends(get_assignment_thread_pool)
]
CommonParamsDep = Annotated[CommonQueryParams, Depends()]
