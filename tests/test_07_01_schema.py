"""
Tests for Phase 07, Plan 01: grading_deadlines table and upsert functions.

Covers:
- TestGradingDeadlinesTable: init_db() creates grading_deadlines table with correct
  columns/index
- TestUpsertGradingDeadline: upsert_grading_deadline() inserts and updates on conflict
- TestGradingDeadlineMigrationIdempotent: calling init_db() twice does not raise
"""

import sqlite3
from datetime import UTC, datetime

import pytest


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """Fixture providing a fresh database in a temp directory."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    import importlib

    import database as db

    importlib.reload(db)
    db.init_db()
    return db


# ---------------------------------------------------------------------------
# TestGradingDeadlinesTable: schema tests
# ---------------------------------------------------------------------------


class TestGradingDeadlinesTable:
    def test_table_exists(self, fresh_db):
        """init_db() creates grading_deadlines table."""
        db = fresh_db
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master"  # noqa: E501
                " WHERE type='table' AND name='grading_deadlines'"
            )
            assert cur.fetchone() is not None, "grading_deadlines table missing"

    def test_table_columns(self, fresh_db):
        """grading_deadlines has expected columns."""
        db = fresh_db
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(grading_deadlines)")
            cols = {row[1] for row in cur.fetchall()}
        expected = {
            "id",
            "course_id",
            "assignment_id",
            "deadline_at",
            "turnaround_days",
            "is_override",
            "note",
            "created_at",
            "updated_at",
        }
        for col in expected:
            assert col in cols, f"Column '{col}' missing from grading_deadlines: {cols}"

    def test_unique_constraint_exists(self, fresh_db):
        """grading_deadlines enforces UNIQUE(course_id, assignment_id)."""
        db = fresh_db
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            # Insert one row directly
            cur.execute(
                "INSERT INTO grading_deadlines"
                " (course_id, assignment_id, deadline_at, turnaround_days)"
                " VALUES ('c1', 1, '2026-04-01T00:00:00', 7)"
            )
            conn.commit()
            # Second insert with same (course_id, assignment_id) should raise
            with pytest.raises(sqlite3.IntegrityError):
                cur.execute(
                    "INSERT INTO grading_deadlines"
                    " (course_id, assignment_id, deadline_at, turnaround_days)"
                    " VALUES ('c1', 1, '2026-04-15T00:00:00', 5)"
                )
                conn.commit()

    def test_course_index_exists(self, fresh_db):
        """idx_grading_deadlines_course index exists on grading_deadlines(course_id)."""
        db = fresh_db
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master"
                " WHERE type='index' AND name='idx_grading_deadlines_course'"
            )
            assert cur.fetchone() is not None, (
                "idx_grading_deadlines_course index missing"
            )


# ---------------------------------------------------------------------------
# TestUpsertGradingDeadline: upsert behavior
# ---------------------------------------------------------------------------


class TestUpsertGradingDeadline:
    def test_insert(self, fresh_db):
        """upsert_grading_deadline() inserts a new row with correct fields."""
        db = fresh_db
        deadline = datetime(2026, 4, 1, 0, 0, 0, tzinfo=UTC)
        db.upsert_grading_deadline("c1", 1, deadline, 7)

        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM grading_deadlines"
                " WHERE course_id='c1' AND assignment_id=1"
            )
            row = cur.fetchone()
        assert row is not None, "grading_deadlines row not found after insert"
        assert row["turnaround_days"] == 7
        assert "2026-04-01" in row["deadline_at"]

    def test_update_on_conflict(self, fresh_db):
        """upsert_grading_deadline() updates deadline_at and updated_at on conflict."""
        db = fresh_db
        deadline1 = datetime(2026, 4, 1, 0, 0, 0, tzinfo=UTC)
        deadline2 = datetime(2026, 4, 15, 0, 0, 0, tzinfo=UTC)

        db.upsert_grading_deadline("c1", 1, deadline1, 7)

        # Second upsert with different deadline
        db.upsert_grading_deadline("c1", 1, deadline2, 5)

        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT updated_at, deadline_at FROM grading_deadlines"
                " WHERE course_id='c1' AND assignment_id=1"
            )
            row2 = cur.fetchone()

        assert "2026-04-15" in row2["deadline_at"], (
            "deadline_at not updated on conflict"
        )
        assert row2["turnaround_days"] == 5, "turnaround_days not updated on conflict"

    def test_is_override_preserved(self, fresh_db):
        """upsert_grading_deadline_if_not_override() preserves is_override rows."""
        db = fresh_db
        deadline1 = datetime(2026, 4, 1, 0, 0, 0, tzinfo=UTC)
        deadline2 = datetime(2026, 4, 20, 0, 0, 0, tzinfo=UTC)

        # Insert with is_override=True
        db.upsert_grading_deadline("c1", 1, deadline1, 7, is_override=True)

        # Try to overwrite with the "if not override" variant
        db.upsert_grading_deadline_if_not_override("c1", 1, deadline2, 3)

        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT deadline_at, is_override FROM grading_deadlines"
                " WHERE course_id='c1' AND assignment_id=1"
            )
            row = cur.fetchone()

        # deadline_at should remain as deadline1 (override preserved)
        assert "2026-04-01" in row["deadline_at"], (
            f"Override row was overwritten: {row['deadline_at']}"
        )
        assert row["is_override"] in (1, True), "is_override should remain True"

    def test_override_flag_stored(self, fresh_db):
        """upsert_grading_deadline() stores is_override=True in DB as 1."""
        db = fresh_db
        deadline = datetime(2026, 4, 1, 0, 0, 0, tzinfo=UTC)
        db.upsert_grading_deadline("c1", 1, deadline, 7, is_override=True)

        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT is_override FROM grading_deadlines"
                " WHERE course_id='c1' AND assignment_id=1"
            )
            row = cur.fetchone()

        assert row["is_override"] in (1, True), (
            f"is_override not stored as truthy: {row['is_override']}"
        )


# ---------------------------------------------------------------------------
# TestGradingDeadlineMigrationIdempotent: init_db() idempotent
# ---------------------------------------------------------------------------


class TestGradingDeadlineMigrationIdempotent:
    def test_init_db_twice(self, fresh_db):
        """Calling init_db() twice does not raise an exception."""
        db = fresh_db
        db.init_db()
        db.init_db()  # Should not raise
