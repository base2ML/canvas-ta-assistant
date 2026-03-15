"""
Tests for Phase 06, Plan 01: ta_users table, submissions column migrations, and upsert.

Covers:
- TestTAUsersTable: init_db() creates ta_users table with correct columns/index
- TestSubmissionsMigration: submissions table gains grader_id and graded_at columns
- TestUpsertTAUsers: upsert_ta_users() inserts and updates on conflict, returns count
- TestClearRefreshableData: clear_refreshable_data() clears ta_users for course_id
"""

import pytest


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """Fixture providing a fresh database in a temp directory."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    # Re-import database after env change so DATA_DIR is picked up
    import importlib

    import database as db

    importlib.reload(db)
    db.init_db()
    return db


# ---------------------------------------------------------------------------
# TestTAUsersTable: schema tests
# ---------------------------------------------------------------------------


class TestTAUsersTable:
    def test_ta_users_table_exists(self, fresh_db):
        """init_db() creates ta_users table."""
        db = fresh_db
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='ta_users'"
            )
            assert cur.fetchone() is not None, "ta_users table missing"

    def test_ta_users_columns(self, fresh_db):
        """ta_users has columns id, course_id, name, email, enrollment_type, synced_at."""  # noqa: E501
        db = fresh_db
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(ta_users)")
            cols = {row[1] for row in cur.fetchall()}
        assert "id" in cols, f"id missing from ta_users: {cols}"
        assert "course_id" in cols, f"course_id missing from ta_users: {cols}"
        assert "name" in cols, f"name missing from ta_users: {cols}"
        assert "email" in cols, f"email missing from ta_users: {cols}"
        assert "enrollment_type" in cols, (
            f"enrollment_type missing from ta_users: {cols}"
        )
        assert "synced_at" in cols, f"synced_at missing from ta_users: {cols}"

    def test_ta_users_index_exists(self, fresh_db):
        """idx_ta_users_course index exists on ta_users(course_id)."""
        db = fresh_db
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_ta_users_course'"  # noqa: E501
            )
            assert cur.fetchone() is not None, "idx_ta_users_course index missing"


# ---------------------------------------------------------------------------
# TestSubmissionsMigration: grader_id and graded_at column migrations
# ---------------------------------------------------------------------------


class TestSubmissionsMigration:
    def test_grader_id_column_exists(self, fresh_db):
        """submissions table has grader_id column after init_db()."""
        db = fresh_db
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(submissions)")
            cols = {row[1] for row in cur.fetchall()}
        assert "grader_id" in cols, f"grader_id missing from submissions: {cols}"

    def test_graded_at_column_exists(self, fresh_db):
        """submissions table has graded_at column after init_db()."""
        db = fresh_db
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(submissions)")
            cols = {row[1] for row in cur.fetchall()}
        assert "graded_at" in cols, f"graded_at missing from submissions: {cols}"

    def test_migration_idempotent(self, fresh_db):
        """Calling init_db() twice on same DB does not raise."""
        db = fresh_db
        # Should not raise on second call
        db.init_db()
        db.init_db()


# ---------------------------------------------------------------------------
# TestUpsertTAUsers: upsert behavior
# ---------------------------------------------------------------------------


class TestUpsertTAUsers:
    def test_insert(self, fresh_db):
        """upsert_ta_users() inserts a new TA user with correct fields."""
        db = fresh_db
        ta_users = [
            {
                "id": 1001,
                "name": "Alice TA",
                "email": "alice@example.com",
                "enrollment_type": "ta",
            }
        ]
        db.upsert_ta_users("course123", ta_users)
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM ta_users WHERE id = 1001")
            row = cur.fetchone()
        assert row is not None, "ta_user row not found after insert"
        assert row["name"] == "Alice TA"
        assert row["email"] == "alice@example.com"
        assert row["enrollment_type"] == "ta"
        assert row["course_id"] == "course123"

    def test_update_on_conflict(self, fresh_db):
        """upsert_ta_users() updates name/email/enrollment_type on id conflict."""
        db = fresh_db
        # Initial insert
        db.upsert_ta_users(
            "course123",
            [
                {
                    "id": 1001,
                    "name": "Alice TA",
                    "email": "alice@example.com",
                    "enrollment_type": "ta",
                }
            ],
        )
        # Update on conflict
        db.upsert_ta_users(
            "course123",
            [
                {
                    "id": 1001,
                    "name": "Alice Updated",
                    "email": "alice2@example.com",
                    "enrollment_type": "teacher",
                }
            ],
        )
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT name, email, enrollment_type FROM ta_users WHERE id = 1001"
            )
            row = cur.fetchone()
        assert row["name"] == "Alice Updated"
        assert row["email"] == "alice2@example.com"
        assert row["enrollment_type"] == "teacher"

    def test_returns_count(self, fresh_db):
        """upsert_ta_users() returns len(ta_users) inserted/updated."""
        db = fresh_db
        ta_users = [
            {
                "id": 1001,
                "name": "Alice TA",
                "email": "alice@example.com",
                "enrollment_type": "ta",
            },
            {
                "id": 1002,
                "name": "Bob TA",
                "email": "bob@example.com",
                "enrollment_type": "ta",
            },
        ]
        count = db.upsert_ta_users("course123", ta_users)
        assert count == 2


# ---------------------------------------------------------------------------
# TestClearRefreshableData: ta_users cleared by course_id
# ---------------------------------------------------------------------------


class TestClearRefreshableData:
    def test_ta_users_cleared(self, fresh_db):
        """clear_refreshable_data() deletes ta_users rows for course_id."""
        db = fresh_db
        db.upsert_ta_users(
            "course123",
            [
                {
                    "id": 1001,
                    "name": "Alice TA",
                    "email": "alice@example.com",
                    "enrollment_type": "ta",
                }
            ],
        )
        with db.get_db_connection() as conn:
            db.clear_refreshable_data("course123", conn)
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM ta_users WHERE course_id = ?", ("course123",)
            )
            count = cur.fetchone()[0]
        assert count == 0, f"Expected 0 ta_users after clear, got {count}"

    def test_ta_users_other_course_preserved(self, fresh_db):
        """clear_refreshable_data() does not delete ta_users for a different course_id."""  # noqa: E501
        db = fresh_db
        db.upsert_ta_users(
            "course_A",
            [
                {
                    "id": 1001,
                    "name": "Alice TA",
                    "email": "alice@example.com",
                    "enrollment_type": "ta",
                }
            ],
        )
        db.upsert_ta_users(
            "course_B",
            [
                {
                    "id": 1002,
                    "name": "Bob TA",
                    "email": "bob@example.com",
                    "enrollment_type": "ta",
                }
            ],
        )
        with db.get_db_connection() as conn:
            db.clear_refreshable_data("course_A", conn)
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM ta_users WHERE course_id = ?", ("course_B",)
            )
            count = cur.fetchone()[0]
        assert count == 1, f"course_B ta_users were incorrectly deleted: {count}"
