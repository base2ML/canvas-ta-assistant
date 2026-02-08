"""
Canvas TA Dashboard FastAPI Application
Local deployment with SQLite data storage
"""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from dateutil import parser as dateutil_parser
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

import canvas_sync
import database as db


# Configure loguru
logger.add("logs/app.log", rotation="500 MB", retention="10 days", level="INFO")

# Constants
APP_VERSION = "5.0.0"

# Environment variables
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
CANVAS_API_URL = os.getenv("CANVAS_API_URL", "")
CANVAS_COURSE_ID = os.getenv("CANVAS_COURSE_ID", "")


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Handle application startup and shutdown."""
    # Startup
    logger.info("Starting Canvas TA Dashboard...")
    db.init_db()

    # Run startup sync if course is configured
    try:
        canvas_sync.sync_on_startup()
    except Exception as e:
        logger.warning(f"Startup sync skipped or failed: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Canvas TA Dashboard...")


# FastAPI app
app = FastAPI(
    title="Canvas TA Dashboard API",
    description="Local Canvas TA Dashboard with SQLite data storage",
    version=APP_VERSION,
    lifespan=lifespan,
)

# Rate Limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware - permissive for local development
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Pydantic models
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    environment: str
    database: str
    canvas_configured: bool


class SettingsResponse(BaseModel):
    course_id: str | None
    course_name: str | None
    canvas_api_url: str
    last_sync: dict[str, Any] | None


class SettingsUpdateRequest(BaseModel):
    course_id: str


class SyncResponse(BaseModel):
    status: str
    message: str
    course_id: str | None
    stats: dict[str, int] | None
    duration_seconds: float | None


class SubmissionStatusMetrics(BaseModel):
    on_time: int
    late: int
    missing: int
    on_time_percentage: float
    late_percentage: float
    missing_percentage: float
    total_expected: int


class PeerReviewEvent(BaseModel):
    peer_review_id: int
    assignment_id: int
    assignment_name: str
    reviewer_id: int
    reviewer_name: str
    assessed_id: int
    assessed_name: str
    submission_id: int | None
    comment_timestamp: str | None
    status: str  # "on_time", "late", "missing"
    hours_difference: float | None


class PeerReviewSummary(BaseModel):
    total_reviews: int
    on_time: int
    late: int
    missing: int
    on_time_percentage: float
    late_percentage: float
    missing_percentage: float


class PenalizedReviewer(BaseModel):
    reviewer_id: int
    reviewer_name: str
    late_count: int
    missing_count: int
    penalty_points: int
    canvas_comment: str


class PeerReviewAnalysis(BaseModel):
    assignment_id: int
    assignment_name: str
    deadline: str
    penalty_per_review: int
    total_score: int
    summary: PeerReviewSummary
    events: list[PeerReviewEvent]
    penalized_reviewers: list[PenalizedReviewer]


# Health check endpoints
@app.get("/health")
async def simple_health_check():
    """Simple health check endpoint for Docker health checks."""
    return {"status": "healthy", "timestamp": datetime.now(UTC).isoformat()}


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check endpoint with service status."""
    # Check database
    db_status = "healthy"
    try:
        db.get_all_settings()
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        db_status = "unhealthy"

    # Check Canvas configuration
    canvas_configured = bool(CANVAS_API_URL and os.getenv("CANVAS_API_TOKEN"))

    # Set overall status based on database health
    overall_status = "healthy" if db_status == "healthy" else "degraded"

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(UTC).isoformat(),
        version=APP_VERSION,
        environment=ENVIRONMENT,
        database=db_status,
        canvas_configured=canvas_configured,
    )


# Settings endpoints
@app.get("/api/settings", response_model=SettingsResponse)
async def get_settings():
    """Get current application settings."""
    course_id = db.get_setting("course_id") or CANVAS_COURSE_ID
    course_name = db.get_setting(f"course_name_{course_id}") if course_id else None
    last_sync = db.get_last_sync(course_id) if course_id else None

    return SettingsResponse(
        course_id=course_id or None,
        course_name=course_name,
        canvas_api_url=CANVAS_API_URL,
        last_sync=last_sync,
    )


@app.put("/api/settings")
async def update_settings(settings: SettingsUpdateRequest) -> dict[str, Any]:
    """Update application settings."""
    db.set_setting("course_id", settings.course_id)
    logger.info(f"Course ID updated to: {settings.course_id}")

    return {
        "status": "success",
        "message": "Settings updated",
        "course_id": settings.course_id,
    }


@app.get("/api/settings/courses")
async def get_available_courses() -> dict[str, Any]:
    """Get list of available courses from Canvas API."""
    try:
        courses = await asyncio.to_thread(canvas_sync.fetch_available_courses)
        return {"courses": courses, "total": len(courses)}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error fetching courses: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch courses from Canvas API",
        ) from e


# Sync endpoints
@app.post("/api/canvas/sync", response_model=SyncResponse)
async def trigger_sync(course_id: str | None = None) -> SyncResponse:
    """Trigger Canvas data sync."""
    # Use provided course_id or get from settings
    sync_course_id = course_id or db.get_setting("course_id") or CANVAS_COURSE_ID

    if not sync_course_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No course ID configured. Set course ID in settings first.",
        )

    try:
        result = await asyncio.to_thread(canvas_sync.sync_course_data, sync_course_id)

        # Update settings with new course ID if different
        if sync_course_id != db.get_setting("course_id"):
            db.set_setting("course_id", sync_course_id)

        return SyncResponse(
            status="success",
            message=f"Synced course: {result.get('course_name', sync_course_id)}",
            course_id=sync_course_id,
            stats=result.get("stats"),
            duration_seconds=result.get("duration_seconds"),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Canvas data sync failed",
        ) from e


@app.get("/api/canvas/sync/status")
async def get_sync_status(course_id: str | None = None) -> dict[str, Any]:
    """Get last sync status."""
    sync_course_id = course_id or db.get_setting("course_id") or CANVAS_COURSE_ID
    last_sync = db.get_last_sync(sync_course_id) if sync_course_id else None
    history = db.get_sync_history(sync_course_id, limit=5) if sync_course_id else []

    return {
        "course_id": sync_course_id,
        "last_sync": last_sync,
        "history": history,
    }


# Canvas data endpoints
@app.get("/api/canvas/courses")
async def get_courses() -> dict[str, Any]:
    """Get list of synced courses from local database."""
    courses = db.get_courses()

    course_data = []
    for course_id in courses:
        course_name = db.get_setting(f"course_name_{course_id}")
        last_sync = db.get_last_sync(course_id)
        course_data.append(
            {
                "id": course_id,
                "name": course_name or f"Course {course_id}",
                "last_updated": last_sync.get("completed_at") if last_sync else None,
            }
        )

    return {
        "courses": course_data,
        "total": len(course_data),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/api/canvas/data/{course_id}")
async def get_canvas_data(course_id: str) -> dict[str, Any]:
    """Get complete Canvas data for a course."""
    assignments = db.get_assignments(course_id)
    submissions = db.get_submissions(course_id)
    users = db.get_users(course_id)
    groups = db.get_groups(course_id)

    if not assignments and not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for course {course_id}. Try syncing first.",
        )

    return {
        "course_id": course_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "assignments": assignments,
        "submissions": submissions,
        "users": users,
        "groups": groups,
        "enrollments": [],
    }


@app.get("/api/canvas/assignments/{course_id}")
async def get_assignments(course_id: str) -> dict[str, Any]:
    """Get assignments for a course."""
    assignments = db.get_assignments(course_id)
    return {"assignments": assignments, "total": len(assignments)}


@app.get("/api/canvas/submissions/{course_id}")
async def get_submissions(
    course_id: str, assignment_id: int | None = None
) -> dict[str, Any]:
    """Get submissions for a course."""
    submissions = db.get_submissions(course_id, assignment_id)
    return {"submissions": submissions, "total": len(submissions)}


@app.get("/api/canvas/users/{course_id}")
async def get_users(course_id: str) -> dict[str, Any]:
    """Get users for a course."""
    users = db.get_users(course_id)
    return {"users": users, "total": len(users)}


@app.get("/api/canvas/groups/{course_id}")
async def get_groups(course_id: str) -> dict[str, Any]:
    """Get groups for a course."""
    groups = db.get_groups(course_id)
    return {"groups": groups, "total": len(groups)}


# Dashboard endpoints
def classify_submission_status(submission: dict, assignment: dict) -> str:
    """Classify submission as on_time, late, or missing."""
    workflow_state = submission.get("workflow_state", "")
    submitted_at = submission.get("submitted_at")
    due_at = assignment.get("due_at")
    late = submission.get("late", False)

    # Missing: not submitted or pending review
    if workflow_state in ["unsubmitted", "pending_review"] or not submitted_at:
        return "missing"

    # Late: explicit late flag or submitted after due date
    if late:
        return "late"

    if submitted_at and due_at:
        try:
            submitted_datetime = dateutil_parser.parse(submitted_at)
            due_datetime = dateutil_parser.parse(due_at)
            if submitted_datetime > due_datetime:
                return "late"
        except Exception as e:
            logger.debug(f"Error parsing dates: {e}")

    return "on_time"


def _build_user_to_ta_group_map(groups: list[dict]) -> dict[int, str]:
    """Build mapping of user IDs to TA group names."""
    user_to_ta_group = {}
    for group in groups:
        group_name = group.get("name")
        for member in group.get("members", []):
            user_id = member.get("user_id") or member.get("id")
            if user_id:
                user_to_ta_group[user_id] = group_name
    return user_to_ta_group


def _build_submission_lookup(submissions: list[dict]) -> dict[tuple[int, int], dict]:
    """Build lookup dictionary for submissions by (user_id, assignment_id)."""
    submission_lookup = {}
    for sub in submissions:
        key = (sub.get("user_id"), sub.get("assignment_id"))
        submission_lookup[key] = sub
    return submission_lookup


def _calculate_percentages(
    on_time: int, late: int, missing: int, total: int
) -> dict[str, float]:
    """Calculate percentages for submission metrics."""
    if total > 0:
        return {
            "on_time_percentage": on_time / total * 100,
            "late_percentage": late / total * 100,
            "missing_percentage": missing / total * 100,
        }
    return {
        "on_time_percentage": 0,
        "late_percentage": 0,
        "missing_percentage": 0,
    }


def calculate_submission_status_metrics(
    assignments: list[dict],
    submissions: list[dict],
    users: list[dict],
    groups: list[dict],
    assignment_filter: str | None = None,
    ta_group_filter: str | None = None,
) -> dict[str, Any]:
    """Calculate comprehensive submission status metrics."""
    # Filter assignments if specified
    if assignment_filter and assignment_filter != "all":
        assignments = [a for a in assignments if str(a.get("id")) == assignment_filter]

    # Pre-compute user to TA group mapping
    user_to_ta_group = _build_user_to_ta_group_map(groups)

    # Filter users by TA group if specified
    if ta_group_filter and ta_group_filter != "all":
        users = [
            u for u in users if user_to_ta_group.get(u.get("id")) == ta_group_filter
        ]

    # Create submission lookup
    submission_lookup = _build_submission_lookup(submissions)

    # Initialize counters
    overall_on_time = 0
    overall_late = 0
    overall_missing = 0

    # Metrics by assignment
    assignment_metrics = {}

    # Metrics by TA
    ta_metrics = {}
    for group in groups:
        group_name = group.get("name")
        if (
            ta_group_filter
            and ta_group_filter != "all"
            and group_name != ta_group_filter
        ):
            continue

        ta_metrics[group_name] = {
            "ta_name": group_name,
            "student_count": 0,
            "on_time": 0,
            "late": 0,
            "missing": 0,
        }

    # Calculate metrics
    for assignment in assignments:
        assignment_id = assignment.get("id")
        assignment_name = assignment.get("name", "Unnamed Assignment")
        due_date = assignment.get("due_at")

        assignment_on_time = 0
        assignment_late = 0
        assignment_missing = 0

        for user in users:
            user_id = user.get("id")
            key = (user_id, assignment_id)

            submission = submission_lookup.get(
                key,
                {
                    "workflow_state": "unsubmitted",
                    "user_id": user_id,
                    "assignment_id": assignment_id,
                },
            )

            status = classify_submission_status(submission, assignment)

            if status == "on_time":
                overall_on_time += 1
                assignment_on_time += 1
            elif status == "late":
                overall_late += 1
                assignment_late += 1
            else:
                overall_missing += 1
                assignment_missing += 1

            # Update TA metrics
            user_ta_group = user_to_ta_group.get(user_id)
            if user_ta_group and user_ta_group in ta_metrics:
                if status == "on_time":
                    ta_metrics[user_ta_group]["on_time"] += 1
                elif status == "late":
                    ta_metrics[user_ta_group]["late"] += 1
                else:
                    ta_metrics[user_ta_group]["missing"] += 1

        # Calculate assignment percentages
        total_assignment_submissions = len(users)
        percentages = _calculate_percentages(
            assignment_on_time,
            assignment_late,
            assignment_missing,
            total_assignment_submissions,
        )
        assignment_metrics[str(assignment_id)] = {
            "assignment_id": str(assignment_id),
            "assignment_name": assignment_name,
            "due_date": due_date,
            "metrics": {
                "on_time": assignment_on_time,
                "late": assignment_late,
                "missing": assignment_missing,
                **percentages,
                "total_expected": total_assignment_submissions,
            },
        }

    # Fix student counts
    for user in users:
        user_id = user.get("id")
        user_ta_group = user_to_ta_group.get(user_id)
        if user_ta_group and user_ta_group in ta_metrics:
            ta_metrics[user_ta_group]["student_count"] += 1

    # Calculate overall percentages
    total_expected = len(assignments) * len(users)
    overall_percentages = _calculate_percentages(
        overall_on_time, overall_late, overall_missing, total_expected
    )

    # Calculate TA percentages
    for metrics in ta_metrics.values():
        total = metrics["on_time"] + metrics["late"] + metrics["missing"]
        ta_percentages = _calculate_percentages(
            metrics["on_time"], metrics["late"], metrics["missing"], total
        )
        metrics.update(ta_percentages)

    return {
        "overall_metrics": {
            "on_time": overall_on_time,
            "late": overall_late,
            "missing": overall_missing,
            **overall_percentages,
            "total_expected": total_expected,
        },
        "by_assignment": list(assignment_metrics.values()),
        "by_ta": list(ta_metrics.values()),
    }


@app.get("/api/dashboard/submission-status/{course_id}")
async def get_submission_status_metrics(
    course_id: str,
    assignment_id: str | None = None,
    ta_group: str | None = None,
) -> dict[str, Any]:
    """Get submission status metrics (on_time, late, missing)."""
    try:
        assignments = db.get_assignments(course_id)
        submissions = db.get_submissions(course_id)
        users = db.get_users(course_id)
        groups = db.get_groups(course_id)

        if not assignments and not users:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for course {course_id}",
            )

        metrics = calculate_submission_status_metrics(
            assignments=assignments,
            submissions=submissions,
            users=users,
            groups=groups,
            assignment_filter=assignment_id,
            ta_group_filter=ta_group,
        )

        return metrics

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating submission status metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculating metrics",
        ) from e


@app.get("/api/dashboard/ta-grading/{course_id}")
async def get_ta_grading_data(course_id: str) -> dict[str, Any]:
    """Get TA grading dashboard data."""
    assignments = db.get_assignments(course_id)
    submissions = db.get_submissions(course_id)
    users = db.get_users(course_id)

    # Create lookup dictionaries
    assignment_dict = {str(a["id"]): a for a in assignments}
    user_dict = {str(u["id"]): u for u in users}

    # Process submissions
    ungraded_submissions = []
    ta_workload = {}

    for submission in submissions:
        if submission.get("workflow_state") == "graded":
            continue

        assignment_id = str(submission.get("assignment_id", ""))
        user_id = str(submission.get("user_id", ""))

        assignment = assignment_dict.get(assignment_id)
        student = user_dict.get(user_id)

        if assignment and student:
            ungraded_item = {
                "assignment_id": assignment_id,
                "assignment_name": assignment["name"],
                "student_id": user_id,
                "student_name": student["name"],
                "submitted_at": submission.get("submitted_at"),
                "due_date": assignment.get("due_at"),
                "points_possible": assignment.get("points_possible"),
            }

            ungraded_submissions.append(ungraded_item)

            ta_name = "Unassigned"
            if ta_name not in ta_workload:
                ta_workload[ta_name] = 0
            ta_workload[ta_name] += 1

    return {
        "ungraded_submissions": ungraded_submissions,
        "ta_workload": ta_workload,
        "total_ungraded": len(ungraded_submissions),
        "last_updated": datetime.now(UTC).isoformat(),
    }


@app.get("/api/dashboard/late-days/{course_id}")
async def get_late_days_data(course_id: str) -> dict[str, Any]:
    """Calculate late days for all students in a course."""
    try:
        assignments = db.get_assignments(course_id)
        submissions = db.get_submissions(course_id)
        users = db.get_users(course_id)
        groups = db.get_groups(course_id)

        # Create user to TA group mapping
        user_to_ta_group = {}
        for group in groups:
            group_name = group.get("name", "")
            for member in group.get("members", []):
                user_id = member.get("user_id") or member.get("id")
                if user_id:
                    user_to_ta_group[user_id] = group_name

        # Create submission lookup
        submission_lookup = {}
        for sub in submissions:
            key = (sub.get("user_id"), sub.get("assignment_id"))
            submission_lookup[key] = sub

        # Calculate late days per student
        students_data = []

        for user in users:
            user_id = user.get("id")
            student_data = {
                "student_id": str(user_id),
                "student_name": user.get("name", ""),
                "student_email": user.get("email", ""),
                "ta_group_name": user_to_ta_group.get(user_id, "Unassigned"),
                "total_late_days": 0,
                "assignments": {},
            }

            for assignment in assignments:
                assignment_id = assignment.get("id")
                due_at = assignment.get("due_at")

                if not due_at:
                    continue

                key = (user_id, assignment_id)
                submission = submission_lookup.get(key)

                if submission:
                    submitted_at = submission.get("submitted_at")
                    workflow_state = submission.get("workflow_state", "")

                    if submitted_at and workflow_state not in [
                        "unsubmitted",
                        "pending_review",
                    ]:
                        try:
                            submitted_datetime = dateutil_parser.parse(submitted_at)
                            due_datetime = dateutil_parser.parse(due_at)

                            if submitted_datetime > due_datetime:
                                time_diff = submitted_datetime - due_datetime
                                days_late = max(0, time_diff.days)

                                student_data["assignments"][str(assignment_id)] = (
                                    days_late
                                )
                                student_data["total_late_days"] += days_late
                        except Exception as e:
                            logger.debug(
                                f"Error parsing dates for user {user_id}, assignment {assignment_id}: {e}"  # noqa: E501
                            )

            students_data.append(student_data)

        # Format assignments data
        assignments_data = [
            {
                "id": a.get("id"),
                "name": a.get("name", "Unnamed Assignment"),
                "due_at": a.get("due_at"),
            }
            for a in assignments
            if a.get("due_at")
        ]

        course_name = (
            db.get_setting(f"course_name_{course_id}") or f"Course {course_id}"
        )
        course_info = {"name": course_name, "course_code": course_id}

        return {
            "students": students_data,
            "assignments": assignments_data,
            "course_info": course_info,
            "last_updated": datetime.now(UTC).isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating late days data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate late days data",
        ) from e


@app.get("/api/canvas/peer-review-assignments/{course_id}")
async def get_peer_review_assignments(course_id: str) -> dict[str, Any]:
    """Get assignments that have peer review data."""
    try:
        assignments = db.get_assignments_with_peer_reviews(course_id)
        return {
            "assignments": assignments,
            "count": len(assignments),
            "last_updated": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching peer review assignments: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch peer review assignments",
        ) from e


@app.get("/api/canvas/peer-reviews/{course_id}")
async def get_peer_reviews_data(
    course_id: str, assignment_id: int | None = None
) -> dict[str, Any]:
    """Get peer reviews with user names joined."""
    try:
        peer_reviews = db.get_peer_reviews_with_names(course_id, assignment_id)
        return {
            "peer_reviews": peer_reviews,
            "count": len(peer_reviews),
            "last_updated": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching peer reviews: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch peer reviews",
        ) from e


@app.get("/api/dashboard/peer-reviews/{course_id}", response_model=PeerReviewAnalysis)
async def analyze_peer_reviews(
    course_id: str,
    assignment_id: int,
    deadline: str,
    penalty_per_review: int = 4,
    total_score: int = 12,
) -> PeerReviewAnalysis:
    """
    Analyze peer review timeliness and calculate penalties.

    Args:
        course_id: Course ID
        assignment_id: Assignment ID to analyze
        deadline: ISO datetime string for peer review deadline
        penalty_per_review: Points deducted per late/missing review (default: 4)
        total_score: Maximum total penalty points (default: 12)

    Returns:
        PeerReviewAnalysis with events and penalty summary
    """
    try:
        # Parse deadline
        try:
            deadline_dt = dateutil_parser.parse(deadline)

            # If naive datetime, assume UTC
            if deadline_dt.tzinfo is None:
                deadline_dt = deadline_dt.replace(tzinfo=UTC)
                logger.debug(f"Deadline was naive, assuming UTC: {deadline_dt}")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid deadline format: {e}",
            ) from e

        # Fetch data
        peer_reviews = db.get_peer_reviews_with_names(course_id, assignment_id)
        assignments = db.get_assignments(course_id)

        if not peer_reviews:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No peer reviews found for assignment {assignment_id}",
            )

        # Get assignment name
        assignment_name = next(
            (a["name"] for a in assignments if a["id"] == assignment_id),
            f"Assignment {assignment_id}",
        )

        # Get earliest comment timestamps (optimized database query)
        comment_lookup = db.get_earliest_peer_review_comments(course_id, assignment_id)

        # Process each peer review
        events = []
        reviewer_penalties = {}  # reviewer_id -> {name, late_count, missing_count}

        for pr in peer_reviews:
            reviewer_id = pr["assessor_id"]
            reviewer_name = pr["reviewer_name"]
            assessed_id = pr["user_id"]
            assessed_name = pr["assessed_name"]

            # Find reviewer's comment on assessed user's submission
            # asset_id in peer_review is typically the submission_id
            submission_id = pr.get("asset_id")
            comment_key = (submission_id, reviewer_id) if submission_id else None

            comment_timestamp = None
            status_val = "missing"
            hours_diff = None

            if comment_key and comment_key in comment_lookup:
                comment_timestamp = comment_lookup[comment_key]
                try:
                    comment_dt = dateutil_parser.parse(comment_timestamp)
                    time_diff = comment_dt - deadline_dt
                    hours_diff = time_diff.total_seconds() / 3600

                    status_val = "on_time" if comment_dt <= deadline_dt else "late"
                except Exception as e:
                    logger.warning(f"Error parsing comment timestamp: {e}")

            # Track penalties
            if reviewer_id not in reviewer_penalties:
                reviewer_penalties[reviewer_id] = {
                    "name": reviewer_name,
                    "late_count": 0,
                    "missing_count": 0,
                }

            if status_val == "late":
                reviewer_penalties[reviewer_id]["late_count"] += 1
            elif status_val == "missing":
                reviewer_penalties[reviewer_id]["missing_count"] += 1

            events.append(
                PeerReviewEvent(
                    peer_review_id=pr["id"],
                    assignment_id=assignment_id,
                    assignment_name=assignment_name,
                    reviewer_id=reviewer_id,
                    reviewer_name=reviewer_name,
                    assessed_id=assessed_id,
                    assessed_name=assessed_name,
                    submission_id=submission_id,
                    comment_timestamp=comment_timestamp,
                    status=status_val,
                    hours_difference=round(hours_diff, 2) if hours_diff else None,
                )
            )

        # Calculate summary
        on_time_count = sum(1 for e in events if e.status == "on_time")
        late_count = sum(1 for e in events if e.status == "late")
        missing_count = sum(1 for e in events if e.status == "missing")
        total = len(events)

        summary = PeerReviewSummary(
            total_reviews=total,
            on_time=on_time_count,
            late=late_count,
            missing=missing_count,
            on_time_percentage=round((on_time_count / total * 100), 2) if total else 0,
            late_percentage=round((late_count / total * 100), 2) if total else 0,
            missing_percentage=round((missing_count / total * 100), 2) if total else 0,
        )

        # Calculate penalized reviewers
        penalized_reviewers = []
        for reviewer_id, penalty_data in reviewer_penalties.items():
            late_review_count = penalty_data["late_count"]
            missing_review_count = penalty_data["missing_count"]
            total_infractions = late_review_count + missing_review_count
            penalty_points = min(total_infractions * penalty_per_review, total_score)
            final_grade = total_score - penalty_points

            if penalty_points > 0:
                canvas_comment = (
                    f"Peer Review Grade: {final_grade}/{total_score}\n\n"
                    f"Late reviews: {late_review_count}\n"
                    f"Missing reviews: {missing_review_count}\n"
                    f"Penalty: {penalty_points} points ({penalty_per_review} points per late/missing review, capped at {total_score} points)"  # noqa: E501
                )

                penalized_reviewers.append(
                    PenalizedReviewer(
                        reviewer_id=reviewer_id,
                        reviewer_name=penalty_data["name"],
                        late_count=late_review_count,
                        missing_count=missing_review_count,
                        penalty_points=penalty_points,
                        canvas_comment=canvas_comment,
                    )
                )

        # Sort penalized reviewers by penalty descending
        penalized_reviewers.sort(key=lambda x: x.penalty_points, reverse=True)

        return PeerReviewAnalysis(
            assignment_id=assignment_id,
            assignment_name=assignment_name,
            deadline=deadline,
            penalty_per_review=penalty_per_review,
            total_score=total_score,
            summary=summary,
            events=events,
            penalized_reviewers=penalized_reviewers,
        )

    except HTTPException:
        raise
    except ValueError as e:
        # Handle data validation errors
        logger.warning(f"Invalid data for peer review analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data: {str(e)}",
        ) from e
    except KeyError as e:
        # Handle missing required fields
        logger.error(
            f"Missing required field in peer review data: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data integrity error: missing field {str(e)}",
        ) from e
    except Exception as e:
        logger.error(
            f"Unexpected error analyzing peer reviews: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze peer reviews",
        ) from e


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
