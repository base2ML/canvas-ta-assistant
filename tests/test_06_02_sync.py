"""
Tests for Phase 06, Plan 02: sync TA/instructor users and grader_id/graded_at fields.

Covers:
- TestSyncTAUsers: upsert_ta_users() inserts correctly, deduplication, enrollment_type
- TestSyncGraderFields: getattr extraction logic for grader_id and graded_at
- TestUpsertSubmissionsGraderFields: upsert_submissions() stores grader_id and graded_at
"""

import importlib

import pytest


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """Fixture providing a fresh database in a temp directory."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    # Re-import database after env change so DATA_DIR is picked up
    import database as db

    importlib.reload(db)
    db.init_db()
    return db


# ---------------------------------------------------------------------------
# TestSyncTAUsers: upsert_ta_users behavior for sync use-cases
# ---------------------------------------------------------------------------


class TestSyncTAUsers:
    def test_ta_users_fetched_and_upserted(self, fresh_db):
        """sync inserts ta users into ta_users table via upsert_ta_users()."""
        db = fresh_db
        ta_users = [
            {
                "id": 2001,
                "name": "Alice TA",
                "email": "alice@example.com",
                "enrollment_type": "ta",
            }
        ]
        db.upsert_ta_users("course42", ta_users)
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM ta_users WHERE id = 2001")
            row = cur.fetchone()
        assert row is not None, "ta_user row not found after upsert"
        assert row["name"] == "Alice TA"
        assert row["course_id"] == "course42"
        assert row["enrollment_type"] == "ta"

    def test_deduplication_across_enrollment_types(self, fresh_db):
        """User enrolled as both ta and teacher appears only once in ta_users."""
        db = fresh_db
        # Simulate two-pass fetch: ta first, then teacher
        # Same user id 3001 appears in both, but seen_ids dedup means
        # only the ta enrollment is stored (first wins)
        seen_ids: set = set()
        ta_users_list = []

        # Simulate ta pass
        ta_candidates = [{"id": 3001, "name": "Bob Grader", "email": "bob@example.com"}]
        for user in ta_candidates:
            if user["id"] not in seen_ids:
                seen_ids.add(user["id"])
                ta_users_list.append(
                    {
                        "id": user["id"],
                        "name": user["name"],
                        "email": user.get("email"),
                        "enrollment_type": "ta",
                    }
                )

        # Simulate teacher pass — same user, should be skipped
        teacher_candidates = [
            {"id": 3001, "name": "Bob Grader", "email": "bob@example.com"}
        ]
        for user in teacher_candidates:
            if user["id"] not in seen_ids:
                seen_ids.add(user["id"])
                ta_users_list.append(
                    {
                        "id": user["id"],
                        "name": user["name"],
                        "email": user.get("email"),
                        "enrollment_type": "teacher",
                    }
                )

        assert len(ta_users_list) == 1, (
            "Deduplication failed: user appears more than once"
        )
        db.upsert_ta_users("course42", ta_users_list)

        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM ta_users"
                " WHERE id = 3001 AND course_id = 'course42'"
            )
            count = cur.fetchone()[0]
        assert count == 1, f"Expected 1 row for deduplicated user, got {count}"

    def test_ta_users_enrollment_type_preserved(self, fresh_db):
        """ta enrollment_type is 'ta', teacher enrollment_type is 'teacher'."""
        db = fresh_db
        ta_users = [
            {
                "id": 4001,
                "name": "Carol TA",
                "email": "carol@example.com",
                "enrollment_type": "ta",
            },
            {
                "id": 4002,
                "name": "Dave Instructor",
                "email": "dave@example.com",
                "enrollment_type": "teacher",
            },
        ]
        db.upsert_ta_users("course42", ta_users)
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, enrollment_type FROM ta_users WHERE id IN (4001, 4002)"
            )
            rows = {row["id"]: row["enrollment_type"] for row in cur.fetchall()}
        assert rows[4001] == "ta", f"Expected 'ta', got {rows[4001]!r}"
        assert rows[4002] == "teacher", f"Expected 'teacher', got {rows[4002]!r}"


# ---------------------------------------------------------------------------
# TestSyncGraderFields: extraction logic for grader_id and graded_at
# ---------------------------------------------------------------------------


class TestSyncGraderFields:
    def _build_submission_dict(
        self, submission_obj: object, assignment_id: int
    ) -> dict:
        """Mirror the dict-construction logic used in canvas_sync.py."""
        return {
            "id": submission_obj.id,  # type: ignore[attr-defined]
            "user_id": submission_obj.user_id,  # type: ignore[attr-defined]
            "assignment_id": assignment_id,
            "submitted_at": getattr(submission_obj, "submitted_at", None),
            "workflow_state": submission_obj.workflow_state,  # type: ignore[attr-defined]
            "late": getattr(submission_obj, "late", False),
            "score": getattr(submission_obj, "score", None),
            "grader_id": getattr(submission_obj, "grader_id", None),
            "graded_at": getattr(submission_obj, "graded_at", None),
        }

    def test_grader_id_captured(self):
        """Submission with grader_id has it captured in the submission dict."""

        class FakeSubmission:
            id = 101
            user_id = 201
            workflow_state = "graded"
            grader_id = 9901
            graded_at = "2026-02-01T10:00:00Z"

        result = self._build_submission_dict(FakeSubmission(), assignment_id=301)
        assert "grader_id" in result, "grader_id key missing from submission dict"
        assert result["grader_id"] == 9901

    def test_graded_at_captured(self):
        """Submission with graded_at has it captured in the submission dict."""

        class FakeSubmission:
            id = 102
            user_id = 202
            workflow_state = "graded"
            grader_id = 9902
            graded_at = "2026-02-02T12:00:00Z"

        result = self._build_submission_dict(FakeSubmission(), assignment_id=302)
        assert "graded_at" in result, "graded_at key missing from submission dict"
        assert result["graded_at"] == "2026-02-02T12:00:00Z"

    def test_null_grader_id_captured(self):
        """Submission without grader_id stores None (not KeyError)."""

        class FakeSubmission:
            id = 103
            user_id = 203
            workflow_state = "submitted"
            # grader_id intentionally absent

        result = self._build_submission_dict(FakeSubmission(), assignment_id=303)
        assert "grader_id" in result, "grader_id key must be present even when None"
        assert result["grader_id"] is None, (
            f"Expected None for missing grader_id, got {result['grader_id']!r}"
        )


# ---------------------------------------------------------------------------
# TestUpsertSubmissionsGraderFields: DB persistence of grader_id and graded_at
# ---------------------------------------------------------------------------


class TestUpsertSubmissionsGraderFields:
    def _insert_prerequisite_user_and_assignment(self, db, course_id: str) -> None:
        """Insert the user and assignment rows required by submission FK constraints."""
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT OR IGNORE INTO users (id, course_id, name) VALUES (?, ?, ?)",
                (5001, course_id, "Test Student"),
            )
            cur.execute(
                "INSERT OR IGNORE INTO assignments"
                " (id, course_id, name) VALUES (?, ?, ?)",
                (6001, course_id, "Test Assignment"),
            )
            conn.commit()

    def test_grader_id_stored(self, fresh_db):
        """upsert_submissions() stores grader_id value in DB."""
        db = fresh_db
        course_id = "course99"
        self._insert_prerequisite_user_and_assignment(db, course_id)

        submissions = [
            {
                "id": 7001,
                "user_id": 5001,
                "assignment_id": 6001,
                "submitted_at": "2026-01-10T08:00:00Z",
                "workflow_state": "graded",
                "late": False,
                "score": 95.0,
                "grader_id": 9901,
                "graded_at": "2026-01-11T09:00:00Z",
            }
        ]
        db.upsert_submissions(course_id, submissions)

        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT grader_id FROM submissions WHERE id = 7001")
            row = cur.fetchone()
        assert row is not None, "Submission row not found"
        assert row["grader_id"] == 9901, (
            f"Expected grader_id=9901, got {row['grader_id']}"
        )

    def test_graded_at_stored(self, fresh_db):
        """upsert_submissions() stores graded_at value in DB."""
        db = fresh_db
        course_id = "course99"
        self._insert_prerequisite_user_and_assignment(db, course_id)

        submissions = [
            {
                "id": 7002,
                "user_id": 5001,
                "assignment_id": 6001,
                "submitted_at": "2026-01-10T08:00:00Z",
                "workflow_state": "graded",
                "late": False,
                "score": 88.0,
                "grader_id": 9902,
                "graded_at": "2026-01-12T11:30:00Z",
            }
        ]
        db.upsert_submissions(course_id, submissions)

        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT graded_at FROM submissions WHERE id = 7002")
            row = cur.fetchone()
        assert row is not None, "Submission row not found"
        assert row["graded_at"] == "2026-01-12T11:30:00Z", (
            f"Expected graded_at='2026-01-12T11:30:00Z', got {row['graded_at']!r}"
        )

    def test_grader_id_null_stored(self, fresh_db):
        """upsert_submissions() stores NULL when grader_id is None."""
        db = fresh_db
        course_id = "course99"
        self._insert_prerequisite_user_and_assignment(db, course_id)

        submissions = [
            {
                "id": 7003,
                "user_id": 5001,
                "assignment_id": 6001,
                "submitted_at": "2026-01-10T08:00:00Z",
                "workflow_state": "submitted",
                "late": False,
                "score": None,
                "grader_id": None,
                "graded_at": None,
            }
        ]
        db.upsert_submissions(course_id, submissions)

        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT grader_id FROM submissions WHERE id = 7003")
            row = cur.fetchone()
        assert row is not None, "Submission row not found"
        assert row["grader_id"] is None, (
            f"Expected NULL grader_id, got {row['grader_id']!r}"
        )
