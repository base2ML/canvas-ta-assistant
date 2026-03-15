"""Tests for grader_name JOIN on get_submissions() and ta_breakdown_mode settings."""

import pytest


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def fresh_db(monkeypatch, tmp_path):
    """Return a fresh in-memory database and patch database module to use it."""
    import database as db_module

    db_path = tmp_path / "test_canvas.db"

    # Patch the DB_PATH so all db functions use our temp file
    monkeypatch.setattr(db_module, "DB_PATH", str(db_path))

    # Initialise schema
    db_module.init_db()

    return db_module


# ---------------------------------------------------------------------------
# TestSubmissionsGraderName
# ---------------------------------------------------------------------------


class TestSubmissionsGraderName:
    """get_submissions() must return grader_id and grader_name from ta_users JOIN."""

    def test_grader_name_resolved(self, fresh_db):  # noqa: ARG002
        """grader_id in ta_users resolves grader_name to that user's name."""
        db = fresh_db
        course_id = "C1"

        # Insert a TA user
        db.upsert_ta_users(
            course_id,
            [
                {
                    "id": 999,
                    "name": "Alice TA",
                    "email": "alice@example.com",
                    "enrollment_type": "ta",
                },
            ],
        )

        # Insert a user (student) so foreign key is not violated
        db.upsert_users(course_id, [{"id": 1, "name": "Student One", "email": None}])

        # Insert an assignment
        db.upsert_assignments(
            course_id,
            [
                {
                    "id": 101,
                    "name": "HW1",
                    "due_at": None,
                    "points_possible": 10,
                    "html_url": "",
                    "assignment_group_id": None,
                },
            ],
        )

        # Insert a submission with grader_id pointing to the TA
        db.upsert_submissions(
            course_id,
            [
                {
                    "id": 201,
                    "user_id": 1,
                    "assignment_id": 101,
                    "submitted_at": "2026-01-01T10:00:00Z",
                    "workflow_state": "graded",
                    "late": False,
                    "score": 9.0,
                    "grader_id": 999,
                    "graded_at": "2026-01-02T10:00:00Z",
                }
            ],
        )

        submissions = db.get_submissions(course_id)
        assert len(submissions) == 1
        sub = submissions[0]
        assert sub["grader_id"] == 999
        assert sub["grader_name"] == "Alice TA", (
            f"Expected 'Alice TA', got {sub.get('grader_name')!r}"
        )

    def test_grader_name_null_when_no_match(self, fresh_db):
        """When grader_id is not in ta_users, grader_name is None."""
        db = fresh_db
        course_id = "C2"

        db.upsert_users(course_id, [{"id": 2, "name": "Student Two", "email": None}])
        db.upsert_assignments(
            course_id,
            [
                {
                    "id": 102,
                    "name": "HW2",
                    "due_at": None,
                    "points_possible": 10,
                    "html_url": "",
                    "assignment_group_id": None,
                },
            ],
        )
        db.upsert_submissions(
            course_id,
            [
                {
                    "id": 202,
                    "user_id": 2,
                    "assignment_id": 102,
                    "submitted_at": "2026-01-01T10:00:00Z",
                    "workflow_state": "graded",
                    "late": False,
                    "score": 8.0,
                    "grader_id": 9999,  # no matching ta_users row
                    "graded_at": "2026-01-02T10:00:00Z",
                }
            ],
        )

        submissions = db.get_submissions(course_id)
        assert len(submissions) == 1
        sub = submissions[0]
        assert sub["grader_id"] == 9999
        assert sub["grader_name"] is None, (
            f"Expected None, got {sub.get('grader_name')!r}"
        )

    def test_grader_name_null_when_grader_id_null(self, fresh_db):
        """When grader_id is None, grader_name is None."""
        db = fresh_db
        course_id = "C3"

        db.upsert_users(course_id, [{"id": 3, "name": "Student Three", "email": None}])
        db.upsert_assignments(
            course_id,
            [
                {
                    "id": 103,
                    "name": "HW3",
                    "due_at": None,
                    "points_possible": 10,
                    "html_url": "",
                    "assignment_group_id": None,
                },
            ],
        )
        db.upsert_submissions(
            course_id,
            [
                {
                    "id": 203,
                    "user_id": 3,
                    "assignment_id": 103,
                    "submitted_at": "2026-01-01T10:00:00Z",
                    "workflow_state": "submitted",
                    "late": False,
                    "score": None,
                    "grader_id": None,
                    "graded_at": None,
                }
            ],
        )

        submissions = db.get_submissions(course_id)
        assert len(submissions) == 1
        sub = submissions[0]
        assert sub.get("grader_id") is None
        assert sub.get("grader_name") is None, (
            f"Expected None, got {sub.get('grader_name')!r}"
        )

    def test_grader_id_returned(self, fresh_db):
        """grader_id field is present on each submission dict."""
        db = fresh_db
        course_id = "C4"

        db.upsert_users(course_id, [{"id": 4, "name": "Student Four", "email": None}])
        db.upsert_assignments(
            course_id,
            [
                {
                    "id": 104,
                    "name": "HW4",
                    "due_at": None,
                    "points_possible": 10,
                    "html_url": "",
                    "assignment_group_id": None,
                },
            ],
        )
        db.upsert_submissions(
            course_id,
            [
                {
                    "id": 204,
                    "user_id": 4,
                    "assignment_id": 104,
                    "submitted_at": "2026-01-01T10:00:00Z",
                    "workflow_state": "submitted",
                    "late": False,
                    "score": None,
                    "grader_id": None,
                    "graded_at": None,
                }
            ],
        )

        submissions = db.get_submissions(course_id)
        assert len(submissions) == 1
        sub = submissions[0]
        assert "grader_id" in sub, "grader_id key must be present on submission dict"


# ---------------------------------------------------------------------------
# TestTABreakdownModeSetting
# ---------------------------------------------------------------------------


class TestTABreakdownModeSetting:
    """GET /api/settings returns ta_breakdown_mode; PUT validates and persists it."""

    @pytest.fixture()
    def client(self, fresh_db):
        """TestClient for the FastAPI app using a patched fresh DB."""
        from main import app

        return app, fresh_db

    def test_get_settings_returns_ta_breakdown_mode(self, fresh_db):  # noqa: ARG002
        """GET /api/settings response includes ta_breakdown_mode field."""
        from main import SettingsResponse

        fields = SettingsResponse.model_fields
        assert "ta_breakdown_mode" in fields, (
            "ta_breakdown_mode missing from SettingsResponse"
        )

    def test_default_ta_breakdown_mode_is_group(self, fresh_db):  # noqa: ARG002
        """When ta_breakdown_mode is not set in DB, default value is 'group'."""
        import asyncio

        from httpx import ASGITransport, AsyncClient

        from main import app

        async def run():
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.get("/api/settings")
            return resp

        resp = asyncio.run(run())
        assert resp.status_code == 200
        data = resp.json()
        assert "ta_breakdown_mode" in data, (
            "ta_breakdown_mode missing from GET /api/settings response"
        )
        assert data["ta_breakdown_mode"] == "group", (
            f"Expected default 'group', got {data['ta_breakdown_mode']!r}"
        )

    def test_put_settings_stores_actual(self, fresh_db):  # noqa: ARG002
        """PUT /api/settings with ta_breakdown_mode='actual' persists it."""
        import asyncio

        from httpx import ASGITransport, AsyncClient

        from main import app

        async def run():
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                put_resp = await ac.put(
                    "/api/settings", json={"ta_breakdown_mode": "actual"}
                )
                get_resp = await ac.get("/api/settings")
            return put_resp, get_resp

        put_resp, get_resp = asyncio.run(run())
        assert put_resp.status_code == 200
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["ta_breakdown_mode"] == "actual", (
            f"Expected 'actual' after PUT, got {data['ta_breakdown_mode']!r}"
        )

    def test_put_settings_stores_group(self, fresh_db):  # noqa: ARG002
        """PUT /api/settings with ta_breakdown_mode='group' persists it."""
        import asyncio

        from httpx import ASGITransport, AsyncClient

        from main import app

        async def run():
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                # First set to actual, then back to group
                await ac.put("/api/settings", json={"ta_breakdown_mode": "actual"})
                put_resp = await ac.put(
                    "/api/settings", json={"ta_breakdown_mode": "group"}
                )
                get_resp = await ac.get("/api/settings")
            return put_resp, get_resp

        put_resp, get_resp = asyncio.run(run())
        assert put_resp.status_code == 200
        data = get_resp.json()
        assert data["ta_breakdown_mode"] == "group"

    def test_put_settings_rejects_invalid(self, fresh_db):  # noqa: ARG002
        """PUT /api/settings with ta_breakdown_mode='invalid' returns 400."""
        import asyncio

        from httpx import ASGITransport, AsyncClient

        from main import app

        async def run():
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.put(
                    "/api/settings", json={"ta_breakdown_mode": "invalid"}
                )
            return resp

        resp = asyncio.run(run())
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
