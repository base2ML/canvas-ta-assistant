"""
Assignment-related API endpoints.
Following FastAPI best practices with dependency injection and proper error handling.
"""

import asyncio
from typing import Annotated, Any, Dict, List, Optional, Tuple

from canvasapi import Canvas
from canvasapi.exceptions import CanvasException
from fastapi import APIRouter, Depends, HTTPException, status

from config import Settings
from dependencies import SettingsDep, ThreadPoolDep, get_validated_canvas_client
from services.cache import get_cached_assignments, set_cached_assignments
from models import (
    Assignment,
    AssignmentRequest,
    AssignmentResponse,
    Course,
    DetailedAssignment,
)

router = APIRouter(
    prefix="/api",
    tags=["assignments"],
    responses={404: {"description": "Not found"}},
)


async def get_canvas_from_request(
    request: AssignmentRequest, settings: SettingsDep
) -> Canvas:
    """Convert AssignmentRequest to Canvas client."""
    from dependencies import validate_canvas_credentials

    return await validate_canvas_credentials(
        str(request.base_url), request.api_token, settings
    )


@router.post("/assignments", response_model=AssignmentResponse)
async def get_assignments(
    request: AssignmentRequest, settings: SettingsDep, thread_pool: ThreadPoolDep
) -> AssignmentResponse:
    """
    Fetch assignments from specified Canvas courses with status information.

    - **course_ids**: List of Canvas course IDs to fetch assignments from
    - **base_url**: Canvas instance base URL
    - **api_token**: Canvas API access token
    """
    try:
        # Check cache first (if enabled)
        if settings.enable_caching:
            cached_result = get_cached_assignments(
                request.course_ids, request.api_token, settings.assignment_cache_ttl
            )
            if cached_result is not None:
                assignments_data, courses_data, warnings = cached_result

                # Convert back to response format
                assignments = [
                    Assignment(**assignment_data)
                    for assignment_data in assignments_data
                ]
                courses = [Course(**course_data) for course_data in courses_data]

                return AssignmentResponse(
                    assignments=assignments,
                    courses=courses,
                    total_assignments=len(assignments),
                    warnings=warnings if warnings else None,
                )

        canvas = await get_canvas_from_request(request, settings)

        # Fetch assignments from all courses concurrently
        loop = asyncio.get_event_loop()

        async def fetch_course_assignments(
            course_id: str,
        ) -> Tuple[Optional[Any], List[Any]]:
            try:
                course = await loop.run_in_executor(
                    thread_pool, lambda: canvas.get_course(course_id)
                )
                def get_assignments() -> List[Any]:
                    """Get assignments using CanvasAPI best practices."""
                    return list(course.get_assignments(
                        per_page=100,  # CanvasAPI best practice
                        include=["submission", "assignment_group"],  # Include related data
                        bucket="ungraded"  # Focus on ungraded assignments if available
                    ))
                
                try:
                    assignments = await loop.run_in_executor(thread_pool, get_assignments)
                except Exception:
                    # Fallback without bucket filter if not supported
                    def get_assignments_fallback() -> List[Any]:
                        return list(course.get_assignments(
                            per_page=100,
                            include=["submission", "assignment_group"]
                        ))
                    assignments = await loop.run_in_executor(thread_pool, get_assignments_fallback)
                return course, assignments
            except Exception as e:
                print(f"Error fetching assignments for course {course_id}: {e}")
                return None, []

        # Process all courses concurrently
        tasks = [fetch_course_assignments(cid) for cid in request.course_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_assignments = []
        courses = []
        warnings = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                warnings.append(
                    f"Error processing course {request.course_ids[i]}: {str(result)}"
                )
                continue

            # Ensure result is a tuple
            if not isinstance(result, tuple) or len(result) != 2:
                warnings.append(
                    f"Invalid result format for course {request.course_ids[i]}"
                )
                continue

            course, assignments = result
            if course is None:
                warnings.append(f"Could not access course {request.course_ids[i]}")
                continue

            courses.append(
                Course(
                    id=str(course.id),
                    name=course.name,
                    course_code=getattr(course, "course_code", None),
                    enrollment_term_id=getattr(course, "enrollment_term_id", None),
                )
            )

            # Process assignments for this course
            for assignment in assignments:
                # Get submission status
                try:

                    def get_submission() -> Any:
                        """Get submission using CanvasAPI best practices."""
                        return assignment.get_submission(
                            "self", 
                            include=["submission_history", "submission_comments", "rubric_assessment"]
                        )

                    submission = await loop.run_in_executor(thread_pool, get_submission)

                    status_info = determine_assignment_status(assignment, submission)

                    all_assignments.append(
                        Assignment(
                            id=assignment.id,
                            name=assignment.name,
                            description=getattr(assignment, "description", None),
                            course_name=course.name,
                            course_id=str(course.id),
                            due_at=getattr(assignment, "due_at", None),
                            unlock_at=getattr(assignment, "unlock_at", None),
                            lock_at=getattr(assignment, "lock_at", None),
                            submitted_at=getattr(submission, "submitted_at", None),
                            points_possible=getattr(
                                assignment, "points_possible", None
                            ),
                            html_url=getattr(assignment, "html_url", None),
                            assignment_group_id=getattr(
                                assignment, "assignment_group_id", None
                            ),
                            **status_info,
                        )
                    )

                except Exception:
                    # If we can't get submission, still include the assignment
                    all_assignments.append(
                        Assignment(
                            id=assignment.id,
                            name=assignment.name,
                            description=getattr(assignment, "description", None),
                            course_name=course.name,
                            course_id=str(course.id),
                            due_at=getattr(assignment, "due_at", None),
                            points_possible=getattr(
                                assignment, "points_possible", None
                            ),
                            html_url=getattr(assignment, "html_url", None),
                            status="unknown",
                            status_text="Could not determine status",
                            grade=None,
                            score=None,
                        )
                    )

        # Cache the result (if enabled)
        if settings.enable_caching:
            # Convert to serializable data for caching
            assignments_data = [
                assignment.model_dump() for assignment in all_assignments
            ]
            courses_data = [course.model_dump() for course in courses]
            set_cached_assignments(
                request.course_ids,
                request.api_token,
                assignments_data,
                courses_data,
                warnings,
            )

        return AssignmentResponse(
            assignments=all_assignments,
            courses=courses,
            total_assignments=len(all_assignments),
            warnings=warnings if warnings else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching assignments: {str(e)}",
        )


@router.post("/assignment/{assignment_id}/details", response_model=DetailedAssignment)
async def get_assignment_details(
    assignment_id: int,
    request: AssignmentRequest,
    settings: SettingsDep,
    thread_pool: ThreadPoolDep,
) -> DetailedAssignment:
    """
    Get detailed information about a specific assignment including submission and rubric.

    - **assignment_id**: Canvas assignment ID
    - **course_ids**: Should contain the course ID where the assignment exists
    """
    try:
        canvas = await get_canvas_from_request(request, settings)
        loop = asyncio.get_event_loop()

        # Find the assignment in one of the provided courses
        assignment = None
        course = None

        for course_id in request.course_ids:
            try:
                course = await loop.run_in_executor(
                    thread_pool, lambda: canvas.get_course(course_id)
                )
                if course is not None:
                    assignment = await loop.run_in_executor(
                        thread_pool, lambda: course.get_assignment(assignment_id)
                    )
                break
            except Exception:
                continue

        if not assignment or not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assignment {assignment_id} not found in specified courses",
            )

        # Get submission and rubric concurrently
        submission_task = loop.run_in_executor(
            thread_pool,
            lambda: assignment.get_submission(
                "self", include=["submission_history", "rubric_assessment"]
            ),
        )

        rubric_task = loop.run_in_executor(
            thread_pool, lambda: getattr(assignment, "rubric", None)
        )

        submission, rubric = await asyncio.gather(submission_task, rubric_task)

        return DetailedAssignment(
            assignment=assignment.__dict__,
            submission=submission.__dict__ if submission else {},
            rubric=rubric if isinstance(rubric, list) else None,
            course_info={
                "id": course.id,
                "name": course.name,
                "course_code": getattr(course, "course_code", None),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching assignment details: {str(e)}",
        )


def determine_assignment_status(assignment: Any, submission: Any) -> Dict[str, Any]:
    """Determine assignment status based on assignment and submission data."""
    if not submission:
        return {
            "status": "not_submitted",
            "status_text": "Not submitted",
            "grade": None,
            "score": None,
            "graded_at": None,
            "late": False,
            "missing": True,
            "excused": False,
            "workflow_state": getattr(assignment, "workflow_state", None),
        }

    workflow_state = getattr(submission, "workflow_state", "unsubmitted")
    grade = getattr(submission, "grade", None)
    score = getattr(submission, "score", None)
    late = getattr(submission, "late", False)
    missing = getattr(submission, "missing", False)
    excused = getattr(submission, "excused", False)

    if excused:
        status = "excused"
        status_text = "Excused"
    elif grade and grade != "ungraded":
        status = "graded"
        status_text = f"Graded ({grade})"
    elif workflow_state == "submitted":
        status = "pending"
        status_text = "Pending grading"
    elif missing:
        status = "missing"
        status_text = "Missing"
    else:
        status = "not_submitted"
        status_text = "Not submitted"

    return {
        "status": status,
        "status_text": status_text,
        "grade": grade,
        "score": score,
        "graded_at": getattr(submission, "graded_at", None),
        "late": late,
        "missing": missing,
        "excused": excused,
        "workflow_state": workflow_state,
    }
