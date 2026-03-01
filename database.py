"""
SQLite database module for Canvas TA Dashboard.
Handles schema creation and CRUD operations for Canvas data.
"""

import contextlib
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger


# Database configuration
DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
DB_PATH = DATA_DIR / "canvas.db"


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_db_transaction():
    """Context manager for database transactions with automatic rollback on error."""
    with get_db_connection() as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def init_db() -> None:
    """Initialize database with schema."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Application settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Assignments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY,
                course_id TEXT NOT NULL,
                name TEXT NOT NULL,
                due_at TIMESTAMP,
                points_possible REAL,
                html_url TEXT,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_assignments_course ON assignments(course_id)"  # noqa: E501
        )

        # Assignment groups table (Canvas assignment group categories)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assignment_groups (
                id INTEGER PRIMARY KEY,
                course_id TEXT NOT NULL,
                name TEXT NOT NULL,
                position INTEGER,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_assignment_groups_course "
            "ON assignment_groups(course_id)"
        )

        # Migration: Add assignment_group_id column for existing assignments tables
        try:
            cursor.execute(
                "ALTER TABLE assignments ADD COLUMN assignment_group_id INTEGER"
            )
            logger.info("Added assignment_group_id column to assignments table")
        except sqlite3.OperationalError:
            # Column already exists
            pass

        # Users table (students)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                course_id TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Migration: Add enrollment_status column for existing databases
        try:
            cursor.execute(
                "ALTER TABLE users ADD COLUMN enrollment_status TEXT DEFAULT 'active'"
            )
            logger.info("Added enrollment_status column to users table")
        except sqlite3.OperationalError:
            # Column already exists
            pass

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_course ON users(course_id)"
        )
        cursor.execute(
            """CREATE INDEX IF NOT EXISTS idx_users_enrollment
               ON users(course_id, enrollment_status)"""
        )

        # Submissions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY,
                course_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                assignment_id INTEGER NOT NULL,
                submitted_at TIMESTAMP,
                workflow_state TEXT,
                late INTEGER DEFAULT 0,
                score REAL,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_submissions_course ON submissions(course_id)"  # noqa: E501
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_submissions_assignment ON submissions(assignment_id)"  # noqa: E501
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_submissions_user ON submissions(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_submissions_user_assignment ON submissions(user_id, assignment_id)"  # noqa: E501
        )

        # Groups table (TA groups)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY,
                course_id TEXT NOT NULL,
                name TEXT NOT NULL,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_groups_course ON groups(course_id)"
        )

        # Group members table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_members (
                group_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                name TEXT,
                PRIMARY KEY (group_id, user_id)
            )
        """)

        # Sync history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                assignments_count INTEGER DEFAULT 0,
                submissions_count INTEGER DEFAULT 0,
                users_count INTEGER DEFAULT 0,
                groups_count INTEGER DEFAULT 0,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)

        # Add dropped_users_count to sync_history if not exists
        with contextlib.suppress(sqlite3.OperationalError):
            cursor.execute(
                """ALTER TABLE sync_history
                ADD COLUMN dropped_users_count INTEGER DEFAULT 0"""
            )

        # Peer reviews table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS peer_reviews (
                id INTEGER PRIMARY KEY,
                course_id TEXT NOT NULL,
                assignment_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                assessor_id INTEGER NOT NULL,
                asset_id INTEGER,
                asset_type TEXT,
                workflow_state TEXT,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_peer_reviews_course ON peer_reviews(course_id)"  # noqa: E501
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_peer_reviews_assignment ON peer_reviews(assignment_id)"  # noqa: E501
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_peer_reviews_course_assignment ON peer_reviews(course_id, assignment_id)"  # noqa: E501
        )

        # Enrollment history table - snapshots of enrollment counts per sync
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS enrollment_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id TEXT NOT NULL,
                sync_id INTEGER NOT NULL,
                active_count INTEGER DEFAULT 0,
                dropped_count INTEGER DEFAULT 0,
                newly_dropped_count INTEGER DEFAULT 0,
                newly_enrolled_count INTEGER DEFAULT 0,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute(
            """CREATE INDEX IF NOT EXISTS idx_enrollment_history_course
            ON enrollment_history(course_id)"""
        )
        cursor.execute(
            """CREATE INDEX IF NOT EXISTS idx_enrollment_history_sync
            ON enrollment_history(sync_id)"""
        )

        # Enrollment events table - individual student status changes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS enrollment_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                user_name TEXT NOT NULL,
                previous_status TEXT NOT NULL,
                new_status TEXT NOT NULL,
                sync_id INTEGER NOT NULL,
                occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute(
            """CREATE INDEX IF NOT EXISTS idx_enrollment_events_course
            ON enrollment_events(course_id)"""
        )

        # Peer review comments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS peer_review_comments (
                id INTEGER PRIMARY KEY,
                course_id TEXT NOT NULL,
                submission_id INTEGER NOT NULL,
                author_id INTEGER NOT NULL,
                comment TEXT,
                created_at TIMESTAMP,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_peer_review_comments_submission ON peer_review_comments(submission_id)"  # noqa: E501
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_peer_review_comments_author ON peer_review_comments(author_id)"  # noqa: E501
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_peer_review_comments_course_submission ON peer_review_comments(course_id, submission_id)"  # noqa: E501
        )

        # Comment templates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comment_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_type TEXT NOT NULL,
                template_text TEXT NOT NULL,
                template_variables TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_comment_templates_type ON comment_templates(template_type)"  # noqa: E501
        )

        # Comment posting history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comment_posting_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id TEXT NOT NULL,
                assignment_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                template_id INTEGER,
                comment_text TEXT NOT NULL,
                canvas_comment_id INTEGER,
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'posted',
                error_message TEXT,
                UNIQUE(course_id, assignment_id, user_id, template_id)
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_posting_history_course_assignment ON comment_posting_history(course_id, assignment_id)"  # noqa: E501
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_posting_history_user ON comment_posting_history(user_id)"  # noqa: E501
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_posting_history_status ON comment_posting_history(status)"  # noqa: E501
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_posting_history_posted_at ON comment_posting_history(posted_at DESC)"  # noqa: E501
        )

        # Clean up any sync records left in_progress from a previous session
        # (happens when the container is stopped/restarted mid-sync)
        cursor.execute(
            """
            UPDATE sync_history
            SET status = 'interrupted', completed_at = ?
            WHERE status = 'in_progress'
            """,
            (datetime.now(UTC),),
        )
        if cursor.rowcount > 0:
            logger.info(
                f"Marked {cursor.rowcount} interrupted sync record(s) as 'interrupted'"
            )

        conn.commit()
        logger.info(f"Database initialized at {DB_PATH}")

        # Populate default templates if needed
        populate_default_templates()


def populate_default_templates() -> None:
    """Populate default comment templates if table is empty."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM comment_templates")
        if cursor.fetchone()["count"] > 0:
            return  # Templates already exist

        default_templates = [
            {
                "template_type": "penalty",
                "template_text": (
                    "Late Day Update for this assignment:\n\n"
                    "Days late: {days_late}\n"
                    "Late days used (this assignment): {penalty_days}\n"
                    "Late days remaining: {days_remaining}\n"
                    "Penalty: {penalty_percent}%\n\n"
                    "Maximum late days per assignment: {max_late_days}\n\n"
                    "Please review the course late day policy if you have questions."
                ),
                "template_variables": json.dumps(
                    [
                        "days_late",
                        "penalty_days",
                        "days_remaining",
                        "penalty_percent",
                        "max_late_days",
                    ]
                ),
            },
            {
                "template_type": "non_penalty",
                "template_text": (
                    "Late Day Update for this assignment:\n\n"
                    "Days late: {days_late}\n"
                    "Late days remaining: {days_remaining}\n\n"
                    "No penalty has been applied.\n\n"
                    "Maximum late days per assignment: {max_late_days}\n\n"
                    "Please review the course late day policy if you have questions."
                ),
                "template_variables": json.dumps(
                    ["days_late", "days_remaining", "max_late_days"]
                ),
            },
        ]

        for template in default_templates:
            cursor.execute(
                """INSERT INTO comment_templates
                   (template_type, template_text, template_variables)
                   VALUES (?, ?, ?)""",
                (
                    template["template_type"],
                    template["template_text"],
                    template["template_variables"],
                ),
            )
        conn.commit()
        logger.info(f"Populated {len(default_templates)} default comment templates")


# Comment template CRUD operations
def create_template(
    template_type: str,
    template_text: str,
    template_variables: str | None = None,
) -> int:
    """Create a new comment template and return its ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now(UTC)
        cursor.execute(
            """INSERT INTO comment_templates
               (template_type, template_text, template_variables,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (template_type, template_text, template_variables, now, now),
        )
        conn.commit()
        return cursor.lastrowid


def get_templates(template_type: str | None = None) -> list[dict[str, Any]]:
    """Get all templates, optionally filtered by template_type."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if template_type:
            cursor.execute(
                """SELECT * FROM comment_templates
                   WHERE template_type = ?
                   ORDER BY template_type, created_at DESC""",
                (template_type,),
            )
        else:
            cursor.execute(
                """SELECT * FROM comment_templates
                   ORDER BY template_type, created_at DESC"""
            )
        return [dict(row) for row in cursor.fetchall()]


def get_template_by_id(template_id: int) -> dict[str, Any] | None:
    """Get a single template by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM comment_templates WHERE id = ?", (template_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_template(
    template_id: int,
    template_type: str,
    template_text: str,
    template_variables: str | None = None,
) -> bool:
    """Update a template. Returns True if updated, False if not found."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE comment_templates
               SET template_type = ?, template_text = ?,
                   template_variables = ?, updated_at = ?
               WHERE id = ?""",
            (
                template_type,
                template_text,
                template_variables,
                datetime.now(UTC),
                template_id,
            ),
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_template(template_id: int) -> bool:
    """Delete a template. Returns True if deleted, False if not found."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM comment_templates WHERE id = ?", (template_id,))
        conn.commit()
        return cursor.rowcount > 0


# Comment posting history operations
def record_comment_posting(
    course_id: str,
    assignment_id: int,
    user_id: int,
    template_id: int | None,
    comment_text: str,
    status: str = "posted",
    canvas_comment_id: int | None = None,
    error_message: str | None = None,
) -> int:
    """Record a comment posting attempt with upsert behavior.

    On conflict (duplicate course_id, assignment_id, user_id, template_id),
    updates the existing record with new data.
    Returns the record ID.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now(UTC)
        cursor.execute(
            """INSERT INTO comment_posting_history
               (course_id, assignment_id, user_id, template_id, comment_text,
                canvas_comment_id, posted_at, status, error_message)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(course_id, assignment_id, user_id, template_id)
               DO UPDATE SET
                   comment_text = excluded.comment_text,
                   canvas_comment_id = excluded.canvas_comment_id,
                   status = excluded.status,
                   error_message = excluded.error_message,
                   posted_at = excluded.posted_at""",
            (
                course_id,
                assignment_id,
                user_id,
                template_id,
                comment_text,
                canvas_comment_id,
                now,
                status,
                error_message,
            ),
        )
        conn.commit()
        record_id = cursor.lastrowid
        logger.info(
            f"Comment posting recorded: course={course_id}, "
            f"assignment={assignment_id}, user={user_id}, status={status}"
        )
        return record_id


def get_posting_history(
    course_id: str,
    assignment_id: int | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Get posting history with optional filters."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        query = "SELECT * FROM comment_posting_history WHERE course_id = ?"
        params: list[Any] = [course_id]

        if assignment_id is not None:
            query += " AND assignment_id = ?"
            params.append(assignment_id)

        if status is not None:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY posted_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def check_duplicate_posting(
    course_id: str,
    assignment_id: int,
    user_id: int,
    template_id: int | None,
) -> dict[str, Any] | None:
    """Check if a comment has already been posted for this combination.

    Returns the existing record if found (status='posted'), None otherwise.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT * FROM comment_posting_history
               WHERE course_id = ? AND assignment_id = ?
                 AND user_id = ? AND template_id = ?
                 AND status = 'posted'""",
            (course_id, assignment_id, user_id, template_id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


# Settings operations
def get_setting(key: str) -> str | None:
    """Get a setting value by key."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else None


def set_setting(key: str, value: str) -> None:
    """Set a setting value."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = ?
        """,
            (key, value, datetime.now(UTC), value, datetime.now(UTC)),
        )
        conn.commit()


def get_all_settings() -> dict[str, str]:
    """Get all settings as a dictionary."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM settings")
        return {row["key"]: row["value"] for row in cursor.fetchall()}


# Canvas data operations
def clear_refreshable_data(course_id: str, conn: sqlite3.Connection) -> None:
    """Clear refreshable data for a course (preserves users and submissions).

    This function clears data that gets fully re-fetched during sync:
    - Peer review comments and peer reviews
    - Groups and group members
    - Assignments

    Users and submissions are preserved:
    - Users have enrollment status tracking (active/dropped)
    - Submissions are upserted (updated if they exist)

    IMPORTANT: This relies on the fact that no FK constraints exist between
    submissions→assignments or submissions→users in the actual schema.
    If FK constraints are added in the future, this function must be updated.
    """
    cursor = conn.cursor()
    cursor.execute("DELETE FROM peer_review_comments WHERE course_id = ?", (course_id,))
    cursor.execute("DELETE FROM peer_reviews WHERE course_id = ?", (course_id,))
    # Note: submissions are preserved (upserted, not cleared)
    cursor.execute(
        "DELETE FROM group_members WHERE group_id IN (SELECT id FROM groups WHERE course_id = ?)",  # noqa: E501
        (course_id,),
    )
    cursor.execute("DELETE FROM groups WHERE course_id = ?", (course_id,))
    cursor.execute("DELETE FROM assignments WHERE course_id = ?", (course_id,))
    cursor.execute("DELETE FROM assignment_groups WHERE course_id = ?", (course_id,))
    # Note: users are preserved (enrollment status tracked, not cleared)
    logger.info(f"Cleared refreshable data for course {course_id}")


def clear_course_data(course_id: str, conn: sqlite3.Connection | None = None) -> None:
    """Clear all data for a course (nuclear option for full reset).

    This is a complete data wipe for a course. Use clear_refreshable_data()
    for normal syncs. This function is kept for manual reset operations
    (e.g., from Settings page).
    """

    def _clear(db_conn: sqlite3.Connection) -> None:
        cursor = db_conn.cursor()
        cursor.execute(
            "DELETE FROM peer_review_comments WHERE course_id = ?", (course_id,)
        )
        cursor.execute("DELETE FROM peer_reviews WHERE course_id = ?", (course_id,))
        cursor.execute(
            "DELETE FROM enrollment_events WHERE course_id = ?", (course_id,)
        )
        cursor.execute(
            "DELETE FROM enrollment_history WHERE course_id = ?", (course_id,)
        )
        cursor.execute("DELETE FROM submissions WHERE course_id = ?", (course_id,))
        cursor.execute(
            "DELETE FROM group_members WHERE group_id IN (SELECT id FROM groups WHERE course_id = ?)",  # noqa: E501
            (course_id,),
        )
        cursor.execute("DELETE FROM groups WHERE course_id = ?", (course_id,))
        cursor.execute("DELETE FROM users WHERE course_id = ?", (course_id,))
        cursor.execute("DELETE FROM assignments WHERE course_id = ?", (course_id,))
        cursor.execute(
            "DELETE FROM assignment_groups WHERE course_id = ?", (course_id,)
        )
        if conn is None:
            db_conn.commit()
        logger.info(f"Cleared all data for course {course_id}")

    if conn is not None:
        _clear(conn)
    else:
        with get_db_connection() as db_conn:
            _clear(db_conn)


def upsert_assignments(
    course_id: str,
    assignments: list[dict[str, Any]],
    conn: sqlite3.Connection | None = None,
) -> int:
    """Insert or update assignments for a course."""

    def _upsert(db_conn: sqlite3.Connection) -> int:
        cursor = db_conn.cursor()
        synced_at = datetime.now(UTC)

        data = [
            (
                assignment["id"],
                course_id,
                assignment["name"],
                assignment.get("due_at"),
                assignment.get("points_possible"),
                assignment.get("html_url"),
                assignment.get("assignment_group_id"),
                synced_at,
            )
            for assignment in assignments
        ]

        cursor.executemany(
            """
            INSERT INTO assignments (
                id, course_id, name, due_at, points_possible, html_url,
                assignment_group_id, synced_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                course_id = excluded.course_id,
                name = excluded.name,
                due_at = excluded.due_at,
                points_possible = excluded.points_possible,
                html_url = excluded.html_url,
                assignment_group_id = excluded.assignment_group_id,
                synced_at = excluded.synced_at
        """,
            data,
        )

        if conn is None:
            db_conn.commit()
        return len(assignments)

    if conn is not None:
        return _upsert(conn)
    else:
        with get_db_connection() as db_conn:
            return _upsert(db_conn)


def upsert_assignment_groups(
    course_id: str,
    groups: list[dict[str, Any]],
    conn: sqlite3.Connection | None = None,
) -> int:
    """Insert or update Canvas assignment groups for a course."""

    def _upsert(db_conn: sqlite3.Connection) -> int:
        cursor = db_conn.cursor()
        synced_at = datetime.now(UTC)
        data = [
            (g["id"], course_id, g["name"], g.get("position"), synced_at)
            for g in groups
        ]
        cursor.executemany(
            """
            INSERT INTO assignment_groups (id, course_id, name, position, synced_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                course_id = excluded.course_id,
                name = excluded.name,
                position = excluded.position,
                synced_at = excluded.synced_at
            """,
            data,
        )
        if conn is None:
            db_conn.commit()
        return len(groups)

    if conn is not None:
        return _upsert(conn)
    else:
        with get_db_connection() as db_conn:
            return _upsert(db_conn)


def upsert_users(
    course_id: str, users: list[dict[str, Any]], conn: sqlite3.Connection | None = None
) -> int:
    """Insert or update users for a course."""

    def _upsert(db_conn: sqlite3.Connection) -> int:
        cursor = db_conn.cursor()
        synced_at = datetime.now(UTC)

        data = [
            (user["id"], course_id, user["name"], user.get("email"), synced_at)
            for user in users
        ]

        cursor.executemany(
            """
            INSERT INTO users (id, course_id, name, email, synced_at, enrollment_status)
            VALUES (?, ?, ?, ?, ?, 'active')
            ON CONFLICT(id) DO UPDATE SET
                course_id = excluded.course_id,
                name = excluded.name,
                email = excluded.email,
                synced_at = excluded.synced_at,
                enrollment_status = 'active'
        """,
            data,
        )

        if conn is None:
            db_conn.commit()
        return len(users)

    if conn is not None:
        return _upsert(conn)
    else:
        with get_db_connection() as db_conn:
            return _upsert(db_conn)


def upsert_submissions(
    course_id: str,
    submissions: list[dict[str, Any]],
    conn: sqlite3.Connection | None = None,
) -> int:
    """Insert or update submissions for a course."""

    def _upsert(db_conn: sqlite3.Connection) -> int:
        cursor = db_conn.cursor()
        synced_at = datetime.now(UTC)

        data = [
            (
                submission["id"],
                course_id,
                submission["user_id"],
                submission["assignment_id"],
                submission.get("submitted_at"),
                submission.get("workflow_state"),
                1 if submission.get("late") else 0,
                submission.get("score"),
                synced_at,
            )
            for submission in submissions
        ]

        cursor.executemany(
            """
            INSERT INTO submissions (
                id, course_id, user_id, assignment_id, submitted_at,
                workflow_state, late, score, synced_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                course_id = excluded.course_id,
                user_id = excluded.user_id,
                assignment_id = excluded.assignment_id,
                submitted_at = excluded.submitted_at,
                workflow_state = excluded.workflow_state,
                late = excluded.late,
                score = excluded.score,
                synced_at = excluded.synced_at
        """,
            data,
        )

        if conn is None:
            db_conn.commit()
        return len(submissions)

    if conn is not None:
        return _upsert(conn)
    else:
        with get_db_connection() as db_conn:
            return _upsert(db_conn)


def upsert_groups(
    course_id: str, groups: list[dict[str, Any]], conn: sqlite3.Connection | None = None
) -> int:
    """Insert or update groups and their members for a course."""

    def _upsert(db_conn: sqlite3.Connection) -> int:
        cursor = db_conn.cursor()
        synced_at = datetime.now(UTC)

        # Prepare groups data
        groups_data = [
            (group["id"], course_id, group["name"], synced_at) for group in groups
        ]

        cursor.executemany(
            """
            INSERT INTO groups (id, course_id, name, synced_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                course_id = excluded.course_id,
                name = excluded.name,
                synced_at = excluded.synced_at
        """,
            groups_data,
        )

        # Clear existing members and prepare new members data
        group_ids = [group["id"] for group in groups]
        if group_ids:
            # Safe: placeholders contains only "?" characters, user data is
            # parameterized. Example: If group_ids = [1, 2, 3],
            # placeholders = "?,?,?" and params = [1, 2, 3]
            placeholders = ",".join("?" * len(group_ids))
            cursor.execute(
                f"DELETE FROM group_members WHERE group_id IN ({placeholders})",
                group_ids,
            )

        members_data = []
        for group in groups:
            for member in group.get("members", []):
                members_data.append(
                    (
                        group["id"],
                        member.get("user_id") or member.get("id"),
                        member.get("name"),
                    )
                )

        if members_data:
            cursor.executemany(
                """
                INSERT INTO group_members (group_id, user_id, name)
                VALUES (?, ?, ?)
            """,
                members_data,
            )

        if conn is None:
            db_conn.commit()
        return len(groups)

    if conn is not None:
        return _upsert(conn)
    else:
        with get_db_connection() as db_conn:
            return _upsert(db_conn)


# Query operations
def get_assignments(course_id: str) -> list[dict[str, Any]]:
    """Get all assignments for a course."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, course_id, name, due_at, points_possible, html_url, synced_at
            FROM assignments WHERE course_id = ?
            ORDER BY due_at DESC NULLS LAST
        """,
            (course_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_users(course_id: str, include_dropped: bool = False) -> list[dict[str, Any]]:
    """Get users for a course. Defaults to active students only."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        query = """
            SELECT id, course_id, name, email, synced_at, enrollment_status
            FROM users WHERE course_id = ?
        """
        params: list[Any] = [course_id]

        if not include_dropped:
            # Also include 'pending_check' as a safety fallback (treated as active)
            query += " AND enrollment_status IN ('active', 'pending_check')"

        query += " ORDER BY name"

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_submissions(
    course_id: str, assignment_id: int | None = None
) -> list[dict[str, Any]]:
    """Get submissions for a course, optionally filtered by assignment."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if assignment_id:
            cursor.execute(
                """
                SELECT id, course_id, user_id, assignment_id, submitted_at,
                       workflow_state, late, score, synced_at
                FROM submissions WHERE course_id = ? AND assignment_id = ?
            """,
                (course_id, assignment_id),
            )
        else:
            cursor.execute(
                """
                SELECT id, course_id, user_id, assignment_id, submitted_at,
                       workflow_state, late, score, synced_at
                FROM submissions WHERE course_id = ?
            """,
                (course_id,),
            )

        return [dict(row) for row in cursor.fetchall()]


def get_groups(course_id: str) -> list[dict[str, Any]]:
    """Get all groups with members for a course."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Get all groups with their members in a single query using LEFT JOIN
        cursor.execute(
            """
            SELECT g.id, g.course_id, g.name, g.synced_at,
                   gm.user_id, gm.name as member_name
            FROM groups g
            LEFT JOIN group_members gm ON g.id = gm.group_id
            WHERE g.course_id = ?
            ORDER BY g.name, gm.name
        """,
            (course_id,),
        )

        # Build groups dict with members
        groups_dict = {}
        for row in cursor.fetchall():
            group_id = row["id"]
            if group_id not in groups_dict:
                groups_dict[group_id] = {
                    "id": group_id,
                    "course_id": row["course_id"],
                    "name": row["name"],
                    "synced_at": row["synced_at"],
                    "members": [],
                }
            if row["user_id"] is not None:
                groups_dict[group_id]["members"].append(
                    {
                        "id": row["user_id"],
                        "user_id": row["user_id"],
                        "name": row["member_name"],
                    }
                )

        return list(groups_dict.values())


def get_courses() -> list[str]:
    """Get list of unique course IDs that have been synced."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT course_id FROM assignments ORDER BY course_id")
        return [row["course_id"] for row in cursor.fetchall()]


# Sync history operations
def create_sync_record(course_id: str) -> int:
    """Create a new sync history record and return its ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO sync_history (course_id, status, started_at)
            VALUES (?, 'in_progress', ?)
        """,
            (course_id, datetime.now(UTC)),
        )
        conn.commit()
        return cursor.lastrowid


def update_sync_record(
    sync_id: int,
    status: str,
    message: str | None = None,
    assignments_count: int = 0,
    submissions_count: int = 0,
    users_count: int = 0,
    groups_count: int = 0,
    dropped_users_count: int = 0,
) -> None:
    """Update a sync history record."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE sync_history
            SET status = ?, message = ?, assignments_count = ?,
                submissions_count = ?, users_count = ?, groups_count = ?,
                dropped_users_count = ?, completed_at = ?
            WHERE id = ?
        """,
            (
                status,
                message,
                assignments_count,
                submissions_count,
                users_count,
                groups_count,
                dropped_users_count,
                datetime.now(UTC),
                sync_id,
            ),
        )
        conn.commit()


def get_last_sync(course_id: str | None = None) -> dict[str, Any] | None:
    """Get the most recent sync record."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if course_id:
            cursor.execute(
                """
                SELECT * FROM sync_history
                WHERE course_id = ?
                ORDER BY started_at DESC LIMIT 1
            """,
                (course_id,),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM sync_history
                ORDER BY started_at DESC LIMIT 1
            """
            )

        row = cursor.fetchone()
        return dict(row) if row else None


def get_sync_history(
    course_id: str | None = None, limit: int = 10
) -> list[dict[str, Any]]:
    """Get sync history records."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if course_id:
            cursor.execute(
                """
                SELECT * FROM sync_history
                WHERE course_id = ?
                ORDER BY started_at DESC LIMIT ?
            """,
                (course_id, limit),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM sync_history
                ORDER BY started_at DESC LIMIT ?
            """,
                (limit,),
            )

        return [dict(row) for row in cursor.fetchall()]


# Peer review operations
def upsert_peer_reviews(
    course_id: str,
    peer_reviews: list[dict[str, Any]],
    conn: sqlite3.Connection | None = None,
) -> int:
    """Insert or update peer reviews for a course."""

    def _upsert(db_conn: sqlite3.Connection) -> int:
        cursor = db_conn.cursor()
        synced_at = datetime.now(UTC)

        data = [
            (
                pr["id"],
                course_id,
                pr["assignment_id"],
                pr["user_id"],
                pr["assessor_id"],
                pr.get("asset_id"),
                pr.get("asset_type"),
                pr.get("workflow_state"),
                synced_at,
            )
            for pr in peer_reviews
        ]

        cursor.executemany(
            """
            INSERT INTO peer_reviews (
                id, course_id, assignment_id, user_id, assessor_id,
                asset_id, asset_type, workflow_state, synced_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                course_id = excluded.course_id,
                assignment_id = excluded.assignment_id,
                user_id = excluded.user_id,
                assessor_id = excluded.assessor_id,
                asset_id = excluded.asset_id,
                asset_type = excluded.asset_type,
                workflow_state = excluded.workflow_state,
                synced_at = excluded.synced_at
        """,
            data,
        )

        if conn is None:
            db_conn.commit()
        return len(peer_reviews)

    if conn is not None:
        return _upsert(conn)
    else:
        with get_db_connection() as db_conn:
            return _upsert(db_conn)


def upsert_peer_review_comments(
    course_id: str,
    comments: list[dict[str, Any]],
    conn: sqlite3.Connection | None = None,
) -> int:
    """Insert or update peer review comments for a course."""

    def _upsert(db_conn: sqlite3.Connection) -> int:
        cursor = db_conn.cursor()
        synced_at = datetime.now(UTC)

        data = [
            (
                c["id"],
                course_id,
                c["submission_id"],
                c["author_id"],
                c.get("comment"),
                c.get("created_at"),
                synced_at,
            )
            for c in comments
        ]

        cursor.executemany(
            """
            INSERT INTO peer_review_comments (
                id, course_id, submission_id, author_id, comment,
                created_at, synced_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                course_id = excluded.course_id,
                submission_id = excluded.submission_id,
                author_id = excluded.author_id,
                comment = excluded.comment,
                created_at = excluded.created_at,
                synced_at = excluded.synced_at
        """,
            data,
        )

        if conn is None:
            db_conn.commit()
        return len(comments)

    if conn is not None:
        return _upsert(conn)
    else:
        with get_db_connection() as db_conn:
            return _upsert(db_conn)


def get_peer_reviews(
    course_id: str, assignment_id: int | None = None
) -> list[dict[str, Any]]:
    """Get peer reviews for a course, optionally filtered by assignment."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if assignment_id:
            cursor.execute(
                """
                SELECT * FROM peer_reviews
                WHERE course_id = ? AND assignment_id = ?
            """,
                (course_id, assignment_id),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM peer_reviews WHERE course_id = ?
            """,
                (course_id,),
            )

        return [dict(row) for row in cursor.fetchall()]


def get_peer_review_comments(
    course_id: str, assignment_id: int | None = None
) -> list[dict[str, Any]]:
    """Get peer review comments for a course, optionally filtered by assignment."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if assignment_id:
            cursor.execute(
                """
                SELECT prc.*
                FROM peer_review_comments prc
                INNER JOIN submissions s ON prc.submission_id = s.id
                WHERE prc.course_id = ? AND s.assignment_id = ?
            """,
                (course_id, assignment_id),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM peer_review_comments WHERE course_id = ?
            """,
                (course_id,),
            )

        return [dict(row) for row in cursor.fetchall()]


def get_earliest_peer_review_comments(
    course_id: str, assignment_id: int
) -> dict[tuple[int, int], str]:
    """Get earliest comment timestamp for each (submission_id, author_id) pair.

    This optimized query performs aggregation at the database level to find
    the earliest comment timestamp for each unique (submission_id, author_id)
    pair, which is more efficient than iterating through all comments in Python.

    Args:
        course_id: Course ID to filter comments
        assignment_id: Assignment ID to filter comments

    Returns:
        Dictionary mapping (submission_id, author_id) tuples to earliest
        comment timestamp strings
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                prc.submission_id,
                prc.author_id,
                MIN(prc.created_at) as earliest_comment
            FROM peer_review_comments prc
            INNER JOIN submissions s ON prc.submission_id = s.id
            WHERE prc.course_id = ? AND s.assignment_id = ?
            GROUP BY prc.submission_id, prc.author_id
            """,
            (course_id, assignment_id),
        )
        return {
            (row["submission_id"], row["author_id"]): row["earliest_comment"]
            for row in cursor.fetchall()
        }


def get_peer_reviews_with_names(
    course_id: str, assignment_id: int | None = None
) -> list[dict[str, Any]]:
    """Get peer reviews with reviewer and assessed user names joined."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if assignment_id:
            cursor.execute(
                """
                SELECT
                    pr.*,
                    reviewer.name as reviewer_name,
                    assessed.name as assessed_name,
                    a.name as assignment_name
                FROM peer_reviews pr
                INNER JOIN users reviewer ON pr.assessor_id = reviewer.id
                INNER JOIN users assessed ON pr.user_id = assessed.id
                INNER JOIN assignments a ON pr.assignment_id = a.id
                WHERE pr.course_id = ? AND pr.assignment_id = ?
                ORDER BY reviewer.name, assessed.name
            """,
                (course_id, assignment_id),
            )
        else:
            cursor.execute(
                """
                SELECT
                    pr.*,
                    reviewer.name as reviewer_name,
                    assessed.name as assessed_name,
                    a.name as assignment_name
                FROM peer_reviews pr
                INNER JOIN users reviewer ON pr.assessor_id = reviewer.id
                INNER JOIN users assessed ON pr.user_id = assessed.id
                INNER JOIN assignments a ON pr.assignment_id = a.id
                WHERE pr.course_id = ?
                ORDER BY a.name, reviewer.name, assessed.name
            """,
                (course_id,),
            )

        return [dict(row) for row in cursor.fetchall()]


def get_assignments_with_peer_reviews(course_id: str) -> list[dict[str, Any]]:
    """Get assignments that have peer review data."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT a.id, a.course_id, a.name, a.due_at,
                   a.points_possible, a.html_url, a.synced_at
            FROM assignments a
            INNER JOIN peer_reviews pr ON a.id = pr.assignment_id
            WHERE a.course_id = ?
            ORDER BY a.due_at DESC NULLS LAST
        """,
            (course_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


# Enrollment status management
def mark_all_users_pending(course_id: str, conn: sqlite3.Connection) -> int:
    """Mark all users as pending_check before sync. Returns count updated."""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET enrollment_status = 'pending_check' WHERE course_id = ?",
        (course_id,),
    )
    return cursor.rowcount


def mark_dropped_users(course_id: str, conn: sqlite3.Connection) -> int:
    """Mark users still pending_check after sync as dropped. Returns count dropped."""
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE users SET enrollment_status = 'dropped'
           WHERE course_id = ? AND enrollment_status = 'pending_check'""",
        (course_id,),
    )
    return cursor.rowcount


def get_enrollment_counts(course_id: str) -> dict[str, int]:
    """Get active and dropped student counts."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT enrollment_status, COUNT(*) as count
               FROM users WHERE course_id = ?
               GROUP BY enrollment_status""",
            (course_id,),
        )
        counts = {row["enrollment_status"]: row["count"] for row in cursor.fetchall()}
        return {
            "active": counts.get("active", 0),
            "dropped": counts.get("dropped", 0),
        }


def cleanup_orphaned_submissions(course_id: str, conn: sqlite3.Connection) -> int:
    """Delete submissions whose assignment_id no longer exists in assignments table."""
    cursor = conn.cursor()
    cursor.execute(
        """DELETE FROM submissions
           WHERE course_id = ?
           AND assignment_id NOT IN (SELECT id FROM assignments WHERE course_id = ?)""",
        (course_id, course_id),
    )
    count = cursor.rowcount
    if count > 0:
        logger.info(f"Cleaned up {count} orphaned submissions for course {course_id}")
    return count


# Statistics
def get_submission_stats(course_id: str) -> dict[str, Any]:
    """Get submission statistics for a course."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Total counts
        cursor.execute(
            "SELECT COUNT(*) as total FROM assignments WHERE course_id = ?",
            (course_id,),
        )
        total_assignments = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT COUNT(*) as total FROM users WHERE course_id = ?", (course_id,)
        )
        total_users = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT COUNT(*) as total FROM submissions WHERE course_id = ?",
            (course_id,),
        )
        total_submissions = cursor.fetchone()["total"]

        # Submission status breakdown
        cursor.execute(
            """
            SELECT workflow_state, COUNT(*) as count
            FROM submissions WHERE course_id = ?
            GROUP BY workflow_state
        """,
            (course_id,),
        )
        status_breakdown = {
            row["workflow_state"]: row["count"] for row in cursor.fetchall()
        }

        # Late submissions
        cursor.execute(
            "SELECT COUNT(*) as count FROM submissions WHERE course_id = ? AND late = 1",  # noqa: E501
            (course_id,),
        )
        late_count = cursor.fetchone()["count"]

        return {
            "total_assignments": total_assignments,
            "total_users": total_users,
            "total_submissions": total_submissions,
            "status_breakdown": status_breakdown,
            "late_submissions": late_count,
        }


# Enrollment tracking functions


def get_enrollment_state_snapshot(
    course_id: str, conn: sqlite3.Connection
) -> dict[int, tuple[str, str]]:
    """Get current enrollment state before sync modifies anything.

    Returns dict mapping user_id to (enrollment_status, name).
    Called within transaction, before mark_all_users_pending().
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, name, enrollment_status
        FROM users
        WHERE course_id = ?
        """,
        (course_id,),
    )
    return {
        row["id"]: (row["enrollment_status"], row["name"]) for row in cursor.fetchall()
    }


def record_enrollment_snapshot(
    course_id: str,
    sync_id: int,
    active_count: int,
    dropped_count: int,
    newly_dropped_count: int,
    newly_enrolled_count: int,
    conn: sqlite3.Connection,
) -> int:
    """Record an enrollment snapshot for a sync.

    Returns the snapshot ID.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO enrollment_history
        (course_id, sync_id, active_count, dropped_count,
         newly_dropped_count, newly_enrolled_count, recorded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            course_id,
            sync_id,
            active_count,
            dropped_count,
            newly_dropped_count,
            newly_enrolled_count,
            datetime.now(UTC),
        ),
    )
    return cursor.lastrowid


def record_enrollment_events(
    course_id: str,
    sync_id: int,
    before_state: dict[int, tuple[str, str]],
    conn: sqlite3.Connection,
) -> dict[str, int]:
    """Record individual enrollment status changes.

    Compares before_state with current DB state and records events.
    Returns dict with counts: {"events_recorded", "newly_dropped", "newly_enrolled"}.
    """
    # Get current state after sync
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, name, enrollment_status
        FROM users
        WHERE course_id = ?
        """,
        (course_id,),
    )
    current_users = {
        row["id"]: (row["enrollment_status"], row["name"]) for row in cursor.fetchall()
    }

    events_recorded = 0
    newly_dropped = 0
    newly_enrolled = 0

    # Find status changes and new users
    for user_id, (current_status, current_name) in current_users.items():
        if user_id in before_state:
            previous_status, _ = before_state[user_id]
            if previous_status != current_status:
                # Status changed
                cursor.execute(
                    """
                    INSERT INTO enrollment_events
                    (course_id, user_id, user_name, previous_status,
                     new_status, sync_id, occurred_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        course_id,
                        user_id,
                        current_name,
                        previous_status,
                        current_status,
                        sync_id,
                        datetime.now(UTC),
                    ),
                )
                events_recorded += 1
                if current_status == "dropped":
                    newly_dropped += 1
                elif current_status == "active" and previous_status == "dropped":
                    newly_enrolled += 1  # Re-enrolled
        else:
            # New user (not in before_state)
            if current_status == "active":
                cursor.execute(
                    """
                    INSERT INTO enrollment_events
                    (course_id, user_id, user_name, previous_status,
                     new_status, sync_id, occurred_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        course_id,
                        user_id,
                        current_name,
                        "new",
                        current_status,
                        sync_id,
                        datetime.now(UTC),
                    ),
                )
                events_recorded += 1
                newly_enrolled += 1

    return {
        "events_recorded": events_recorded,
        "newly_dropped": newly_dropped,
        "newly_enrolled": newly_enrolled,
    }


def get_enrollment_counts_transactional(
    course_id: str, conn: sqlite3.Connection
) -> tuple[int, int]:
    """Get enrollment counts using existing connection (within transaction).

    Returns (active_count, dropped_count).
    """
    cursor = conn.cursor()
    cursor.execute(
        """SELECT COUNT(*) as count FROM users
        WHERE course_id = ? AND enrollment_status = 'active'""",
        (course_id,),
    )
    active_count = cursor.fetchone()["count"]

    cursor.execute(
        """SELECT COUNT(*) as count FROM users
        WHERE course_id = ? AND enrollment_status = 'dropped'""",
        (course_id,),
    )
    dropped_count = cursor.fetchone()["count"]

    return active_count, dropped_count


def get_enrollment_history(course_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """Get enrollment history snapshots for a course.

    Returns list of snapshots with sync timestamps, ordered by most recent first.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                eh.id,
                eh.course_id,
                eh.sync_id,
                eh.active_count,
                eh.dropped_count,
                eh.newly_dropped_count,
                eh.newly_enrolled_count,
                eh.recorded_at,
                sh.started_at as sync_started_at,
                sh.completed_at as sync_completed_at
            FROM enrollment_history eh
            LEFT JOIN sync_history sh ON eh.sync_id = sh.id
            WHERE eh.course_id = ?
            ORDER BY eh.recorded_at DESC
            LIMIT ?
            """,
            (course_id, limit),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_enrollment_events(course_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Get recent enrollment events for a course.

    Returns list of individual student status changes, ordered by most recent first.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                ee.id,
                ee.course_id,
                ee.user_id,
                ee.user_name,
                ee.previous_status,
                ee.new_status,
                ee.sync_id,
                ee.occurred_at
            FROM enrollment_events ee
            WHERE ee.course_id = ?
            ORDER BY ee.occurred_at DESC
            LIMIT ?
            """,
            (course_id, limit),
        )
        return [dict(row) for row in cursor.fetchall()]
