"""
Background refresh endpoints for cache warming.
Implements background task pattern for non-blocking cache updates.
"""

import asyncio
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from loguru import logger

from dependencies import AssignmentThreadPoolDep, SettingsDep, ThreadPoolDep
from models import TAGradingRequest
from services.cache import (
    set_cached_assignment_stats,
    set_cached_ta_groups,
)
from services.ta_processing import (
    get_canvas_from_ta_request,
    get_group_members_with_memberships,
)


router = APIRouter(
    prefix="/api/background",
    tags=["background"],
    responses={404: {"description": "Not found"}},
)


# Configure loguru for this module
logger = logger.bind(module="background")


async def refresh_ta_groups_task(
    request: TAGradingRequest,
    settings: SettingsDep,
    thread_pool: ThreadPoolDep,
) -> None:
    """
    Background task to refresh TA groups cache.
    Runs asynchronously without blocking the response.
    """
    try:
        # Ensure course_id is an integer for Canvas API
        course_id = (
            int(request.course_id)
            if isinstance(request.course_id, str)
            else request.course_id
        )

        logger.info(f"Starting background refresh for TA groups in course {course_id}")

        canvas = await get_canvas_from_ta_request(request, settings)
        loop = asyncio.get_event_loop()

        # Get course and groups
        course = await loop.run_in_executor(
            thread_pool, lambda: canvas.get_course(course_id)
        )

        def get_groups():
            return list(
                course.get_groups(per_page=100, include=["users", "group_category"])
            )

        groups = await loop.run_in_executor(thread_pool, get_groups)

        # Filter and process TA groups
        ta_groups_data = []
        for group in groups:
            if "Term Project" not in group.name:
                members = await get_group_members_with_memberships(group, thread_pool)
                ta_groups_data.append(
                    {
                        "id": group.id,
                        "name": group.name,
                        "description": getattr(group, "description", None),
                        "course_id": course_id,
                        "members_count": len(members),
                        "members": members,
                    }
                )

        course_info = {
            "id": course.id,
            "name": course.name,
            "course_code": getattr(course, "course_code", None),
        }

        # Update cache (cache key uses string course_id)
        set_cached_ta_groups(
            str(course_id),
            request.api_token,
            ta_groups_data,
            course_info,
            None,
        )

        logger.info(
            f"Background refresh completed for TA groups in course {course_id}: "
            f"{len(ta_groups_data)} groups cached"
        )

    except Exception as e:
        logger.error(
            f"Background refresh failed for TA groups in course {request.course_id}: {e}"
        )


async def refresh_assignment_stats_task(
    request: TAGradingRequest,
    settings: SettingsDep,
    thread_pool: ThreadPoolDep,
    assignment_pool: AssignmentThreadPoolDep,
) -> None:
    """
    Background task to refresh assignment statistics cache.
    Runs asynchronously without blocking the response.
    """
    try:
        # Ensure course_id is an integer for Canvas API
        course_id = (
            int(request.course_id)
            if isinstance(request.course_id, str)
            else request.course_id
        )

        logger.info(
            f"Starting background refresh for assignment stats in course {course_id}"
        )

        # Import here to avoid circular dependencies
        from routers.statistics import get_assignment_statistics_logic

        assignment_stats = await get_assignment_statistics_logic(
            request, settings, thread_pool, assignment_pool
        )

        # Update cache (cache key uses string course_id)
        set_cached_assignment_stats(
            str(course_id),
            request.api_token,
            assignment_stats,
        )

        logger.info(
            f"Background refresh completed for assignment stats in course {course_id}: "
            f"{len(assignment_stats)} assignments cached"
        )

    except Exception as e:
        logger.error(
            f"Background refresh failed for assignment stats in course {request.course_id}: {e}"
        )


@router.post("/refresh-ta-groups/{course_id}")
async def trigger_ta_groups_refresh(
    request: TAGradingRequest,
    background_tasks: BackgroundTasks,
    settings: SettingsDep,
    thread_pool: ThreadPoolDep,
) -> Dict[str, Any]:
    """
    Trigger background refresh of TA groups cache.
    Returns immediately while refresh happens in background.

    - **course_id**: Canvas course ID
    - **base_url**: Canvas instance base URL
    - **api_token**: Canvas API access token
    """
    try:
        # Validate that caching is enabled
        if not settings.enable_caching:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Caching is disabled - background refresh not available",
            )

        # Add background task
        background_tasks.add_task(
            refresh_ta_groups_task,
            request,
            settings,
            thread_pool,
        )

        logger.info(
            f"Queued background refresh for TA groups in course {request.course_id}"
        )

        return {
            "message": "Background refresh queued for TA groups",
            "course_id": request.course_id,
            "status": "queued",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error queueing background refresh: {str(e)}",
        )


@router.post("/refresh-assignment-stats/{course_id}")
async def trigger_assignment_stats_refresh(
    request: TAGradingRequest,
    background_tasks: BackgroundTasks,
    settings: SettingsDep,
    thread_pool: ThreadPoolDep,
    assignment_pool: AssignmentThreadPoolDep,
) -> Dict[str, Any]:
    """
    Trigger background refresh of assignment statistics cache.
    Returns immediately while refresh happens in background.

    - **course_id**: Canvas course ID
    - **base_url**: Canvas instance base URL
    - **api_token**: Canvas API access token
    """
    try:
        # Validate that caching is enabled
        if not settings.enable_caching:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Caching is disabled - background refresh not available",
            )

        # Add background task
        background_tasks.add_task(
            refresh_assignment_stats_task,
            request,
            settings,
            thread_pool,
            assignment_pool,
        )

        logger.info(
            f"Queued background refresh for assignment stats in course {request.course_id}"
        )

        return {
            "message": "Background refresh queued for assignment statistics",
            "course_id": request.course_id,
            "status": "queued",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error queueing background refresh: {str(e)}",
        )


@router.post("/refresh-all/{course_id}")
async def trigger_full_refresh(
    request: TAGradingRequest,
    background_tasks: BackgroundTasks,
    settings: SettingsDep,
    thread_pool: ThreadPoolDep,
    assignment_pool: AssignmentThreadPoolDep,
) -> Dict[str, Any]:
    """
    Trigger background refresh of all caches (TA groups and assignment stats).
    Returns immediately while refresh happens in background.

    This is useful for scheduled refreshes to keep all data current.

    - **course_id**: Canvas course ID
    - **base_url**: Canvas instance base URL
    - **api_token**: Canvas API access token
    """
    try:
        # Validate that caching is enabled
        if not settings.enable_caching:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Caching is disabled - background refresh not available",
            )

        # Queue both background tasks
        background_tasks.add_task(
            refresh_ta_groups_task,
            request,
            settings,
            thread_pool,
        )
        background_tasks.add_task(
            refresh_assignment_stats_task,
            request,
            settings,
            thread_pool,
            assignment_pool,
        )

        logger.info(f"Queued full background refresh for course {request.course_id}")

        return {
            "message": "Background refresh queued for all caches",
            "course_id": request.course_id,
            "status": "queued",
            "tasks": ["ta_groups", "assignment_stats"],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error queueing background refresh: {str(e)}",
        )
