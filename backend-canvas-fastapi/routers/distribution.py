"""
Distribution router for Canvas TA grading workload distribution.
Focused on TA grading distribution and workload metrics.
"""

import asyncio
from concurrent.futures import as_completed
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, status, Path
from loguru import logger

from dependencies import SettingsDep, ThreadPoolDep, AssignmentThreadPoolDep
from models import TAGradingRequest
from services.ta_processing import (
    get_canvas_from_ta_request,
    process_assignment_submissions_sync,
    build_ta_member_mapping,
    get_group_members_with_memberships,
)
from config import get_settings

_settings = get_settings()

# Configure loguru for this module
logger = logger.bind(module="distribution")

router = APIRouter(
    prefix="/api/distribution",
    tags=["distribution"],
    responses={404: {"description": "Not found"}},
)


@router.post("/grading/{course_id}", response_model=Dict[str, int])
async def get_grading_distribution(
    request: TAGradingRequest,
    settings: SettingsDep,
    thread_pool: ThreadPoolDep,
    assignment_pool: AssignmentThreadPoolDep,
    course_id: str = Path(
        ..., description="Canvas course ID", example=_settings.canvas_course_id or "12345"
    ),
) -> Dict[str, int]:
    """
    Get TA grading workload distribution for a Canvas course.

    Focused endpoint that returns mapping of TA names to ungraded submission counts.
    """
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
            return list(course.get_groups(
                per_page=100,  # CanvasAPI best practice
                include=["users"]  # Include user data in single request
            ))
        
        groups = await loop.run_in_executor(thread_pool, get_groups)

        def get_assignments() -> List[Any]:
            """Get all assignments with optimal parameters."""
            return list(course.get_assignments(
                per_page=100,  # CanvasAPI best practice
                include=["submission"],  # Include submission data for efficiency
                bucket="ungraded"  # Focus on ungraded assignments if available
            ))
        
        try:
            assignments = await loop.run_in_executor(thread_pool, get_assignments)
        except Exception:
            # Fallback without bucket filter if not supported
            def get_assignments_fallback() -> List[Any]:
                return list(course.get_assignments(
                    per_page=100,
                    include=["submission"]
                ))
            assignments = await loop.run_in_executor(thread_pool, get_assignments_fallback)

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
        ta_groups = []
        for group in groups:
            if "Term Project" not in getattr(group, "name", ""):
                # Use CanvasAPI best practices for group membership retrieval
                members = await get_group_members_with_memberships(group, thread_pool)
                ta_groups.append({"name": group.name, "members": members})

        # Build student-to-TA-group mapping (students are TA group members)
        student_to_ta_group = build_ta_member_mapping(ta_groups)

        # Process assignments to get grading distribution
        grading_distribution: Dict[str, int] = {}

        # Submit all jobs
        future_to_assignment = {
            assignment_pool.submit(
                process_assignment_submissions_sync, a, student_to_ta_group, ta_groups
            ): a
            for a in assignments
        }

        # Collect grading distribution as they complete
        for fut in as_completed(future_to_assignment):
            assignment = future_to_assignment[fut]
            try:
                _, ta_counts, _, err = fut.result(timeout=120.0)
                if err:
                    logger.error(
                        f"Error processing assignment {getattr(assignment, 'id', 'unknown')}: {err}"
                    )
                    continue

                # Debug: Log ta_counts for each assignment
                assignment_id = getattr(assignment, 'id', 'unknown')
                logger.info(
                    f"Assignment {assignment_id} returned ta_counts: {ta_counts}"
                )

                # Aggregate TA counts
                if ta_counts:
                    logger.info(
                        f"Aggregating ta_counts for assignment {assignment_id}: {ta_counts}"
                    )
                    for ta, count in ta_counts.items():
                        try:
                            old_count = grading_distribution.get(ta, 0)
                            new_count = old_count + int(count or 0)
                            grading_distribution[ta] = new_count
                            logger.debug(
                                f"TA {ta}: {old_count} + {count} = {new_count}"
                            )
                        except Exception as ex:
                            logger.error(f"Error aggregating count for TA {ta}: {ex}")
                            continue
                else:
                    logger.info(
                        f"Assignment {assignment_id} returned empty ta_counts"
                    )

            except Exception as ex:
                logger.error(
                    f"Exception processing assignment {getattr(assignment, 'id', 'unknown')}: {ex}"
                )

        if not grading_distribution:
            logger.info(
                f"No TA-specific grading distribution available for course {course_id} "
                "(Canvas does not assign submissions to TAs)"
            )

        logger.info(
            f"Generated grading distribution for {len(grading_distribution)} TAs in course {course_id}"
        )
        return grading_distribution

    except HTTPException:
        raise
    except Exception as ex:
        logger.exception(f"Unexpected error fetching grading distribution: {ex}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching grading distribution: {ex}",
        )
