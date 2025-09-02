"""
Late days tracking endpoints.
Following FastAPI best practices for dependency injection and error handling.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List

from canvasapi import Canvas
from canvasapi.exceptions import ResourceDoesNotExist
from fastapi import APIRouter, Depends, HTTPException, status

from dependencies import SettingsDep, ThreadPoolDep
from models import AssignmentInfo, LateDaysRequest, LateDaysResponse, StudentLateDays

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["late-days"],
    responses={404: {"description": "Not found"}},
)


async def get_canvas_from_late_days_request(
    request: LateDaysRequest, settings: SettingsDep
) -> Canvas:
    """Convert late days request to Canvas client."""
    from dependencies import validate_canvas_credentials

    return await validate_canvas_credentials(
        str(request.base_url), request.api_token, settings
    )


def calculate_late_days(submitted_at: str, due_at: str) -> int:
    """Calculate the number of late days between submission and due date."""
    if not submitted_at or not due_at:
        return 0

    try:
        submitted_date = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
        due_date = datetime.fromisoformat(due_at.replace("Z", "+00:00"))

        if submitted_date <= due_date:
            return 0

        # Calculate days late (rounded up)
        time_diff = submitted_date - due_date
        return max(1, int(time_diff.total_seconds() / (24 * 3600)) + 1)
    except (ValueError, TypeError) as e:
        logger.warning(f"Error parsing dates: {e}")
        return 0


@router.post("/late-days", response_model=LateDaysResponse)
async def get_late_days_tracking(
    request: LateDaysRequest,
    settings: SettingsDep,
    thread_pool: ThreadPoolDep,
) -> LateDaysResponse:
    """
    Track late days for all students in a course.

    - **course_id**: Canvas course ID
    - **base_url**: Canvas instance base URL
    - **api_token**: Canvas API access token
    """
    try:
        logger.info(f"Processing late days request for course {request.course_id}")
        canvas = await get_canvas_from_late_days_request(request, settings)
        loop = asyncio.get_event_loop()

        # Get course
        logger.info(f"Fetching course data for course ID: {request.course_id}")
        course = await loop.run_in_executor(
            thread_pool, lambda: canvas.get_course(request.course_id)
        )
        logger.info(f"Successfully retrieved course: {course.name}")

        course_info = {
            "id": str(course.id),
            "name": course.name,
            "course_code": getattr(course, "course_code", None),
        }

        # Get all assignments with due dates
        def get_assignments() -> List[Any]:
            return [a for a in course.get_assignments() if getattr(a, "due_at", None)]

        assignments = await loop.run_in_executor(thread_pool, get_assignments)

        # Get all students in the course
        def get_students() -> List[Any]:
            return list(course.get_users(enrollment_type=["student"]))

        students = await loop.run_in_executor(thread_pool, get_students)

        # Process each assignment and collect late days data
        student_late_days = {}
        assignment_info = []

        for assignment in assignments:
            assignment_data = {
                "id": assignment.id,
                "name": assignment.name,
                "due_at": assignment.due_at,
                "points_possible": getattr(assignment, "points_possible", None),
            }
            assignment_info.append(assignment_data)

            # Get all submissions for this assignment
            def get_submissions() -> List[Any]:
                return list(assignment.get_submissions(include=["user"]))

            submissions = await loop.run_in_executor(thread_pool, get_submissions)

            # Process each submission
            for submission in submissions:
                if not hasattr(submission, "user") or not hasattr(
                    submission.user, "id"
                ):
                    continue

                user_id = submission.user.id
                user_name = getattr(submission.user, "name", f"Student {user_id}")

                # Initialize student data if not exists
                if user_id not in student_late_days:
                    student_late_days[user_id] = {
                        "student_id": user_id,
                        "student_name": user_name,
                        "student_email": getattr(submission.user, "email", ""),
                        "ta_group_name": None,  # Would need additional logic to determine TA group
                        "assignments": {},
                        "total_late_days": 0,
                    }

                # Calculate late days for this assignment
                submitted_at = getattr(submission, "submitted_at", None)
                if submitted_at:
                    late_days = calculate_late_days(submitted_at, assignment.due_at)
                else:
                    # Not submitted - could be considered "missing" rather than late
                    late_days = 0

                student_late_days[user_id]["assignments"][assignment.id] = late_days
                student_late_days[user_id]["total_late_days"] += late_days

        # Convert to proper Pydantic models
        students_list = [
            StudentLateDays(**student_data)
            for student_data in student_late_days.values()
        ]

        assignments_list = [
            AssignmentInfo(**assignment_data) for assignment_data in assignment_info
        ]

        return LateDaysResponse(
            students=students_list,
            assignments=assignments_list,
            course_info=course_info,
        )

    except HTTPException:
        raise
    except ResourceDoesNotExist as e:
        logger.error(f"Course {request.course_id} not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course {request.course_id} not found. Please check: 1) Course ID is correct, 2) API token has access to this course, 3) You have instructor/TA permissions",
        )
    except Exception as e:
        logger.error(
            f"Error processing late days data for course {request.course_id}: {str(e)}"
        )
        # Check if it's a Canvas API authentication error
        if "Invalid access token" in str(e) or "Unauthorized" in str(e):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Canvas API authentication failed. Please check your API token and Canvas base URL.",
            )
        elif "Not Found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Canvas resource not found. Please verify course ID {request.course_id} exists and you have access.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing late days data: {str(e)}",
            )
