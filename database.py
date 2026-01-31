"""
SQLite database module for Canvas TA Dashboard.
Handles schema creation and CRUD operations for Canvas data.
"""

import sqlite3
import os
from datetime import datetime
from typing import Any, Optional
from pathlib import Path
from contextlib import contextmanager

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
    try:
        yield conn
    finally:
        conn.close()


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
            "CREATE INDEX IF NOT EXISTS idx_assignments_course ON assignments(course_id)"
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
            "CREATE INDEX IF NOT EXISTS idx_submissions_course ON submissions(course_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_submissions_assignment ON submissions(assignment_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_submissions_user ON submissions(user_id)"
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

        conn.commit()
        logger.info(f"Database initialized at {DB_PATH}")


# Settings operations
def get_setting(key: str) -> Optional[str]:
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
            (key, value, datetime.utcnow(), value, datetime.utcnow()),
        )
        conn.commit()


def get_all_settings() -> dict[str, str]:
    """Get all settings as a dictionary."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM settings")
        return {row["key"]: row["value"] for row in cursor.fetchall()}


# Canvas data operations
def clear_course_data(course_id: str) -> None:
    """Clear all data for a course before re-sync."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM submissions WHERE course_id = ?", (course_id,))
        cursor.execute("DELETE FROM group_members WHERE group_id IN (SELECT id FROM groups WHERE course_id = ?)", (course_id,))
        cursor.execute("DELETE FROM groups WHERE course_id = ?", (course_id,))
        cursor.execute("DELETE FROM users WHERE course_id = ?", (course_id,))
        cursor.execute("DELETE FROM assignments WHERE course_id = ?", (course_id,))
        conn.commit()
        logger.info(f"Cleared existing data for course {course_id}")


def upsert_assignments(course_id: str, assignments: list[dict[str, Any]]) -> int:
    """Insert or update assignments for a course."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        synced_at = datetime.utcnow()

        for assignment in assignments:
            cursor.execute(
                """
                INSERT INTO assignments (id, course_id, name, due_at, points_possible, html_url, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    course_id = ?, name = ?, due_at = ?, points_possible = ?, html_url = ?, synced_at = ?
            """,
                (
                    assignment["id"],
                    course_id,
                    assignment["name"],
                    assignment.get("due_at"),
                    assignment.get("points_possible"),
                    assignment.get("html_url"),
                    synced_at,
                    course_id,
                    assignment["name"],
                    assignment.get("due_at"),
                    assignment.get("points_possible"),
                    assignment.get("html_url"),
                    synced_at,
                ),
            )

        conn.commit()
        return len(assignments)


def upsert_users(course_id: str, users: list[dict[str, Any]]) -> int:
    """Insert or update users for a course."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        synced_at = datetime.utcnow()

        for user in users:
            cursor.execute(
                """
                INSERT INTO users (id, course_id, name, email, synced_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    course_id = ?, name = ?, email = ?, synced_at = ?
            """,
                (
                    user["id"],
                    course_id,
                    user["name"],
                    user.get("email"),
                    synced_at,
                    course_id,
                    user["name"],
                    user.get("email"),
                    synced_at,
                ),
            )

        conn.commit()
        return len(users)


def upsert_submissions(course_id: str, submissions: list[dict[str, Any]]) -> int:
    """Insert or update submissions for a course."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        synced_at = datetime.utcnow()

        for submission in submissions:
            cursor.execute(
                """
                INSERT INTO submissions (id, course_id, user_id, assignment_id, submitted_at, workflow_state, late, score, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    course_id = ?, user_id = ?, assignment_id = ?, submitted_at = ?, workflow_state = ?, late = ?, score = ?, synced_at = ?
            """,
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
                    course_id,
                    submission["user_id"],
                    submission["assignment_id"],
                    submission.get("submitted_at"),
                    submission.get("workflow_state"),
                    1 if submission.get("late") else 0,
                    submission.get("score"),
                    synced_at,
                ),
            )

        conn.commit()
        return len(submissions)


def upsert_groups(course_id: str, groups: list[dict[str, Any]]) -> int:
    """Insert or update groups and their members for a course."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        synced_at = datetime.utcnow()

        for group in groups:
            cursor.execute(
                """
                INSERT INTO groups (id, course_id, name, synced_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    course_id = ?, name = ?, synced_at = ?
            """,
                (
                    group["id"],
                    course_id,
                    group["name"],
                    synced_at,
                    course_id,
                    group["name"],
                    synced_at,
                ),
            )

            # Clear existing members and re-insert
            cursor.execute("DELETE FROM group_members WHERE group_id = ?", (group["id"],))

            for member in group.get("members", []):
                cursor.execute(
                    """
                    INSERT INTO group_members (group_id, user_id, name)
                    VALUES (?, ?, ?)
                """,
                    (group["id"], member.get("user_id") or member.get("id"), member.get("name")),
                )

        conn.commit()
        return len(groups)


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
    course_id: str, assignment_id: Optional[int] = None
) -> list[dict[str, Any]]:
    """Get submissions for a course, optionally filtered by assignment."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if assignment_id:
            cursor.execute(
                """
                SELECT id, course_id, user_id, assignment_id, submitted_at, workflow_state, late, score, synced_at
                FROM submissions WHERE course_id = ? AND assignment_id = ?
            """,
                (course_id, assignment_id),
            )
        else:
            cursor.execute(
                """
                SELECT id, course_id, user_id, assignment_id, submitted_at, workflow_state, late, score, synced_at
                FROM submissions WHERE course_id = ?
            """,
                (course_id,),
            )

        return [dict(row) for row in cursor.fetchall()]


def get_groups(course_id: str) -> list[dict[str, Any]]:
    """Get all groups with members for a course."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Get groups
        cursor.execute(
            """
            SELECT id, course_id, name, synced_at
            FROM groups WHERE course_id = ?
            ORDER BY name
        """,
            (course_id,),
        )
        groups = [dict(row) for row in cursor.fetchall()]

        # Get members for each group
        for group in groups:
            cursor.execute(
                """
                SELECT user_id, name FROM group_members WHERE group_id = ?
            """,
                (group["id"],),
            )
            group["members"] = [
                {"id": row["user_id"], "user_id": row["user_id"], "name": row["name"]}
                for row in cursor.fetchall()
            ]

        return groups


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
            (course_id, datetime.utcnow()),
        )
        conn.commit()
        return cursor.lastrowid


def update_sync_record(
    sync_id: int,
    status: str,
    message: Optional[str] = None,
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
                datetime.utcnow(),
                sync_id,
            ),
        )
        conn.commit()


def get_last_sync(course_id: Optional[str] = None) -> Optional[dict[str, Any]]:
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


def get_sync_history(course_id: Optional[str] = None, limit: int = 10) -> list[dict[str, Any]]:
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
        status_breakdown = {row["workflow_state"]: row["count"] for row in cursor.fetchall()}

        # Late submissions
        cursor.execute(
            "SELECT COUNT(*) as count FROM submissions WHERE course_id = ? AND late = 1",
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
