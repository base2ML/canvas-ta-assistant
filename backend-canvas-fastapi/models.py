"""
Pydantic models for request/response validation.
Following FastAPI best practices for data models organization.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl

from config import get_settings


# Load settings once for default factories
_settings = get_settings()


# Request Models
class CanvasCredentials(BaseModel):
    """Canvas API credentials with env-based defaults (visible in docs)."""

    # Use defaults from .env via Settings when not provided in request
    # Use 'default=' so Swagger UI shows values in Try it out.
    base_url: Optional[HttpUrl] = Field(default=_settings.canvas_base_url)
    api_token: Optional[str] = Field(default=_settings.canvas_api_token)


class AssignmentRequest(CanvasCredentials):
    """Request for fetching assignments from multiple courses."""

    course_ids: List[str] = Field(
        default=([_settings.canvas_course_id] if _settings.canvas_course_id else [])
    )


class TAGradingRequest(CanvasCredentials):
    """Request for TA grading information."""

    course_id: str = Field(default=_settings.canvas_course_id or "")
    assignment_id: Optional[int] = None


class PeerReviewRequest(CanvasCredentials):
    """Request for peer review tracking."""

    course_id: str = Field(default=_settings.canvas_course_id or "")
    assignment_id: int
    deadline: str
    penalty_per_review: float = 4.0


# User and Course Models
class UserProfile(BaseModel):
    """User profile information from Canvas."""

    name: str
    email: Optional[str] = None
    id: int
    login_id: Optional[str] = None


class Course(BaseModel):
    """Canvas course information."""

    id: str
    name: str
    course_code: Optional[str] = None
    enrollment_term_id: Optional[int] = None


# Assignment Models
class Assignment(BaseModel):
    """Canvas assignment with submission status."""

    id: int
    name: str
    description: Optional[str] = None
    course_name: str
    course_id: str
    due_at: Optional[str] = None
    unlock_at: Optional[str] = None
    lock_at: Optional[str] = None
    submitted_at: Optional[str] = None
    points_possible: Optional[float] = None
    html_url: Optional[str] = None
    assignment_group_id: Optional[int] = None
    status: str
    status_text: str
    grade: Optional[str] = None
    score: Optional[float] = None
    graded_at: Optional[str] = None
    late: bool = False
    missing: bool = False
    workflow_state: Optional[str] = None


class DetailedAssignment(BaseModel):
    """Detailed assignment information with submission and rubric."""

    assignment: Dict[str, Any]
    submission: Dict[str, Any]
    rubric: Optional[List[Dict[str, Any]]] = None
    course_info: Dict[str, Any]


class AssignmentGradingStats(BaseModel):
    """Assignment grading statistics."""

    assignment_id: int
    assignment_name: str
    total_submissions: int
    graded_submissions: int
    ungraded_submissions: int
    percentage_graded: float
    due_at: Optional[str] = None
    html_url: Optional[str] = None
    ta_grading_breakdown: List[Dict[str, Any]] = []


# TA Management Models
class TAGroup(BaseModel):
    """TA group information."""

    id: int
    name: str
    description: Optional[str] = None
    course_id: str
    members_count: int
    members: List[Dict[str, Any]]


class UngradedSubmission(BaseModel):
    """Information about ungraded submissions assigned to TAs."""

    submission_id: int
    student_name: str
    student_id: str
    assignment_name: str
    assignment_id: int
    course_name: str
    course_id: str
    submitted_at: Optional[str] = None
    late: bool = False
    grader_name: Optional[str] = None  # Specific TA assigned to grade this submission
    ta_group_name: Optional[str] = None  # TA group name this submission belongs to
    ta_members: List[str] = []  # All members in the TA group (for reference)
    html_url: Optional[str] = None


# Peer Review Models
class PeerReviewEvent(BaseModel):
    """Individual peer review event."""

    reviewer_id: int
    reviewer_name: str
    assessed_user_id: int
    assessed_name: str
    assignment_id: int
    review_date: Optional[str] = None
    status: str  # "completed", "late", "missing"
    penalty_points: float = 0.0
    comments: Optional[str] = None


class PeerReviewSummary(BaseModel):
    """Summary of peer review penalties for a student."""

    student_id: int
    student_name: str
    total_penalty: float
    completed_reviews: int
    late_reviews: int
    missing_reviews: int
    details: List[Dict[str, Any]]


# Response Models
class CredentialValidationResponse(BaseModel):
    """Response for credential validation."""

    valid: bool
    user: Optional[UserProfile] = None
    error: Optional[str] = None


class AssignmentResponse(BaseModel):
    """Response for assignment requests."""

    assignments: List[Assignment]
    courses: List[Course]
    total_assignments: int
    warnings: Optional[List[str]] = None


class TAGroupsResponse(BaseModel):
    """Response for TA groups."""

    ta_groups: List[TAGroup]
    course_info: Dict[str, Any]
    total_ta_groups: int


class TAGradingResponse(BaseModel):
    """Response for TA grading information."""

    ungraded_submissions: List[UngradedSubmission]
    ta_groups: List[TAGroup]
    course_info: Dict[str, Any]
    total_ungraded: int
    grading_distribution: Dict[str, int]
    assignment_stats: List[AssignmentGradingStats]


class UngradedSubmissionsResponse(BaseModel):
    """Response for ungraded submissions endpoint."""

    ungraded_submissions: List[UngradedSubmission]
    total_ungraded: int
    course_info: Dict[str, Any]


class AssignmentStatsResponse(BaseModel):
    """Response for assignment statistics endpoint."""

    assignment_stats: List[AssignmentGradingStats]
    course_info: Dict[str, Any]


class GradingDistributionResponse(BaseModel):
    """Response for grading distribution endpoint."""

    grading_distribution: Dict[str, int]
    course_info: Dict[str, Any]


class PeerReviewResponse(BaseModel):
    """Response for peer review tracking."""

    peer_events_data: List[PeerReviewEvent]
    peer_summary_data: List[PeerReviewSummary]
    assignment_data: Dict[str, Any]
    course_data: Dict[str, Any]
    error: Optional[str] = None


# Late Days Models
class LateDaysRequest(BaseModel):
    """Request for late days tracking with env-based defaults (visible in docs)."""

    base_url: Optional[HttpUrl] = Field(default=_settings.canvas_base_url)
    api_token: Optional[str] = Field(default=_settings.canvas_api_token)
    course_id: str = Field(default=_settings.canvas_course_id or "")


class AssignmentInfo(BaseModel):
    """Assignment information for late days tracking."""

    id: int
    name: str
    due_at: Optional[str] = None
    points_possible: Optional[float] = None


class StudentLateDays(BaseModel):
    """Student late days information."""

    student_id: int
    student_name: str
    student_email: Optional[str] = None
    ta_group_name: Optional[str] = None
    assignments: Dict[int, int]  # assignment_id -> late_days
    total_late_days: int


class LateDaysResponse(BaseModel):
    """Response for late days tracking."""

    students: List[StudentLateDays]
    assignments: List[AssignmentInfo]
    course_info: Dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: str
    version: str = "2.0.0"
    canvas_api_version: str = "1.0"


# Error Models
class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    error_type: Optional[str] = None
    timestamp: Optional[str] = None
