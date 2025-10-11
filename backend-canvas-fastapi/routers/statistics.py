"""
Statistics router for Canvas assignment grading statistics.
Focused on assignment grading statistics and metrics.
"""

import asyncio
from concurrent.futures import as_completed
from typing import Any, List

from fastapi import APIRouter, HTTPException, Path, status
from loguru import logger

from config import get_settings
from dependencies import AssignmentThreadPoolDep, SettingsDep, ThreadPoolDep
from models import AssignmentGradingStats, TAGradingRequest
from services.ta_processing import (
    build_ta_member_mapping,
    get_canvas_from_ta_request,
    get_group_members_with_memberships,
    process_assignment_submissions_sync,
)


_settings = get_settings()

# Configure loguru for this module
logger = logger.bind(module="statistics")

router = APIRouter(
    prefix="/api/statistics",
    tags=["statistics"],
    responses={404: {"description": "Not found"}},
)


async def get_assignment_statistics_logic(
    request: TAGradingRequest,
    settings: SettingsDep,
    thread_pool: ThreadPoolDep,
    assignment_pool: AssignmentThreadPoolDep,
) -> List[AssignmentGradingStats]:
    """
    Core logic for getting assignment statistics.
    Extracted for reuse by both endpoint and background tasks.
    """
    # Ensure course_id is an integer for Canvas API
    course_id = (
        int(request.course_id)
        if isinstance(request.course_id, str)
        else request.course_id
    )

    try:
        # Get Canvas client and course data
        canvas = await get_canvas_from_ta_request(request, settings)
        loop = asyncio.get_event_loop()

        # Load course, groups, and assignments
        course = await loop.run_in_executor(
            thread_pool, lambda: canvas.get_course(course_id)
        )

        def get_groups() -> List[Any]:
            """Get all groups with optimal pagination."""
            return list(
                course.get_groups(
                    per_page=100,  # CanvasAPI best practice
                    include=["users"],  # Include user data in single request
                )
            )

        groups = await loop.run_in_executor(thread_pool, get_groups)

        def get_assignments() -> List[Any]:
            """Get all assignments with optimal parameters."""
            return list(
                course.get_assignments(
                    per_page=100,  # CanvasAPI best practice
                    include=["submission"],  # Include submission data for efficiency
                    bucket="ungraded",  # Focus on ungraded assignments if available
                )
            )

        try:
            assignments = await loop.run_in_executor(thread_pool, get_assignments)
        except Exception:
            # Fallback without bucket filter if not supported
            def get_assignments_fallback() -> List[Any]:
                return list(
                    course.get_assignments(per_page=100, include=["submission"])
                )

            assignments = await loop.run_in_executor(
                thread_pool, get_assignments_fallback
            )

        # Optional single-assignment constraint
        if getattr(request, "assignment_id", None):
            try:
                assignment = await loop.run_in_executor(
                    thread_pool, lambda: course.get_assignment(request.assignment_id)
                )
                assignments = [assignment] if assignment is not None else []
            except Exception as ex:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Assignment {request.assignment_id} not found: {ex}",
                )
        # Filter TA groups (exclude Term Project groups)
        # TA Groups are all groups except those with "Term Project" in the name
        ta_groups = []
        for group in groups:
            if "Term Project" not in getattr(group, "name", ""):
                # Use CanvasAPI best practices for group membership retrieval
                members = await get_group_members_with_memberships(group, thread_pool)
                ta_groups.append({"name": group.name, "members": members})

        # Build student-to-TA-group mapping (students are TA group members)
        student_to_ta_group = build_ta_member_mapping(ta_groups)

        # Process assignments to get statistics
        assignment_stats_raw = []

        # Submit all jobs
        future_to_assignment = {
            assignment_pool.submit(
                process_assignment_submissions_sync, a, student_to_ta_group, ta_groups
            ): a
            for a in assignments
        }

        # Collect statistics as they complete
        for fut in as_completed(future_to_assignment):
            assignment = future_to_assignment[fut]
            try:
                _, _, stats, err = fut.result(timeout=120.0)
                if err:
                    logger.error(
                        f"Error processing assignment {getattr(assignment, 'id', 'unknown')}: {err}"
                    )
                    continue

                if stats:
                    assignment_stats_raw.append(stats)

            except Exception as ex:
                logger.error(
                    f"Exception processing assignment {getattr(assignment, 'id', 'unknown')}: {ex}"
                )

        # Convert to response models
        assignment_statistics = []
        for stats_data in assignment_stats_raw:
            try:
                assignment_statistics.append(AssignmentGradingStats(**stats_data))
            except Exception as ex:
                logger.error(f"Invalid assignment stats payload skipped: {ex}")

        logger.info(
            f"Generated statistics for {len(assignment_statistics)} assignments in course {course_id}"
        )
        return assignment_statistics

    except HTTPException:
        raise
    except Exception as ex:
        logger.exception(f"Unexpected error fetching assignment statistics: {ex}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching assignment statistics: {ex}",
        )


@router.post("/assignments/{course_id}", response_model=List[AssignmentGradingStats])
async def get_assignment_statistics(
    request: TAGradingRequest,
    settings: SettingsDep,
    thread_pool: ThreadPoolDep,
    assignment_pool: AssignmentThreadPoolDep,
    course_id: str = Path(
        ...,
        description="Canvas course ID",
        example=_settings.canvas_course_id or "12345",
    ),
) -> List[AssignmentGradingStats]:
    """
    Get assignment grading statistics for a Canvas course.

    Focused endpoint that returns only assignment grading statistics.
    """
    # Override request course_id with path parameter to ensure consistency
    request.course_id = course_id

    return await get_assignment_statistics_logic(
        request, settings, thread_pool, assignment_pool
    )
