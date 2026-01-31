"""
Canvas data synchronization module.
Fetches data from Canvas API and stores it in SQLite database.
"""

import os
import time
from typing import Any, Optional

from canvasapi import Canvas
from canvasapi.exceptions import CanvasException
from loguru import logger

import database as db


def get_canvas_client(api_url: Optional[str] = None, api_token: Optional[str] = None) -> Canvas:
    """Create a Canvas API client."""
    url = api_url or os.getenv("CANVAS_API_URL")
    token = api_token or os.getenv("CANVAS_API_TOKEN")

    if not url:
        raise ValueError("Canvas API URL not configured. Set CANVAS_API_URL environment variable.")
    if not token:
        raise ValueError("Canvas API token not configured. Set CANVAS_API_TOKEN environment variable.")

    return Canvas(url, token)


def fetch_available_courses(api_url: Optional[str] = None, api_token: Optional[str] = None) -> list[dict[str, Any]]:
    """Fetch list of available courses from Canvas API."""
    try:
        canvas = get_canvas_client(api_url, api_token)
        courses = []

        for course in canvas.get_courses(enrollment_type="ta", state=["available"]):
            courses.append({
                "id": str(course.id),
                "name": getattr(course, "name", f"Course {course.id}"),
                "code": getattr(course, "course_code", ""),
            })

        # Also try teacher enrollment
        for course in canvas.get_courses(enrollment_type="teacher", state=["available"]):
            if not any(c["id"] == str(course.id) for c in courses):
                courses.append({
                    "id": str(course.id),
                    "name": getattr(course, "name", f"Course {course.id}"),
                    "code": getattr(course, "course_code", ""),
                })

        logger.info(f"Found {len(courses)} available courses")
        return courses

    except CanvasException as e:
        logger.error(f"Canvas API error fetching courses: {e}")
        raise
    except Exception as e:
        logger.error(f"Error fetching courses: {e}")
        raise


def sync_course_data(
    course_id: str,
    api_url: Optional[str] = None,
    api_token: Optional[str] = None,
) -> dict[str, Any]:
    """
    Sync Canvas data for a course to the local SQLite database.

    Args:
        course_id: Canvas course ID to sync
        api_url: Canvas API URL (uses env var if not provided)
        api_token: Canvas API token (uses env var if not provided)

    Returns:
        Dictionary with sync results and statistics
    """
    # Initialize database
    db.init_db()

    # Create sync record
    sync_id = db.create_sync_record(course_id)
    logger.info(f"Starting sync for course {course_id} (sync_id: {sync_id})")

    try:
        # Create Canvas client
        canvas = get_canvas_client(api_url, api_token)
        course = canvas.get_course(course_id)
        course_name = getattr(course, "name", f"Course {course_id}")
        logger.info(f"Fetching data for course: {course_name}")

        # Clear existing data for this course
        db.clear_course_data(course_id)

        fetch_start = time.time()

        # Fetch assignments and submissions
        assignments = []
        submissions = []
        assignments_start = time.time()

        for assignment in course.get_assignments(per_page=100):
            assignments.append({
                "id": assignment.id,
                "name": assignment.name,
                "due_at": getattr(assignment, "due_at", None),
                "points_possible": getattr(assignment, "points_possible", None),
                "html_url": getattr(assignment, "html_url", None),
            })

            # Fetch submissions for this assignment
            for submission in assignment.get_submissions(include=["submission_history"]):
                submissions.append({
                    "id": submission.id,
                    "user_id": submission.user_id,
                    "assignment_id": assignment.id,
                    "submitted_at": getattr(submission, "submitted_at", None),
                    "workflow_state": submission.workflow_state,
                    "late": getattr(submission, "late", False),
                    "score": getattr(submission, "score", None),
                })

        logger.info(
            f"Assignments and submissions fetched in {time.time() - assignments_start:.2f}s "
            f"({len(assignments)} assignments, {len(submissions)} submissions)"
        )

        # Store assignments and submissions
        db.upsert_assignments(course_id, assignments)
        db.upsert_submissions(course_id, submissions)

        # Fetch users
        users_start = time.time()
        users = []
        for user in course.get_users(enrollment_type=["student"]):
            users.append({
                "id": user.id,
                "name": user.name,
                "email": getattr(user, "email", None),
            })
        logger.info(f"Users fetched in {time.time() - users_start:.2f}s ({len(users)} users)")
        db.upsert_users(course_id, users)

        # Fetch groups
        groups_start = time.time()
        groups = []
        for group in course.get_groups(per_page=100, include=["users"]):
            # Filter out project groups
            if "Term Project" in getattr(group, "name", ""):
                continue

            members = []
            for member in getattr(group, "users", []):
                member_id = member.get("id") if isinstance(member, dict) else getattr(member, "id", None)
                member_name = member.get("name") if isinstance(member, dict) else getattr(member, "name", None)

                if member_id:
                    members.append({
                        "id": member_id,
                        "user_id": member_id,
                        "name": member_name,
                    })

            groups.append({
                "id": group.id,
                "name": group.name,
                "members": members,
            })
        logger.info(f"Groups fetched in {time.time() - groups_start:.2f}s ({len(groups)} groups)")
        db.upsert_groups(course_id, groups)

        total_time = time.time() - fetch_start
        logger.info(f"Total sync time: {total_time:.2f}s")

        # Update sync record with success
        db.update_sync_record(
            sync_id,
            status="success",
            message=f"Synced course: {course_name}",
            assignments_count=len(assignments),
            submissions_count=len(submissions),
            users_count=len(users),
            groups_count=len(groups),
        )

        # Store course name in settings
        db.set_setting(f"course_name_{course_id}", course_name)

        return {
            "status": "success",
            "course_id": course_id,
            "course_name": course_name,
            "sync_id": sync_id,
            "stats": {
                "assignments": len(assignments),
                "submissions": len(submissions),
                "users": len(users),
                "groups": len(groups),
            },
            "duration_seconds": round(total_time, 2),
        }

    except CanvasException as e:
        error_msg = f"Canvas API error: {e}"
        logger.error(error_msg)
        db.update_sync_record(sync_id, status="failed", message=error_msg)
        raise

    except Exception as e:
        error_msg = f"Sync failed: {e}"
        logger.error(error_msg)
        db.update_sync_record(sync_id, status="failed", message=error_msg)
        raise


def sync_on_startup() -> Optional[dict[str, Any]]:
    """
    Sync Canvas data on application startup.
    Uses course ID from settings or environment variable.
    """
    db.init_db()

    # Get course ID from settings or environment
    course_id = db.get_setting("course_id") or os.getenv("CANVAS_COURSE_ID")

    if not course_id:
        logger.info("No course ID configured - skipping startup sync")
        return None

    # Check if Canvas credentials are available
    if not os.getenv("CANVAS_API_TOKEN"):
        logger.warning("Canvas API token not configured - skipping startup sync")
        return None

    if not os.getenv("CANVAS_API_URL"):
        logger.warning("Canvas API URL not configured - skipping startup sync")
        return None

    logger.info(f"Running startup sync for course {course_id}")

    try:
        result = sync_course_data(course_id)
        logger.info(f"Startup sync completed: {result['stats']}")
        return result
    except Exception as e:
        logger.error(f"Startup sync failed: {e}")
        return None
