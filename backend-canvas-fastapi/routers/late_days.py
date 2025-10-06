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

from dependencies import SettingsDep, ThreadPoolDep, resolve_credentials
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

    base_url, token = resolve_credentials(
        request.base_url, request.api_token, settings
    )
    return await validate_canvas_credentials(base_url, token, settings)


def calculate_late_days(submitted_at: str, due_at: str) -> int:
    """Calculate the number of late days between submission and due date."""
    if not submitted_at or not due_at:
        logger.debug(f"Missing dates: submitted_at={submitted_at}, due_at={due_at}")
        return 0

    try:
        # Handle various Canvas date formats
        submitted_str = submitted_at.replace("Z", "+00:00") if "Z" in submitted_at else submitted_at
        due_str = due_at.replace("Z", "+00:00") if "Z" in due_at else due_at

        submitted_date = datetime.fromisoformat(submitted_str)
        due_date = datetime.fromisoformat(due_str)

        logger.debug(f"Parsed dates: submitted={submitted_date}, due={due_date}")

        if submitted_date <= due_date:
            logger.debug(f"Submission was on time: {submitted_date} <= {due_date}")
            return 0

        # Calculate days late (rounded up)
        time_diff = submitted_date - due_date
        days_late = max(1, int(time_diff.total_seconds() / (24 * 3600)) + 1)
        logger.info(f"🔴 LATE CALCULATION: {days_late} days late (time_diff={time_diff}, submitted={submitted_date}, due={due_date})")
        return days_late
    except (ValueError, TypeError) as e:
        logger.warning(f"Error parsing dates: submitted_at='{submitted_at}', due_at='{due_at}', error={e}")
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
            """Get assignments with due dates using CanvasAPI best practices."""
            # Get all assignments with optimal pagination and includes
            all_assignments = list(course.get_assignments(
                per_page=100,  # CanvasAPI best practice
                include=["submission", "due_at"],  # Include submission data efficiently
            ))
            logger.info(f"Retrieved {len(all_assignments)} total assignments from Canvas")

            # Filter for assignments with due dates and log details
            assignments_with_due_dates = []
            for assignment in all_assignments:
                due_at = getattr(assignment, "due_at", None)
                if due_at:
                    assignments_with_due_dates.append(assignment)
                    logger.info(f"Assignment '{assignment.name}' (ID: {assignment.id}) has due date: {due_at}")
                else:
                    logger.debug(f"Assignment '{assignment.name}' (ID: {assignment.id}) has no due date, skipping")

            logger.info(f"Found {len(assignments_with_due_dates)} assignments with due dates")
            return assignments_with_due_dates

        assignments = await loop.run_in_executor(thread_pool, get_assignments)

        # Get all students in the course
        def get_students() -> List[Any]:
            """Get students using CanvasAPI best practices."""
            students_list = list(course.get_users(
                enrollment_type=["student"],
                enrollment_state=["active", "invited"],  # Only active/invited students
                per_page=100,  # CanvasAPI best practice
                include=["email", "sis_user_id"]  # Include useful student data
            ))
            logger.info(f"Retrieved {len(students_list)} students from Canvas")
            for student in students_list[:5]:  # Log first 5 students for debugging
                logger.debug(f"Student: {getattr(student, 'name', 'Unknown')} (ID: {student.id}, Email: {getattr(student, 'email', 'N/A')})")
            if len(students_list) > 5:
                logger.debug(f"... and {len(students_list) - 5} more students")
            return students_list

        students = await loop.run_in_executor(thread_pool, get_students)

        # Initialize all students first to ensure complete data
        logger.info(f"Initializing student data for {len(students)} students")
        student_late_days = {}
        for student in students:
            student_late_days[student.id] = {
                "student_id": student.id,
                "student_name": getattr(student, "name", f"Student {student.id}"),
                "student_email": getattr(student, "email", ""),
                "ta_group_name": None,  # Would need additional logic to determine TA group
                "assignments": {},
                "total_late_days": 0,
            }

        # Process each assignment and collect late days data
        assignment_info = []

        for assignment in assignments:
            logger.info(f"Processing assignment: {assignment.name} (ID: {assignment.id})")
            assignment_data = {
                "id": assignment.id,
                "name": assignment.name,
                "due_at": assignment.due_at,
                "points_possible": getattr(assignment, "points_possible", None),
            }
            assignment_info.append(assignment_data)

            # Get all submissions for this assignment (both submitted and not submitted)
            def get_submissions() -> List[Any]:
                """Get all submissions using CanvasAPI best practices."""
                submissions_list = list(assignment.get_submissions(
                    include=["user", "submission_history"],  # Include comprehensive data
                    per_page=100,  # CanvasAPI best practice
                    # Remove workflow_state filter to get all submissions (submitted and unsubmitted)
                ))
                logger.info(f"Canvas API returned {len(submissions_list)} submission records for assignment {assignment.name}")

                # Log submission states for debugging
                submission_states = {}
                submitted_count = 0
                for sub in submissions_list:
                    state = getattr(sub, "workflow_state", "unknown")
                    submitted_at = getattr(sub, "submitted_at", None)
                    submission_states[state] = submission_states.get(state, 0) + 1
                    if submitted_at:
                        submitted_count += 1
                        if submitted_count <= 3:  # Log first 3 submitted assignments
                            logger.info(f"Sample submission: student_id={getattr(sub, 'user_id', 'N/A')}, state={state}, submitted_at={submitted_at}")

                logger.info(f"Submission states: {submission_states}")
                logger.info(f"Submissions with submitted_at date: {submitted_count}")
                return submissions_list

            submissions = await loop.run_in_executor(thread_pool, get_submissions)
            logger.info(f"Processing {len(submissions)} submissions for assignment {assignment.name}")

            # Initialize all students for this assignment with 0 late days
            for student_id in student_late_days:
                student_late_days[student_id]["assignments"][assignment.id] = 0

            # Process each submission
            processed_submissions = 0
            late_submissions_found = 0
            for submission in submissions:
                processed_submissions += 1

                if not hasattr(submission, "user") or not hasattr(
                    submission.user, "id"
                ):
                    logger.debug(f"Submission {processed_submissions}: No user data, skipping")
                    continue

                user_id = submission.user.id

                # Only process if this user is in our student list
                if user_id not in student_late_days:
                    logger.debug(f"Submission {processed_submissions}: User {user_id} not in student list, skipping")
                    continue

                # Calculate late days for this assignment
                submitted_at = getattr(submission, "submitted_at", None)
                workflow_state = getattr(submission, "workflow_state", None)

                # Debug logging for submission details
                logger.debug(f"Processing submission {processed_submissions} for student {user_id}, assignment {assignment.id}")
                logger.debug(f"  Submitted at: {submitted_at}")
                logger.debug(f"  Due at: {assignment.due_at}")
                logger.debug(f"  Workflow state: {workflow_state}")

                # Canvas workflow states can include: submitted, unsubmitted, graded, pending_review
                # We want to calculate late days for any submission that has a submitted_at date
                if submitted_at:
                    late_days = calculate_late_days(submitted_at, assignment.due_at)
                    if late_days > 0:
                        late_submissions_found += 1
                        logger.warning(f"🔴 LATE SUBMISSION FOUND: Student {user_id} submitted assignment {assignment.id} {late_days} days late (submitted: {submitted_at}, due: {assignment.due_at}, workflow_state: {workflow_state})")
                    else:
                        logger.info(f"✅ On-time submission: Student {user_id} submitted assignment {assignment.id} on time (submitted: {submitted_at}, due: {assignment.due_at}, workflow_state: {workflow_state})")
                else:
                    # Not submitted - 0 late days
                    late_days = 0
                    logger.debug(f"⚪ No submission: Student {user_id} assignment {assignment.id} (workflow_state={workflow_state})")

                student_late_days[user_id]["assignments"][assignment.id] = late_days

            logger.info(f"Assignment {assignment.name} processing complete: {processed_submissions} submissions processed, {late_submissions_found} late submissions found")

        # Calculate total late days for each student
        for student_data in student_late_days.values():
            student_data["total_late_days"] = sum(student_data["assignments"].values())

        # Convert to proper Pydantic models
        students_list = [
            StudentLateDays(**student_data)
            for student_data in student_late_days.values()
        ]

        assignments_list = [
            AssignmentInfo(**assignment_data) for assignment_data in assignment_info
        ]

        logger.info(f"Late days processing complete: {len(students_list)} students, {len(assignments_list)} assignments")

        # Log summary statistics for debugging
        total_late_days = sum(s.total_late_days for s in students_list)
        students_with_late_days = sum(1 for s in students_list if s.total_late_days > 0)
        logger.info(f"Late days summary: {students_with_late_days}/{len(students_list)} students have late days, total late days: {total_late_days}")

        response = LateDaysResponse(
            students=students_list,
            assignments=assignments_list,
            course_info=course_info,
        )

        # Additional validation to catch empty response issues
        if not students_list:
            logger.warning("No students found in late days response - check course enrollment")
        if not assignments_list:
            logger.warning("No assignments with due dates found - check assignment setup")

        return response

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
