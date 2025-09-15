"""
Peer review tracking and lateness analysis endpoints.
Following FastAPI best practices for dependency injection and error handling.
"""

import asyncio
import logging
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional

import pandas as pd
from canvasapi import Canvas
from canvasapi.exceptions import ResourceDoesNotExist
from fastapi import APIRouter, Depends, HTTPException, status

from dependencies import SettingsDep, ThreadPoolDep, resolve_credentials
from models import (
    PeerReviewEvent,
    PeerReviewRequest,
    PeerReviewResponse,
    PeerReviewSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["peer-reviews"],
    responses={404: {"description": "Not found"}},
)


async def get_canvas_from_peer_request(
    request: PeerReviewRequest, settings: SettingsDep
) -> Canvas:
    """Convert PeerReviewRequest to Canvas client."""
    from dependencies import validate_canvas_credentials

    base_url, token = resolve_credentials(
        request.base_url, request.api_token, settings
    )
    return await validate_canvas_credentials(base_url, token, settings)


def analyze_comments_for_peer_reviews(
    assignment: Any, name_map: Optional[Dict[int, str]] = None
) -> pd.DataFrame:
    """
    Alternative approach: Analyze all submission comments to identify potential peer reviews.
    This is a fallback when Canvas peer review API doesn't return data.
    """
    try:
        logger.info("Using alternative comment analysis for peer review detection")

        # Get all submissions with comments using CanvasAPI best practices
        submissions = list(
            assignment.get_submissions(
                include=["submission_comments", "user", "submission_history"],
                per_page=100,  # CanvasAPI best practice
                workflow_state="submitted"  # Only submitted submissions for efficiency
            )
        )
        logger.info(f"Found {len(submissions)} submissions to analyze")

        rows = []
        student_ids = set()

        # First pass: collect all student IDs
        for submission in submissions:
            if hasattr(submission, "user") and hasattr(submission.user, "id"):
                student_ids.add(submission.user.id)

        logger.info(f"Found {len(student_ids)} unique students")

        # Second pass: analyze comments for cross-student interactions (potential peer reviews)
        for submission in submissions:
            if not hasattr(submission, "user") or not hasattr(submission.user, "id"):
                continue

            submission_author_id = submission.user.id
            comments = getattr(submission, "submission_comments", [])

            for comment in comments:
                commenter_id = comment.get("author_id")
                comment_time = comment.get("created_at")

                # If a student commented on another student's submission, treat as peer review
                if (
                    commenter_id
                    and commenter_id != submission_author_id
                    and commenter_id in student_ids
                ):

                    logger.info(
                        f"Found potential peer review: student {commenter_id} commented on {submission_author_id}'s submission at {comment_time}"
                    )

                    rows.append(
                        dict(
                            reviewer_id=commenter_id,
                            assessed_user_id=submission_author_id,
                            comment_time=comment_time,
                        )
                    )

        df = pd.DataFrame(rows)
        if df.empty:
            logger.warning(
                "No cross-student comments found - no peer review activity detected"
            )
            return df

        logger.info(
            f"Found {len(df)} potential peer review interactions through comment analysis"
        )

        # Add name mapping
        df["comment_time"] = pd.to_datetime(
            df["comment_time"], utc=True, errors="coerce"
        )
        if name_map:
            df["reviewer_name"] = df["reviewer_id"].map(name_map)
            df["assessed_name"] = df["assessed_user_id"].map(name_map)

        return df

    except Exception as e:
        logger.error(f"Error in alternative comment analysis: {str(e)}")
        return pd.DataFrame()


def fetch_peer_review_events_sync(
    assignment: Any, name_map: Optional[Dict[int, str]] = None
) -> pd.DataFrame:
    """
    Return one row per assigned peer review with the reviewer, assessed user, and
    the timestamp of the reviewer's comment on the assessed submission (if any).
    Columns: reviewer_id, assessed_user_id, comment_time (tz-aware or NaT).
    """
    rows = []
    try:
        logger.info(
            f"Fetching peer reviews for assignment {assignment.id}: {assignment.name}"
        )

        # Get all peer reviews
        try:
            peer_reviews = list(assignment.get_peer_reviews())
            logger.info(f"Found {len(peer_reviews)} Canvas peer reviews")
        except Exception as pr_error:
            logger.error(
                f"Error calling assignment.get_peer_reviews(): {str(pr_error)}"
            )
            logger.error(f"Error type: {type(pr_error)}")
            # Try alternative approach immediately
            logger.info("Falling back to comment analysis due to peer review API error")
            return analyze_comments_for_peer_reviews(assignment, name_map)

        if not peer_reviews:
            logger.warning("No Canvas peer reviews found. This might mean:")
            logger.warning(
                "1. The assignment doesn't have peer reviews enabled in Canvas"
            )
            logger.warning("2. Peer reviews haven't been assigned yet")
            logger.warning("3. You need instructor/TA permissions to see peer reviews")

            # Alternative approach: Look for comments that might be peer reviews
            logger.info(
                "Attempting alternative approach: analyzing all comments for peer review patterns"
            )
            return analyze_comments_for_peer_reviews(assignment, name_map)

        for pr in peer_reviews:
            logger.info(
                f"Processing peer review: assessor_id={pr.assessor_id}, user_id={pr.user_id}"
            )
            reviewer_id = pr.assessor_id
            assessed_id = pr.user_id

            # Look for a comment authored by the reviewer on the assessed submission
            assessed_sub = assignment.get_submission(
                assessed_id, include=["submission_comments"]
            )
            comment_time = None
            comments = getattr(assessed_sub, "submission_comments", [])
            logger.info(f"Found {len(comments)} comments on submission {assessed_id}")

            for c in comments:
                if c.get("author_id") == reviewer_id:
                    comment_time = c.get("created_at")  # ISO8601 string
                    logger.info(
                        f"Found peer review comment from {reviewer_id} at {comment_time}"
                    )
                    break

            if not comment_time:
                logger.info(
                    f"No comment found from reviewer {reviewer_id} on submission {assessed_id}"
                )

            rows.append(
                dict(
                    reviewer_id=reviewer_id,
                    assessed_user_id=assessed_id,
                    comment_time=comment_time,
                )
            )

        df = pd.DataFrame(rows)
        if df.empty:
            return df

        # Normalize timestamps to tz-aware datetimes (NaT for missing)
        df["comment_time"] = pd.to_datetime(
            df["comment_time"], utc=True, errors="coerce"
        )
        if name_map:
            df["reviewer_name"] = df["reviewer_id"].map(name_map)
            df["assessed_name"] = df["assessed_user_id"].map(name_map)
        return df
    except Exception as e:
        logger.error(f"Error fetching peer review events: {str(e)}")
        return pd.DataFrame()


def evaluate_peer_review_lateness_sync(
    peer_events: pd.DataFrame,
    deadline_ts: Any,  # tz-aware pandas.Timestamp or python datetime w/ tzinfo
    points_per_missed_or_late: float = 4,  # penalty per late or missing review
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Classify each review as on-time/late/missing and compute penalties.
    Returns:
      per_review  : one row per assigned review with status and Canvas comment text
      per_reviewer: aggregated penalties and concatenated comments
    """
    if peer_events.empty:
        return peer_events.copy(), peer_events.copy()

    per = peer_events.copy()
    per["status"] = per["comment_time"].apply(
        lambda t: (
            "missing"
            if pd.isna(t)
            else (
                "late"
                if t > pd.to_datetime(deadline_ts).tz_convert("UTC")
                else "on_time"
            )
        )
    )
    per["penalty_points"] = (
        per["status"].isin(["late", "missing"]).astype(int) * points_per_missed_or_late
    )

    # Human-readable names if present; otherwise fall back to IDs
    def _name(row: Any, who: str) -> str:
        return row.get(f"{who}_name") or str(row[f"{who}_id"])

    # Canvas-ready comment (one per late/missing review)
    deadline_str = pd.to_datetime(deadline_ts).strftime("%m/%d/%Y %I:%M %p %Z")

    def _comment(row: Any) -> str:
        assessed = _name(row, "assessed")
        if row["status"] == "missing":
            return f"You did not complete a peer review for {assessed}; {points_per_missed_or_late} points deducted."
        if row["status"] == "late":
            return (
                f"Your peer review for {assessed} was submitted after the deadline "
                f"({deadline_str}); {points_per_missed_or_late} points deducted."
            )
        return ""

    per["canvas_comment"] = per.apply(_comment, axis=1)

    # Filter only actionable deductions for posting
    actionable = per[per["penalty_points"] > 0].copy()

    # Aggregate by reviewer: total points and concatenated comments
    if not actionable.empty:
        agg = (
            actionable.groupby(["reviewer_id", "reviewer_name"], dropna=False)
            .agg(
                points=("penalty_points", "sum"),
                canvas_comment=(
                    "canvas_comment",
                    lambda x: "\n+++++++++++++++++\n".join(x),
                ),
            )
            .reset_index()
        )
    else:
        agg = pd.DataFrame(
            columns=["reviewer_id", "reviewer_name", "points", "canvas_comment"]
        )

    return per, agg


@router.post("/peer-reviews", response_model=PeerReviewResponse)
async def get_peer_review_lateness(
    request: PeerReviewRequest, settings: SettingsDep, thread_pool: ThreadPoolDep
) -> PeerReviewResponse:
    """
    Analyze peer review lateness and calculate penalties.

    - **course_id**: Canvas course ID
    - **assignment_id**: Assignment ID for the project proposal or final project
    - **deadline**: Deadline for peer reviews (ISO format: YYYY-MM-DDTHH:MM:SS)
    - **penalty_per_review**: Points deducted per late or missing review (default: 4)
    """
    try:
        canvas = await get_canvas_from_peer_request(request, settings)
        loop = asyncio.get_event_loop()

        # Get course and assignment data concurrently
        course_task = loop.run_in_executor(
            thread_pool, lambda: canvas.get_course(request.course_id)
        )

        # Wait for course first, then get assignment
        course = await course_task
        course_data = {
            "id": str(course.id),
            "name": course.name,
            "course_code": getattr(course, "course_code", None),
        }
        logger.info(f"Course: {course.name} (ID: {course.id})")

        # Get assignment
        assignment = await loop.run_in_executor(
            thread_pool, lambda: course.get_assignment(request.assignment_id)
        )
        assignment_data = {
            "id": assignment.id,
            "name": assignment.name,
            "description": getattr(assignment, "description", None),
            "due_at": getattr(assignment, "due_at", None),
            "html_url": getattr(assignment, "html_url", None),
            "has_submitted_submissions": getattr(
                assignment, "has_submitted_submissions", None
            ),
            "peer_reviews": getattr(assignment, "peer_reviews", None),
        }
        logger.info(f"Assignment details: {assignment.name} (ID: {assignment.id})")

        # Create user name mapping using CanvasAPI best practices
        def get_users() -> List[Any]:
            """Get course users with optimal parameters."""
            return list(course.get_users(
                per_page=100,  # CanvasAPI best practice
                enrollment_type=["student", "teacher", "ta"],  # Include relevant user types
                enrollment_state=["active", "invited"],  # Only active/invited users
                include=["email", "sis_user_id"]  # Include useful user data
            ))
        
        users = await loop.run_in_executor(thread_pool, get_users)
        name_map = {u.id: getattr(u, "name", str(u.id)) for u in users}

        # Fetch peer review events
        peer_events_df = await loop.run_in_executor(
            thread_pool, lambda: fetch_peer_review_events_sync(assignment, name_map)
        )

        if peer_events_df.empty:
            logger.info(f"No peer reviews found for assignment {request.assignment_id}")
            return PeerReviewResponse(
                peer_events_data=[],
                peer_summary_data=[],
                assignment_data=assignment_data,
                course_data=course_data,
                error=None,
            )

        # Parse deadline
        try:
            deadline_ts = pd.to_datetime(request.deadline, utc=True)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid deadline format: {str(e)}",
            )

        # Evaluate lateness
        per_review_df, per_reviewer_df = await loop.run_in_executor(
            thread_pool,
            lambda: evaluate_peer_review_lateness_sync(
                peer_events_df, deadline_ts, request.penalty_per_review
            ),
        )

        # Convert DataFrames to Pydantic models
        peer_review_events = []
        for _, row in per_review_df.iterrows():
            event = PeerReviewEvent(
                reviewer_id=int(row["reviewer_id"]),
                reviewer_name=row.get("reviewer_name", f"Student {row['reviewer_id']}"),
                assessed_user_id=int(row["assessed_user_id"]),
                assessed_name=row.get(
                    "assessed_name", f"Student {row['assessed_user_id']}"
                ),
                assignment_id=request.assignment_id,
                review_date=(
                    row["comment_time"].isoformat()
                    if pd.notna(row["comment_time"])
                    else None
                ),
                status=row["status"],
                penalty_points=float(row["penalty_points"]),
                comments=row.get("canvas_comment", ""),
            )
            peer_review_events.append(event)

        peer_review_summary = []
        for _, row in per_reviewer_df.iterrows():
            # Calculate review counts
            reviewer_events = per_review_df[
                per_review_df["reviewer_id"] == row["reviewer_id"]
            ]
            completed_reviews = len(
                reviewer_events[reviewer_events["status"] == "on_time"]
            )
            late_reviews = len(reviewer_events[reviewer_events["status"] == "late"])
            missing_reviews = len(
                reviewer_events[reviewer_events["status"] == "missing"]
            )

            summary = PeerReviewSummary(
                student_id=int(row["reviewer_id"]),
                student_name=row.get("reviewer_name", f"Student {row['reviewer_id']}"),
                total_penalty=float(row["points"]),
                completed_reviews=completed_reviews,
                late_reviews=late_reviews,
                missing_reviews=missing_reviews,
                details=[
                    {
                        "canvas_comment": row["canvas_comment"],
                        "total_penalty_points": float(row["points"]),
                    }
                ],
            )
            peer_review_summary.append(summary)

        return PeerReviewResponse(
            peer_events_data=peer_review_events,
            peer_summary_data=peer_review_summary,
            assignment_data=assignment_data,
            course_data=course_data,
            error=None,
        )

    except HTTPException:
        raise
    except ResourceDoesNotExist as e:
        if "course" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course {request.course_id} not found or access denied",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assignment {request.assignment_id} not found in course {request.course_id}",
            )
    except Exception as e:
        logger.error(f"Error processing peer review data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing peer review data: {str(e)}",
        )
