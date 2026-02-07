"""
SQLite database module for Canvas TA Dashboard.
Handles schema creation and CRUD operations for Canvas data.
"""

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
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_course ON users(course_id)"
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

        conn.commit()
        logger.info(f"Database initialized at {DB_PATH}")


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
def clear_course_data(course_id: str, conn: sqlite3.Connection | None = None) -> None:
    """Clear all data for a course before re-sync."""

    def _clear(db_conn: sqlite3.Connection) -> None:
        cursor = db_conn.cursor()
        cursor.execute(
            "DELETE FROM peer_review_comments WHERE course_id = ?", (course_id,)
        )
        cursor.execute("DELETE FROM peer_reviews WHERE course_id = ?", (course_id,))
        cursor.execute("DELETE FROM submissions WHERE course_id = ?", (course_id,))
        cursor.execute(
            "DELETE FROM group_members WHERE group_id IN (SELECT id FROM groups WHERE course_id = ?)",  # noqa: E501
            (course_id,),
        )
        cursor.execute("DELETE FROM groups WHERE course_id = ?", (course_id,))
        cursor.execute("DELETE FROM users WHERE course_id = ?", (course_id,))
        cursor.execute("DELETE FROM assignments WHERE course_id = ?", (course_id,))
        if conn is None:
            db_conn.commit()
        logger.info(f"Cleared existing data for course {course_id}")

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
                synced_at,
            )
            for assignment in assignments
        ]

        cursor.executemany(
            """
            INSERT INTO assignments (
                id, course_id, name, due_at, points_possible, html_url, synced_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                course_id = excluded.course_id,
                name = excluded.name,
                due_at = excluded.due_at,
                points_possible = excluded.points_possible,
                html_url = excluded.html_url,
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
            INSERT INTO users (id, course_id, name, email, synced_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                course_id = excluded.course_id,
                name = excluded.name,
                email = excluded.email,
                synced_at = excluded.synced_at
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


def get_users(course_id: str) -> list[dict[str, Any]]:
    """Get all users for a course."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, course_id, name, email, synced_at
            FROM users WHERE course_id = ?
            ORDER BY name
        """,
            (course_id,),
        )
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
) -> None:
    """Update a sync history record."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE sync_history
            SET status = ?, message = ?, assignments_count = ?, submissions_count = ?,
                users_count = ?, groups_count = ?, completed_at = ?
            WHERE id = ?
        """,
            (
                status,
                message,
                assignments_count,
                submissions_count,
                users_count,
                groups_count,
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


def get_peer_review_comments(course_id: str) -> list[dict[str, Any]]:
    """Get peer review comments for a course."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM peer_review_comments WHERE course_id = ?
        """,
            (course_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


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
