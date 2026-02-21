"""
Canvas data synchronization module.
Fetches data from Canvas API and stores it in SQLite database.
"""

import os
import time
from datetime import UTC, datetime
from typing import Any

from canvasapi import Canvas
from canvasapi.exceptions import CanvasException
from loguru import logger

import database as db


def get_canvas_client(
    api_url: str | None = None, api_token: str | None = None
) -> Canvas:
    """Create a Canvas API client."""
    url = api_url or os.getenv("CANVAS_API_URL")
    token = api_token or os.getenv("CANVAS_API_TOKEN")

    if not url:
        raise ValueError(
            "Canvas API URL not configured. Set CANVAS_API_URL environment variable."
        )
    if not token:
        raise ValueError(
            "Canvas API token not configured. Set CANVAS_API_TOKEN environment variable."  # noqa: E501
        )

    return Canvas(url, token)


def post_submission_comment(
    course_id: str,
    assignment_id: int,
    user_id: int,
    comment_text: str,
    max_retries: int = 3,
) -> dict[str, Any]:
    """Post a comment to a student submission via Canvas API with retry logic.

    Retries only on 429 (rate limit) errors with exponential backoff.
    Raises immediately for other Canvas errors (401, 403, 404).

    Args:
        course_id: Canvas course ID
        assignment_id: Canvas assignment ID
        user_id: Canvas user ID of the student
        comment_text: Text to post as a submission comment
        max_retries: Maximum number of retry attempts for 429 errors (default: 3)

    Returns:
        Dictionary with status, canvas_comment_id, user_id, and posted_at.

    Raises:
        ValueError: If submission not found (404)
        CanvasException: For other Canvas API errors
    """
    canvas = get_canvas_client()
    course = canvas.get_course(course_id)
    assignment = course.get_assignment(assignment_id)

    base_delay = 1.0

    for attempt in range(max_retries + 1):
        try:
            submission = assignment.get_submission(user_id)
            result = submission.edit(comment={"text_comment": comment_text})
            posted_at = datetime.now(UTC).isoformat()
            canvas_comment_id = getattr(result, "id", None)
            logger.info(
                f"Posted comment to course={course_id}, assignment={assignment_id}, "
                f"user={user_id}, comment_id={canvas_comment_id}"
            )
            return {
                "status": "success",
                "canvas_comment_id": canvas_comment_id,
                "user_id": user_id,
                "posted_at": posted_at,
            }
        except CanvasException as e:
            error_str = str(e)
            if "404" in error_str:
                raise ValueError(
                    f"Submission not found for user {user_id} "
                    f"on assignment {assignment_id}"
                ) from e
            if "429" in error_str and attempt < max_retries:
                delay = base_delay * (2**attempt)
                logger.warning(
                    f"Rate limited (429) posting to user={user_id}, "
                    f"attempt={attempt + 1}/{max_retries + 1}. "
                    f"Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
                continue
            # Non-429 Canvas errors or exhausted retries — raise immediately
            if "429" in error_str:
                logger.error(
                    f"Rate limit retries exhausted for user={user_id}, "
                    f"assignment={assignment_id}"
                )
            else:
                logger.error(
                    f"Canvas API error posting comment to user={user_id}, "
                    f"assignment={assignment_id}: {e}"
                )
            raise

    # Should not reach here — loop always returns or raises
    raise RuntimeError("Unexpected exit from retry loop")  # pragma: no cover


def fetch_available_courses(
    api_url: str | None = None, api_token: str | None = None
) -> list[dict[str, Any]]:
    """Fetch list of available courses from Canvas API."""
    try:
        canvas = get_canvas_client(api_url, api_token)
        courses = []
        seen_ids = set()

        for course in canvas.get_courses(enrollment_type="ta", state=["available"]):
            course_id = str(course.id)
            if course_id not in seen_ids:
                seen_ids.add(course_id)
                term_obj = getattr(course, "enrollment_term", None)
                courses.append(
                    {
                        "id": course_id,
                        "name": getattr(course, "name", f"Course {course.id}"),
                        "code": getattr(course, "course_code", ""),
                        "term": getattr(term_obj, "name", None)
                        or getattr(course, "term_name", None),
                    }
                )

        # Also try teacher enrollment
        for course in canvas.get_courses(
            enrollment_type="teacher", state=["available"]
        ):
            course_id = str(course.id)
            if course_id not in seen_ids:
                seen_ids.add(course_id)
                term_obj = getattr(course, "enrollment_term", None)
                courses.append(
                    {
                        "id": course_id,
                        "name": getattr(course, "name", f"Course {course.id}"),
                        "code": getattr(course, "course_code", ""),
                        "term": getattr(term_obj, "name", None)
                        or getattr(course, "term_name", None),
                    }
                )

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
    api_url: str | None = None,
    api_token: str | None = None,
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
    # Create sync record
    sync_id = db.create_sync_record(course_id)
    logger.info(f"Starting sync for course {course_id} (sync_id: {sync_id})")

    try:
        # Create Canvas client
        canvas = get_canvas_client(api_url, api_token)
        course = canvas.get_course(course_id)
        course_name = getattr(course, "name", f"Course {course_id}")
        _term_obj = getattr(course, "enrollment_term", None)
        course_term = getattr(_term_obj, "name", None) or getattr(
            course, "term_name", None
        )
        logger.info(f"Fetching data for course: {course_name}")

        fetch_start = time.time()

        # Fetch assignments (keep both objects and data)
        assignments = []
        assignment_objects = []
        assignments_start = time.time()

        for assignment in course.get_assignments(per_page=100):
            assignment_objects.append(assignment)
            assignments.append(
                {
                    "id": assignment.id,
                    "name": assignment.name,
                    "due_at": getattr(assignment, "due_at", None),
                    "points_possible": getattr(assignment, "points_possible", None),
                    "html_url": getattr(assignment, "html_url", None),
                    "has_peer_reviews": getattr(assignment, "peer_reviews", False),
                }
            )

        logger.info(
            f"Assignments fetched in {time.time() - assignments_start:.2f}s ({len(assignments)} assignments)"  # noqa: E501
        )

        # Fetch users
        users_start = time.time()
        users = []
        for user in course.get_users(enrollment_type=["student"]):
            users.append(
                {
                    "id": user.id,
                    "name": user.name,
                    "email": getattr(user, "email", None),
                }
            )
        logger.info(
            f"Users fetched in {time.time() - users_start:.2f}s ({len(users)} users)"
        )

        # Fetch groups
        groups_start = time.time()
        groups = []
        for group in course.get_groups(per_page=100, include=["users"]):
            # Filter out project groups
            if "Term Project" in getattr(group, "name", ""):
                continue

            members = []
            for member in getattr(group, "users", []):
                member_id = (
                    member.get("id")
                    if isinstance(member, dict)
                    else getattr(member, "id", None)
                )
                member_name = (
                    member.get("name")
                    if isinstance(member, dict)
                    else getattr(member, "name", None)
                )

                if member_id:
                    members.append(
                        {
                            "id": member_id,
                            "user_id": member_id,
                            "name": member_name,
                        }
                    )

            groups.append(
                {
                    "id": group.id,
                    "name": group.name,
                    "members": members,
                }
            )
        logger.info(
            f"Groups fetched in {time.time() - groups_start:.2f}s ({len(groups)} groups)"  # noqa: E501
        )

        # Use transaction to write all data atomically
        total_submissions = 0
        dropped_count = 0
        with db.get_db_transaction() as conn:
            # Capture enrollment state before sync modifies anything
            before_enrollment = db.get_enrollment_state_snapshot(course_id, conn)

            # Step 1: Mark all existing users as pending verification
            pending_count = db.mark_all_users_pending(course_id, conn)
            logger.info(f"Marked {pending_count} existing users as pending_check")

            # Step 2: Clear refreshable data (assignments, groups, peer reviews)
            # Users and submissions are preserved
            db.clear_refreshable_data(course_id, conn)

            # Step 3: Upsert data (assignments, users, groups)
            db.upsert_assignments(course_id, assignments, conn)
            db.upsert_users(course_id, users, conn)  # Sets enrollment_status='active'
            db.upsert_groups(course_id, groups, conn)

            # Fetch and store submissions per-assignment to reduce memory usage
            submissions_start = time.time()
            for assignment_obj in assignment_objects:
                assignment_submissions = []
                for submission in assignment_obj.get_submissions(
                    include=["submission_history"]
                ):
                    assignment_submissions.append(
                        {
                            "id": submission.id,
                            "user_id": submission.user_id,
                            "assignment_id": assignment_obj.id,
                            "submitted_at": getattr(submission, "submitted_at", None),
                            "workflow_state": submission.workflow_state,
                            "late": getattr(submission, "late", False),
                            "score": getattr(submission, "score", None),
                        }
                    )

                # Write submissions for this assignment
                if assignment_submissions:
                    db.upsert_submissions(course_id, assignment_submissions, conn)
                    total_submissions += len(assignment_submissions)

            logger.info(
                f"Submissions fetched and stored in {time.time() - submissions_start:.2f}s ({total_submissions} submissions)"  # noqa: E501
            )

            # Fetch and store peer reviews for assignments that have them
            peer_reviews_start = time.time()
            total_peer_reviews = 0
            total_peer_review_comments = 0

            peer_review_assignments = [
                (obj, data)
                for obj, data in zip(assignment_objects, assignments, strict=True)
                if data.get("has_peer_reviews", False)
            ]

            if peer_review_assignments:
                logger.info(
                    f"Found {len(peer_review_assignments)} assignments "
                    "with peer reviews"
                )

                for assignment_obj, assignment_data in peer_review_assignments:
                    try:
                        # Fetch peer reviews
                        peer_reviews = []
                        for pr in assignment_obj.get_peer_reviews():
                            peer_reviews.append(
                                {
                                    "id": pr.id,
                                    "assignment_id": assignment_obj.id,
                                    "user_id": pr.user_id,
                                    "assessor_id": pr.assessor_id,
                                    "asset_id": getattr(pr, "asset_id", None),
                                    "asset_type": getattr(pr, "asset_type", None),
                                    "workflow_state": getattr(
                                        pr, "workflow_state", None
                                    ),
                                }
                            )

                        if peer_reviews:
                            db.upsert_peer_reviews(course_id, peer_reviews, conn)
                            total_peer_reviews += len(peer_reviews)

                        # Fetch submission comments for peer reviews
                        comments = []
                        for submission in assignment_obj.get_submissions(
                            include=["submission_comments"]
                        ):
                            submission_comments = getattr(
                                submission, "submission_comments", []
                            )
                            for comment in submission_comments:
                                comments.append(
                                    {
                                        "id": comment.get("id"),
                                        "submission_id": submission.id,
                                        "author_id": comment.get("author_id"),
                                        "comment": comment.get("comment"),
                                        "created_at": comment.get("created_at"),
                                    }
                                )

                        if comments:
                            db.upsert_peer_review_comments(course_id, comments, conn)
                            total_peer_review_comments += len(comments)

                    except Exception as e:
                        logger.warning(
                            f"Failed to fetch peer reviews for assignment {assignment_data['name']}: {e}"  # noqa: E501
                        )
                        continue

                logger.info(
                    f"Peer reviews fetched in {time.time() - peer_reviews_start:.2f}s "
                    f"({total_peer_reviews} reviews, {total_peer_review_comments} comments)"  # noqa: E501
                )

            # Step 6: Clean up orphaned submissions (assignments removed from Canvas)
            db.cleanup_orphaned_submissions(course_id, conn)

            # Step 7: Mark remaining pending users as dropped
            dropped_count = db.mark_dropped_users(course_id, conn)
            if dropped_count > 0:
                logger.info(
                    f"Marked {dropped_count} users as dropped for course {course_id}"
                )

            # Step 8: Record enrollment events and snapshot
            event_summary = db.record_enrollment_events(
                course_id, sync_id, before_enrollment, conn
            )
            active_final, dropped_final = db.get_enrollment_counts_transactional(
                course_id, conn
            )
            db.record_enrollment_snapshot(
                course_id,
                sync_id,
                active_final,
                dropped_final,
                event_summary["newly_dropped"],
                event_summary["newly_enrolled"],
                conn,
            )
            logger.info(
                f"Recorded enrollment snapshot: {active_final} active, "
                f"{dropped_final} dropped "
                f"({event_summary['newly_dropped']} newly dropped, "
                f"{event_summary['newly_enrolled']} newly enrolled)"
            )

        total_time = time.time() - fetch_start
        logger.info(f"Total sync time: {total_time:.2f}s")

        # Update sync record with success
        db.update_sync_record(
            sync_id,
            status="success",
            message=f"Synced course: {course_name}",
            assignments_count=len(assignments),
            submissions_count=total_submissions,
            users_count=len(users),
            groups_count=len(groups),
            dropped_users_count=dropped_count,
        )

        # Store course name and term in settings
        db.set_setting(f"course_name_{course_id}", course_name)
        if course_term:
            db.set_setting(f"course_term_{course_id}", course_term)

        return {
            "status": "success",
            "course_id": course_id,
            "course_name": course_name,
            "course_term": course_term,
            "sync_id": sync_id,
            "stats": {
                "assignments": len(assignments),
                "submissions": total_submissions,
                "users": len(users),
                "groups": len(groups),
                "peer_reviews": total_peer_reviews,
                "peer_review_comments": total_peer_review_comments,
                "dropped_users": dropped_count,
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


def sync_on_startup() -> dict[str, Any] | None:
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
