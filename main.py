"""
Canvas TA Dashboard FastAPI Application
Local deployment with SQLite data storage
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import database as db
import canvas_sync

# Configure loguru
logger.add("logs/app.log", rotation="500 MB", retention="10 days", level="INFO")

# Environment variables
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
CANVAS_API_URL = os.getenv("CANVAS_API_URL", "")
CANVAS_COURSE_ID = os.getenv("CANVAS_COURSE_ID", "")


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
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
    version="5.0.0",
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
    course_id: Optional[str]
    course_name: Optional[str]
    canvas_api_url: str
    last_sync: Optional[dict[str, Any]]


class SettingsUpdateRequest(BaseModel):
    course_id: str


class SyncResponse(BaseModel):
    status: str
    message: str
    course_id: Optional[str]
    stats: Optional[dict[str, int]]
    duration_seconds: Optional[float]


class SubmissionStatusMetrics(BaseModel):
    on_time: int
    late: int
    missing: int
    on_time_percentage: float
    late_percentage: float
    missing_percentage: float
    total_expected: int


# Health check endpoints
@app.get("/health")
async def simple_health_check():
    """Simple health check endpoint for Docker health checks."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


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

    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="5.0.0",
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
        courses = canvas_sync.fetch_available_courses()
        return {"courses": courses, "total": len(courses)}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error fetching courses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch courses: {str(e)}",
        )


# Sync endpoints
@app.post("/api/canvas/sync", response_model=SyncResponse)
async def trigger_sync(course_id: Optional[str] = None) -> SyncResponse:
    """Trigger Canvas data sync."""
    # Use provided course_id or get from settings
    sync_course_id = course_id or db.get_setting("course_id") or CANVAS_COURSE_ID

    if not sync_course_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No course ID configured. Set course ID in settings first.",
        )

    try:
        result = canvas_sync.sync_course_data(sync_course_id)

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
        )
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}",
        )


@app.get("/api/canvas/sync/status")
async def get_sync_status(course_id: Optional[str] = None) -> dict[str, Any]:
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
        course_data.append({
            "id": course_id,
            "name": course_name or f"Course {course_id}",
            "last_updated": last_sync.get("completed_at") if last_sync else None,
        })

    return {
        "courses": course_data,
        "total": len(course_data),
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
    course_id: str, assignment_id: Optional[int] = None
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
            from dateutil import parser

            submitted_datetime = parser.parse(submitted_at)
            due_datetime = parser.parse(due_at)
            if submitted_datetime > due_datetime:
                return "late"
        except Exception as e:
            logger.debug(f"Error parsing dates: {e}")

    return "on_time"


def calculate_submission_status_metrics(
    assignments: list[dict],
    submissions: list[dict],
    users: list[dict],
    groups: list[dict],
    assignment_filter: Optional[str] = None,
    ta_group_filter: Optional[str] = None,
) -> dict[str, Any]:
    """Calculate comprehensive submission status metrics."""
    # Filter assignments if specified
    if assignment_filter and assignment_filter != "all":
        assignments = [a for a in assignments if str(a.get("id")) == assignment_filter]

    # Pre-compute user to TA group mapping
    user_to_ta_group = {}
    for group in groups:
        group_name = group.get("name")
        for member in group.get("members", []):
            user_id = member.get("user_id") or member.get("id")
            if user_id:
                user_to_ta_group[user_id] = group_name

    # Filter users by TA group if specified
    if ta_group_filter and ta_group_filter != "all":
        users = [
            u for u in users if user_to_ta_group.get(u.get("id")) == ta_group_filter
        ]

    # Create submission lookup
    submission_lookup = {}
    for sub in submissions:
        key = (sub.get("user_id"), sub.get("assignment_id"))
        submission_lookup[key] = sub

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
        if ta_group_filter and ta_group_filter != "all" and group_name != ta_group_filter:
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
        assignment_metrics[str(assignment_id)] = {
            "assignment_id": str(assignment_id),
            "assignment_name": assignment_name,
            "due_date": due_date,
            "metrics": {
                "on_time": assignment_on_time,
                "late": assignment_late,
                "missing": assignment_missing,
                "on_time_percentage": (
                    assignment_on_time / total_assignment_submissions * 100
                )
                if total_assignment_submissions > 0
                else 0,
                "late_percentage": (assignment_late / total_assignment_submissions * 100)
                if total_assignment_submissions > 0
                else 0,
                "missing_percentage": (
                    assignment_missing / total_assignment_submissions * 100
                )
                if total_assignment_submissions > 0
                else 0,
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

    # Calculate TA percentages
    for metrics in ta_metrics.values():
        total = metrics["on_time"] + metrics["late"] + metrics["missing"]
        if total > 0:
            metrics["on_time_percentage"] = metrics["on_time"] / total * 100
            metrics["late_percentage"] = metrics["late"] / total * 100
            metrics["missing_percentage"] = metrics["missing"] / total * 100
        else:
            metrics["on_time_percentage"] = 0
            metrics["late_percentage"] = 0
            metrics["missing_percentage"] = 0

    return {
        "overall_metrics": {
            "on_time": overall_on_time,
            "late": overall_late,
            "missing": overall_missing,
            "on_time_percentage": (overall_on_time / total_expected * 100)
            if total_expected > 0
            else 0,
            "late_percentage": (overall_late / total_expected * 100)
            if total_expected > 0
            else 0,
            "missing_percentage": (overall_missing / total_expected * 100)
            if total_expected > 0
            else 0,
            "total_expected": total_expected,
        },
        "by_assignment": list(assignment_metrics.values()),
        "by_ta": list(ta_metrics.values()),
    }


@app.get("/api/dashboard/submission-status/{course_id}")
async def get_submission_status_metrics(
    course_id: str,
    assignment_id: Optional[str] = None,
    ta_group: Optional[str] = None,
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
        logger.error(f"Error calculating submission status metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating metrics: {str(e)}",
        )


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
        "last_updated": datetime.now(timezone.utc).isoformat(),
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
                            from dateutil import parser

                            submitted_datetime = parser.parse(submitted_at)
                            due_datetime = parser.parse(due_at)

                            if submitted_datetime > due_datetime:
                                time_diff = submitted_datetime - due_datetime
                                days_late = max(0, time_diff.days)

                                student_data["assignments"][str(assignment_id)] = days_late
                                student_data["total_late_days"] += days_late
                        except Exception as e:
                            logger.debug(
                                f"Error parsing dates for user {user_id}, assignment {assignment_id}: {e}"
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

        course_name = db.get_setting(f"course_name_{course_id}") or f"Course {course_id}"
        course_info = {"name": course_name, "course_code": course_id}

        return {
            "students": students_data,
            "assignments": assignments_data,
            "course_info": course_info,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Error calculating late days data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate late days data: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
