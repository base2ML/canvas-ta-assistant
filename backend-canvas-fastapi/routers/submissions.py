"""
Submissions router for Canvas ungraded submissions.
Focused on ungraded submission retrieval and management.
"""

import asyncio
from concurrent.futures import as_completed
from typing import Any, List

from fastapi import APIRouter, HTTPException, status
from loguru import logger

from dependencies import SettingsDep, ThreadPoolDep, AssignmentThreadPoolDep
from models import TAGradingRequest, UngradedSubmission
from services.ta_processing import (
    get_canvas_from_ta_request,
    process_assignment_submissions_sync,
    build_ta_member_mapping,
    get_group_members_with_memberships,
)

# Configure loguru for this module
logger = logger.bind(module="submissions")

router = APIRouter(
    prefix="/api/submissions",
    tags=["submissions"],
    responses={404: {"description": "Not found"}},
)


@router.post("/ungraded/{course_id}", response_model=List[UngradedSubmission])
async def get_ungraded_submissions(
    course_id: str,
    request: TAGradingRequest,
    settings: SettingsDep,
    thread_pool: ThreadPoolDep,
    assignment_pool: AssignmentThreadPoolDep,
) -> List[UngradedSubmission]:
    """
    Get ungraded submissions for a Canvas course.

    Focused endpoint that returns only ungraded submissions assigned to TAs.
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

        # Process assignments to get ungraded submissions
        ungraded_submissions_raw = []

        # Submit all jobs
        future_to_assignment = {
            assignment_pool.submit(
                process_assignment_submissions_sync, a, student_to_ta_group, ta_groups
            ): a
            for a in assignments
        }

        # Collect ungraded submissions as they complete
        for fut in as_completed(future_to_assignment):
            assignment = future_to_assignment[fut]
            try:
                ungraded, _, _, err = fut.result(timeout=120.0)
                if err:
                    logger.error(
                        f"Error processing assignment {getattr(assignment, 'id', 'unknown')}: {err}"
                    )
                    continue

                # Add course information to submissions
                course_name = getattr(course, "name", None)
                for submission in ungraded or []:
                    submission["course_name"] = course_name
                    submission["course_id"] = course_id

                if ungraded:
                    ungraded_submissions_raw.extend(ungraded)

            except Exception as ex:
                logger.error(
                    f"Exception processing assignment {getattr(assignment, 'id', 'unknown')}: {ex}"
                )

        # Convert to response models
        ungraded_submissions = []
        for submission_data in ungraded_submissions_raw:
            try:
                ungraded_submissions.append(UngradedSubmission(**submission_data))
            except Exception as ex:
                logger.error(f"Invalid ungraded submission payload skipped: {ex}")

        logger.info(
            f"Found {len(ungraded_submissions)} ungraded submissions for course {course_id}"
        )
        return ungraded_submissions

    except HTTPException:
        raise
    except Exception as ex:
        logger.exception(f"Unexpected error fetching ungraded submissions: {ex}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching ungraded submissions: {ex}",
        )
