"""
Tests for Phase 05, Plan 01: assignment_groups table and assignments migration.

Covers:
- Task 1: init_db() creates assignment_groups table with correct columns/index
           and adds assignment_group_id column to assignments via idempotent migration
- Task 2: upsert_assignment_groups(), extended upsert_assignments(),
           clear_refreshable_data(), clear_course_data()
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
# Task 1: Schema — assignment_groups table and assignment_group_id migration
# ---------------------------------------------------------------------------


class TestAssignmentGroupsTableCreation:
    def test_assignment_groups_table_exists(self, fresh_db):
        """init_db() creates assignment_groups table."""
        db = fresh_db
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='assignment_groups'"  # noqa: E501
            )
            assert cur.fetchone() is not None, "assignment_groups table missing"

    def test_assignment_groups_columns(self, fresh_db):
        """assignment_groups table has expected columns."""
        db = fresh_db
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(assignment_groups)")
            cols = {row[1] for row in cur.fetchall()}
        assert "id" in cols
        assert "course_id" in cols
        assert "name" in cols
        assert "position" in cols
        assert "synced_at" in cols

    def test_assignment_groups_index_exists(self, fresh_db):
        """idx_assignment_groups_course index exists."""
        db = fresh_db
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_assignment_groups_course'"  # noqa: E501
            )
            assert cur.fetchone() is not None, (
                "idx_assignment_groups_course index missing"
            )

    def test_assignments_has_assignment_group_id_column(self, fresh_db):
        """assignments table gains assignment_group_id column after init_db()."""
        db = fresh_db
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(assignments)")
            cols = {row[1] for row in cur.fetchall()}
        assert "assignment_group_id" in cols, (
            f"assignment_group_id missing from assignments: {cols}"
        )

    def test_init_db_idempotent(self, fresh_db):
        """Calling init_db() twice does not raise an exception."""
        db = fresh_db
        # Should not raise
        db.init_db()
        db.init_db()

    def test_assignment_group_id_defaults_null(self, fresh_db):
        """Existing assignment rows get NULL for assignment_group_id."""
        db = fresh_db
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            # Insert an assignment without assignment_group_id
            cur.execute(
                "INSERT INTO assignments (id, course_id, name) VALUES (999, 'c1', 'Test')"  # noqa: E501
            )
            conn.commit()
            cur.execute("SELECT assignment_group_id FROM assignments WHERE id = 999")
            row = cur.fetchone()
            assert row[0] is None, f"Expected NULL, got {row[0]}"


# ---------------------------------------------------------------------------
# Task 2: upsert_assignment_groups, extended upsert_assignments, clear funcs
# ---------------------------------------------------------------------------


class TestUpsertAssignmentGroups:
    def test_upsert_returns_count(self, fresh_db):
        """upsert_assignment_groups() returns len(groups)."""
        db = fresh_db
        groups = [
            {"id": 1, "name": "Homework", "position": 1},
            {"id": 2, "name": "Projects", "position": 2},
        ]
        count = db.upsert_assignment_groups("course123", groups)
        assert count == 2

    def test_upsert_inserts_rows(self, fresh_db):
        """Rows are actually inserted into assignment_groups."""
        db = fresh_db
        groups = [{"id": 10, "name": "Labs", "position": 3}]
        db.upsert_assignment_groups("course123", groups)
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM assignment_groups WHERE id = 10")
            row = cur.fetchone()
        assert row is not None
        assert row["name"] == "Labs"
        assert row["course_id"] == "course123"

    def test_upsert_on_conflict_updates(self, fresh_db):
        """Calling upsert again with updated name updates the row."""
        db = fresh_db
        db.upsert_assignment_groups(
            "course123", [{"id": 1, "name": "HW", "position": 1}]
        )
        db.upsert_assignment_groups(
            "course123", [{"id": 1, "name": "Homework Updated", "position": 1}]
        )
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM assignment_groups WHERE id = 1")
            row = cur.fetchone()
        assert row[0] == "Homework Updated"

    def test_upsert_with_conn_none(self, fresh_db):
        """upsert_assignment_groups() with conn=None manages its own connection."""
        db = fresh_db
        groups = [{"id": 5, "name": "Quizzes", "position": 2}]
        result = db.upsert_assignment_groups("cx", groups, conn=None)
        assert result == 1

    def test_upsert_with_existing_conn(self, fresh_db):
        """upsert_assignment_groups() uses caller's connection when provided."""
        db = fresh_db
        groups = [{"id": 6, "name": "Midterm", "position": 3}]
        with db.get_db_connection() as conn:
            result = db.upsert_assignment_groups("cx", groups, conn=conn)
            conn.commit()
        assert result == 1

    def test_upsert_position_optional(self, fresh_db):
        """upsert_assignment_groups() handles missing 'position' key gracefully."""
        db = fresh_db
        groups = [{"id": 7, "name": "Extra Credit"}]  # no position
        count = db.upsert_assignment_groups("cx", groups)
        assert count == 1


class TestUpsertAssignmentsWithGroupId:
    def test_upsert_assignments_saves_assignment_group_id(self, fresh_db):
        """upsert_assignments() persists assignment_group_id."""
        db = fresh_db
        assignments = [
            {
                "id": 100,
                "name": "HW1",
                "due_at": None,
                "points_possible": 10,
                "html_url": None,
                "assignment_group_id": 1,
            }
        ]
        db.upsert_assignments("course123", assignments)
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT assignment_group_id FROM assignments WHERE id = 100")
            row = cur.fetchone()
        assert row[0] == 1, f"assignment_group_id not saved: {row}"

    def test_upsert_assignments_updates_assignment_group_id_on_conflict(self, fresh_db):
        """ON CONFLICT path also updates assignment_group_id."""
        db = fresh_db
        assignments = [{"id": 200, "name": "HW2", "assignment_group_id": 1}]
        db.upsert_assignments("cx", assignments)
        # Update with new group id
        assignments[0]["assignment_group_id"] = 2
        db.upsert_assignments("cx", assignments)
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT assignment_group_id FROM assignments WHERE id = 200")
            row = cur.fetchone()
        assert row[0] == 2

    def test_upsert_assignments_null_group_id_ok(self, fresh_db):
        """upsert_assignments() works when assignment_group_id is absent (null)."""
        db = fresh_db
        assignments = [{"id": 300, "name": "HW3"}]
        db.upsert_assignments("cx", assignments)
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT assignment_group_id FROM assignments WHERE id = 300")
            row = cur.fetchone()
        assert row[0] is None


class TestClearFunctions:
    def test_clear_refreshable_data_removes_assignment_groups(self, fresh_db):
        """clear_refreshable_data() deletes assignment_groups for given course_id."""
        db = fresh_db
        db.upsert_assignment_groups(
            "course123", [{"id": 1, "name": "HW", "position": 1}]
        )
        with db.get_db_connection() as conn:
            db.clear_refreshable_data("course123", conn)
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM assignment_groups WHERE course_id = ?",
                ("course123",),
            )
            count = cur.fetchone()[0]
        assert count == 0, f"Expected 0 after clear, got {count}"

    def test_clear_refreshable_data_only_clears_target_course(self, fresh_db):
        """clear_refreshable_data() does not delete rows from other courses."""
        db = fresh_db
        db.upsert_assignment_groups(
            "course_A", [{"id": 1, "name": "HW", "position": 1}]
        )
        db.upsert_assignment_groups(
            "course_B", [{"id": 2, "name": "Projects", "position": 2}]
        )
        with db.get_db_connection() as conn:
            db.clear_refreshable_data("course_A", conn)
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM assignment_groups WHERE course_id = ?",
                ("course_B",),
            )
            count = cur.fetchone()[0]
        assert count == 1, "course_B rows were incorrectly deleted"

    def test_clear_course_data_removes_assignment_groups(self, fresh_db):
        """clear_course_data() also deletes assignment_groups for given course_id."""
        db = fresh_db
        db.upsert_assignment_groups(
            "course123", [{"id": 1, "name": "HW", "position": 1}]
        )
        db.clear_course_data("course123")
        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM assignment_groups WHERE course_id = ?",
                ("course123",),
            )
            count = cur.fetchone()[0]
        assert count == 0, f"Expected 0 after clear_course_data, got {count}"

    def test_re_insert_after_clear_no_conflict(self, fresh_db):
        """After clear_refreshable_data(), can upsert groups again without error."""
        db = fresh_db
        groups = [{"id": 1, "name": "HW", "position": 1}]
        db.upsert_assignment_groups("course123", groups)
        with db.get_db_connection() as conn:
            db.clear_refreshable_data("course123", conn)
        # Should not raise
        db.upsert_assignment_groups("course123", groups)
