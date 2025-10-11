# Minimal peer-review lateness tracker
from typing import Optional

import pandas as pd


def _user_name_map(course) -> dict[int, str]:
    """Return {user_id: 'First Last'} for display; minimal and robust."""
    return {u.id: getattr(u, "name", str(u.id)) for u in course.get_users()}


def fetch_peer_review_events(
    assignment, name_map: Optional[dict[int, str]] = None
) -> pd.DataFrame:
    """
    Return one row per assigned peer review with the reviewer, assessed user, and
    the timestamp of the reviewer's comment on the assessed submission (if any).
    Columns: reviewer_id, assessed_user_id, comment_time (tz-aware or NaT).
    """
    rows = []
    for pr in (
        assignment.get_peer_reviews()
    ):  # pr has assessor_id (reviewer) and user_id (assessed)
        reviewer_id = pr.assessor_id
        assessed_id = pr.user_id
        # Look for a comment authored by the reviewer on the assessed submission
        assessed_sub = assignment.get_submission(
            assessed_id, include=["submission_comments"]
        )
        comment_time = None
        for c in getattr(assessed_sub, "submission_comments", []):
            if c.get("author_id") == reviewer_id:
                comment_time = c.get("created_at")  # ISO8601 string
                break
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
    df["comment_time"] = pd.to_datetime(df["comment_time"], utc=True, errors="coerce")
    if name_map:
        df["reviewer_name"] = df["reviewer_id"].map(name_map)
        df["assessed_name"] = df["assessed_user_id"].map(name_map)
    return df


def evaluate_peer_review_lateness(
    peer_events: pd.DataFrame,
    deadline_ts,  # tz-aware pandas.Timestamp or python datetime w/ tzinfo
    points_per_missed_or_late: int = 4,  # penalty per late or missing review
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
        lambda t: "missing"
        if pd.isna(t)
        else (
            "late" if t > pd.to_datetime(deadline_ts).tz_convert("UTC") else "on_time"
        )
    )
    per["penalty_points"] = (
        per["status"].isin(["late", "missing"]).astype(int) * points_per_missed_or_late
    )

    # Human-readable names if present; otherwise fall back to IDs
    def _name(row, who):
        return row.get(f"{who}_name") or str(row[f"{who}_id"])

    # Canvas-ready comment (one per late/missing review)
    deadline_str = pd.to_datetime(deadline_ts).strftime("%m/%d/%Y %I:%M %p %Z")

    def _comment(row):
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

    return per, agg


# ---------------------------
# Example usage (minimal):
# canvas = Canvas(API_URL, API_KEY)
# course = canvas.get_course(COURSE_ID)
# assignment = course.get_assignment(ASSIGNMENT_ID)
# name_map = _user_name_map(course)
# events = fetch_peer_review_events(assignment, name_map)
# deadline = pd.Timestamp("2025-07-31T00:00:00-04:00").tz_convert("UTC")  # ensure tz-aware
# per_review, per_reviewer = evaluate_peer_review_lateness(events, deadline)
# ---------------------------
