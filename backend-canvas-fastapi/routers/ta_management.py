"""
TA management and grading endpoints.
Following FastAPI best practices for dependency injection and error handling.
Refactored to use orchestration pattern with focused subrouters.
"""

from __future__ import annotations
import asyncio
from typing import Any, Dict, List

from loguru import logger
from fastapi import APIRouter, HTTPException, status, Path
import httpx

from dependencies import SettingsDep, ThreadPoolDep, AssignmentThreadPoolDep
from services.cache import get_cached_ta_groups, set_cached_ta_groups
from services.ta_processing import (
    get_canvas_from_credentials,
    get_canvas_from_ta_request,
    get_group_members_with_memberships,
)
from models import (
    CanvasCredentials,
    TAGradingRequest,
    TAGradingResponse,
    TAGroup,
    TAGroupsResponse,
)
from config import get_settings

_settings = get_settings()

# Configure loguru for this module
logger = logger.bind(module="ta_management")

router = APIRouter(
    prefix="/api",
    tags=["ta-management"],
    responses={404: {"description": "Not found"}},
)


@router.post("/ta-groups/{course_id}", response_model=TAGroupsResponse)
async def get_ta_groups(
    request: CanvasCredentials,
    settings: SettingsDep,
    thread_pool: ThreadPoolDep,
    course_id: str = Path(
        ..., description="Canvas course ID", example=_settings.canvas_course_id or "12345"
    ),
) -> TAGroupsResponse:
    """
    Fetch TA groups from a Canvas course (excludes Term Project groups).

    - **course_id**: Canvas course ID
    - **base_url**: Canvas instance base URL
    - **api_token**: Canvas API access token
    """
    try:
        # Check cache first (if enabled)
        if settings.enable_caching:
            cached_result = get_cached_ta_groups(
                course_id, request.api_token, settings.ta_cache_ttl
            )
            if cached_result is not None:
                ta_groups_data, course_data, error = cached_result
                if error:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, detail=error
                    )

                # Convert to response format
                ta_groups = [TAGroup(**group_data) for group_data in ta_groups_data]
                return TAGroupsResponse(
                    ta_groups=ta_groups,
                    course_info=course_data or {},
                    total_ta_groups=len(ta_groups),
                )

        canvas = await get_canvas_from_credentials(request, settings)
        loop = asyncio.get_event_loop()

        # Get course and groups
        course = await loop.run_in_executor(
            thread_pool, lambda: canvas.get_course(course_id)
        )

        def get_groups() -> List[Any]:
            """Get all groups with optimal pagination and includes."""
            return list(course.get_groups(
                per_page=100,  # CanvasAPI best practice: explicit pagination
                include=["users", "group_category"]  # Include related data in single request
            ))
        
        groups = await loop.run_in_executor(thread_pool, get_groups)

        # Filter out Term Project groups and convert to TA groups
        ta_groups = []
        logger.debug(
            "Processing {total_groups} total groups from Canvas",
            total_groups=len(groups),
        )
        for group in groups:
            if "Term Project" not in group.name:
                logger.debug(
                    "Including TA group: '{group_name}'", group_name=group.name
                )

                # Get group members using CanvasAPI best practices
                members = await get_group_members_with_memberships(group, thread_pool)

                ta_groups.append(
                    TAGroup(
                        id=group.id,
                        name=group.name,
                        description=getattr(group, "description", None),
                        course_id=course_id,
                        members_count=len(members),
                        members=members,
                    )
                )

        logger.debug(
            "Final TA groups count: {ta_groups_count}", ta_groups_count=len(ta_groups)
        )
        for ta_group in ta_groups:
            logger.debug(
                "Final TA group: {ta_group_name} with {members_count} members",
                ta_group_name=ta_group.name,
                members_count=ta_group.members_count,
            )

        course_info = {
            "id": course.id,
            "name": course.name,
            "course_code": getattr(course, "course_code", None),
        }

        # Cache the result (if enabled)
        if settings.enable_caching:
            ta_groups_data = [
                {
                    "id": ta_group.id,
                    "name": ta_group.name,
                    "description": ta_group.description,
                    "course_id": ta_group.course_id,
                    "members_count": ta_group.members_count,
                    "members": ta_group.members,
                }
                for ta_group in ta_groups
            ]
            set_cached_ta_groups(
                course_id, request.api_token, ta_groups_data, course_info, None
            )

        return TAGroupsResponse(
            ta_groups=ta_groups,
            course_info=course_info,
            total_ta_groups=len(ta_groups),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching TA groups: {str(e)}",
        )


@router.post("/ta-grading", response_model=TAGradingResponse)
async def get_ta_grading_info(
    request: TAGradingRequest,
    settings: SettingsDep,
    thread_pool: ThreadPoolDep,
    assignment_pool: AssignmentThreadPoolDep,
) -> TAGradingResponse:
    """
    Orchestrator endpoint that combines data from focused subrouters.
    Maintains backward compatibility while using modular architecture.

    This endpoint calls the new focused subrouters internally to compose
    the complete TAGradingResponse.
    """
    try:
        # Get course information first
        canvas = await get_canvas_from_ta_request(request, settings)
        loop = asyncio.get_event_loop()

        course = await loop.run_in_executor(
            thread_pool, lambda: canvas.get_course(request.course_id)
        )

        course_info = {
            "id": getattr(course, "id", None) or request.course_id,
            "name": getattr(course, "name", None),
            "course_code": getattr(course, "course_code", None),
        }

        # Prepare request body for internal API calls
        # Use resolved credentials so internal calls inherit env defaults
        from dependencies import resolve_credentials

        base_url, token = resolve_credentials(
            request.base_url, request.api_token, settings
        )
        request_data = {
            "base_url": base_url,
            "api_token": token,
            "course_id": request.course_id,
        }
        if hasattr(request, "assignment_id") and request.assignment_id:
            request_data["assignment_id"] = request.assignment_id

        # Call focused endpoints in parallel using httpx
        async with httpx.AsyncClient() as client:
            # Determine base URL for internal calls
            base_url = f"http://localhost:{settings.port}"

            # Create tasks for parallel execution
            tasks = [
                client.post(
                    f"{base_url}/api/submissions/ungraded/{request.course_id}",
                    json=request_data,
                ),
                client.post(
                    f"{base_url}/api/statistics/assignments/{request.course_id}",
                    json=request_data,
                ),
                client.post(
                    f"{base_url}/api/distribution/grading/{request.course_id}",
                    json=request_data,
                ),
                client.post(
                    f"{base_url}/api/ta-groups/{request.course_id}", json=request_data
                ),
            ]

            # Execute all requests in parallel
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # Process responses
            ungraded_submissions = []
            assignment_stats = []
            grading_distribution = {}
            ta_groups = []

            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    logger.error(f"Error calling internal endpoint {i}: {response}")
                    continue

                if response.status_code == 200:
                    data = response.json()
                    if i == 0:  # ungraded submissions
                        ungraded_submissions = data
                    elif i == 1:  # assignment statistics
                        assignment_stats = data
                    elif i == 2:  # grading distribution
                        grading_distribution = data
                    elif i == 3:  # ta groups
                        ta_groups = data.get("ta_groups", [])

        return TAGradingResponse(
            ungraded_submissions=ungraded_submissions,
            ta_groups=ta_groups,
            course_info=course_info,
            total_ungraded=len(ungraded_submissions),
            grading_distribution=grading_distribution,
            assignment_stats=assignment_stats,
        )

    except HTTPException:
        raise
    except Exception as ex:
        logger.exception(f"Unexpected error in TA grading orchestrator: {ex}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching TA grading info: {ex}",
        )
