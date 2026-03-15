"""
Tests for Phase 07, Plans 02-03: settings turnaround field and deadline CRUD endpoints.

Covers:
- TestSettings: default_grading_turnaround_days field on GET/PUT /api/settings
- TestGetDeadlines: GET /api/dashboard/grading-deadlines/{course_id}
- TestPutDeadline: PUT /api/dashboard/grading-deadlines/{course_id}/{assignment_id}
- TestPropagateDefaults: POST .../propagate-defaults
"""

import asyncio
from datetime import UTC

import pytest


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def fresh_db(monkeypatch, tmp_path):
    """Return a fresh database and patch database module to use it."""
    import database as db_module

    db_path = tmp_path / "test_canvas.db"
    monkeypatch.setattr(db_module, "DB_PATH", str(db_path))
    db_module.init_db()
    return db_module


async def _get(app, path):
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        return await ac.get(path)


async def _put(app, path, json_body):
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        return await ac.put(path, json=json_body)


async def _post(app, path, json_body=None):
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        return await ac.post(path, json=json_body or {})


# ---------------------------------------------------------------------------
# TestSettings: default_grading_turnaround_days
# ---------------------------------------------------------------------------


class TestSettings:
    def test_get_settings_returns_default_turnaround(self, fresh_db):  # noqa: ARG002
        """GET /api/settings returns default_grading_turnaround_days == 7."""
        from main import app

        resp = asyncio.run(_get(app, "/api/settings"))
        assert resp.status_code == 200
        data = resp.json()
        assert "default_grading_turnaround_days" in data, (
            f"default_grading_turnaround_days missing from settings: {data}"
        )
        assert data["default_grading_turnaround_days"] == 7, (
            f"Expected default=7, got {data['default_grading_turnaround_days']}"
        )

    def test_put_settings_persists_turnaround(self, fresh_db):  # noqa: ARG002
        """PUT /api/settings with default_grading_turnaround_days=5 persists it."""
        from main import app

        async def run():
            from httpx import ASGITransport, AsyncClient

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                put_resp = await ac.put(
                    "/api/settings", json={"default_grading_turnaround_days": 5}
                )
                get_resp = await ac.get("/api/settings")
            return put_resp, get_resp

        put_resp, get_resp = asyncio.run(run())
        assert put_resp.status_code == 200
        data = get_resp.json()
        assert data["default_grading_turnaround_days"] == 5, (
            f"Expected 5 after PUT, got {data.get('default_grading_turnaround_days')}"
        )


# ---------------------------------------------------------------------------
# TestGetDeadlines: GET /api/dashboard/grading-deadlines/{course_id}
# ---------------------------------------------------------------------------


class TestGetDeadlines:
    def test_returns_200(self, fresh_db):  # noqa: ARG002
        """GET grading-deadlines with no data returns 200 with empty list."""
        from main import app

        resp = asyncio.run(_get(app, "/api/dashboard/grading-deadlines/test_course"))
        assert resp.status_code == 200
        data = resp.json()
        assert "assignments" in data, f"Response missing 'assignments' key: {data}"
        assert isinstance(data["assignments"], list)

    def test_has_deadline_fields(self, fresh_db):
        """Deadline row appears in GET response with expected fields."""
        from datetime import datetime

        from main import app

        db = fresh_db
        # Insert assignment, user, and deadline
        db.upsert_users("test_course", [{"id": 1, "name": "Student", "email": None}])
        db.upsert_assignments(
            "test_course",
            [
                {
                    "id": 101,
                    "name": "HW 1",
                    "due_at": "2026-03-01T23:59:00Z",
                    "points_possible": 10,
                    "html_url": "",
                    "assignment_group_id": None,
                }
            ],
        )
        deadline = datetime(2026, 4, 1, 0, 0, 0, tzinfo=UTC)
        db.upsert_grading_deadline("test_course", 101, deadline, 7)

        resp = asyncio.run(_get(app, "/api/dashboard/grading-deadlines/test_course"))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["assignments"]) >= 1, "Expected at least one assignment item"
        item = data["assignments"][0]
        for field in (
            "assignment_id",
            "deadline_at",
            "turnaround_days",
            "is_override",
            "is_overdue",
        ):
            assert field in item, f"Field '{field}' missing from response item: {item}"


# ---------------------------------------------------------------------------
# TestPutDeadline: PUT /api/dashboard/grading-deadlines/{course_id}/{assignment_id}
# ---------------------------------------------------------------------------


class TestPutDeadline:
    def test_put_updates_deadline(self, fresh_db):
        """PUT grading-deadlines/{course}/{assignment_id} returns 200."""
        from main import app

        db = fresh_db
        db.upsert_assignments(
            "course1",
            [
                {
                    "id": 1,
                    "name": "HW 1",
                    "due_at": "2026-03-01T23:59:00Z",
                    "points_possible": 10,
                    "html_url": "",
                    "assignment_group_id": None,
                }
            ],
        )

        resp = asyncio.run(
            _put(
                app,
                "/api/dashboard/grading-deadlines/course1/1",
                {"deadline_date": "2026-04-01", "is_override": True},
            )
        )
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}: {resp.text}"
        )

    def test_put_sets_is_override(self, fresh_db):
        """After PUT with is_override=true, grading_deadlines row has is_override=1."""
        from main import app

        db = fresh_db
        db.upsert_assignments(
            "course1",
            [
                {
                    "id": 1,
                    "name": "HW 1",
                    "due_at": "2026-03-01T23:59:00Z",
                    "points_possible": 10,
                    "html_url": "",
                    "assignment_group_id": None,
                }
            ],
        )

        asyncio.run(
            _put(
                app,
                "/api/dashboard/grading-deadlines/course1/1",
                {"deadline_date": "2026-04-01", "is_override": True},
            )
        )

        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT is_override FROM grading_deadlines"
                " WHERE course_id='course1' AND assignment_id=1"
            )
            row = cur.fetchone()

        assert row is not None, "No grading_deadlines row found after PUT"
        assert row["is_override"] in (1, True), (
            f"is_override not set after PUT: {row['is_override']}"
        )


# ---------------------------------------------------------------------------
# TestPropagateDefaults: POST .../propagate-defaults
# ---------------------------------------------------------------------------


class TestPropagateDefaults:
    def test_propagates_for_assignments_with_due_at(self, fresh_db):
        """POST propagate-defaults creates deadline rows for assignments with due_at."""
        from main import app

        db = fresh_db
        db.upsert_assignments(
            "course1",
            [
                {
                    "id": 1,
                    "name": "HW 1",
                    "due_at": "2026-03-01T23:59:00Z",
                    "points_possible": 10,
                    "html_url": "",
                    "assignment_group_id": None,
                }
            ],
        )

        resp = asyncio.run(
            _post(app, "/api/dashboard/grading-deadlines/course1/propagate-defaults")
        )
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}: {resp.text}"
        )

        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM grading_deadlines"
                " WHERE course_id='course1' AND assignment_id=1"
            )
            count = cur.fetchone()[0]

        assert count == 1, (
            f"Expected 1 deadline row after propagate-defaults, got {count}"
        )

    def test_skips_null_due_at(self, fresh_db):
        """POST propagate-defaults skips assignments with due_at=NULL."""
        from main import app

        db = fresh_db
        db.upsert_assignments(
            "course1",
            [
                {
                    "id": 2,
                    "name": "HW No Due Date",
                    "due_at": None,
                    "points_possible": 10,
                    "html_url": "",
                    "assignment_group_id": None,
                }
            ],
        )

        asyncio.run(
            _post(app, "/api/dashboard/grading-deadlines/course1/propagate-defaults")
        )

        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM grading_deadlines"
                " WHERE course_id='course1' AND assignment_id=2"
            )
            count = cur.fetchone()[0]

        assert count == 0, f"Expected 0 deadline rows for null due_at, got {count}"

    def test_skips_existing_override(self, fresh_db):
        """POST propagate-defaults does not overwrite existing is_override=1 rows."""
        from datetime import datetime

        from main import app

        db = fresh_db
        db.upsert_assignments(
            "course1",
            [
                {
                    "id": 3,
                    "name": "HW 3",
                    "due_at": "2026-03-01T23:59:00Z",
                    "points_possible": 10,
                    "html_url": "",
                    "assignment_group_id": None,
                }
            ],
        )

        # Insert manual override deadline
        override_deadline = datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC)
        db.upsert_grading_deadline("course1", 3, override_deadline, 7, is_override=True)

        asyncio.run(
            _post(app, "/api/dashboard/grading-deadlines/course1/propagate-defaults")
        )

        with db.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT deadline_at, is_override FROM grading_deadlines"
                " WHERE course_id='course1' AND assignment_id=3"
            )
            row = cur.fetchone()

        assert row is not None
        assert "2026-05-01" in row["deadline_at"], (
            f"Override deadline overwritten by propagate-defaults: {row['deadline_at']}"
        )
        assert row["is_override"] in (1, True)
