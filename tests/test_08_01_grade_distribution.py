"""
Tests for Phase 08: grade distribution endpoint — index and detail.

All tests in this file are expected to FAIL (RED state) since the endpoint
does not yet exist.

Covers:
- TestGradeDistributionIndex: GET /api/dashboard/grade-distribution/{course_id}
- TestGradeDistributionDetail: GET .../grade-distribution/{course_id}/{assignment_id}
- TestGradeStats: stats block correctness for known scores
- TestSmallSample: small_sample flag and None fields when n < 5 / n == 1
- TestHistogramBins: 10 bins, correct total count, last bin catches max score
- TestPerTaStats: grader_name grouping, NULL grader_id → "Unknown / Pre-Phase 6"
"""

import asyncio

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


# ---------------------------------------------------------------------------
# Shared seed helpers
# ---------------------------------------------------------------------------

_ASSIGNMENT = {
    "id": 101,
    "name": "HW 1",
    "due_at": "2026-03-01T23:59:00Z",
    "points_possible": 100.0,
    "html_url": "",
    "assignment_group_id": None,
}

_STUDENT = {"id": 1, "name": "Alice Student", "email": "alice@example.com"}


def _make_submission(sub_id: int, score: float, grader_id=None) -> dict:
    return {
        "id": sub_id,
        "user_id": 1,
        "assignment_id": 101,
        "submitted_at": "2026-02-28T12:00:00Z",
        "workflow_state": "graded",
        "late": False,
        "score": score,
        "grader_id": grader_id,
        "graded_at": "2026-03-02T10:00:00Z",
    }


# ---------------------------------------------------------------------------
# TestGradeDistributionIndex
# ---------------------------------------------------------------------------


class TestGradeDistributionIndex:
    def test_returns_200_with_assignments_key(self, fresh_db):
        """GET grade-distribution/{course_id} returns 200 with 'assignments' list."""
        from main import app

        fresh_db.upsert_assignments("course1", [_ASSIGNMENT])
        fresh_db.upsert_users("course1", [_STUDENT])
        fresh_db.upsert_submissions("course1", [_make_submission(1, 80.0)])

        resp = asyncio.run(_get(app, "/api/dashboard/grade-distribution/course1"))
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        assert "assignments" in data, f"Response missing 'assignments' key: {data}"
        assert isinstance(data["assignments"], list)

    def test_assignment_item_has_required_fields(self, fresh_db):
        """Each assignment in index response has required fields."""
        from main import app

        fresh_db.upsert_assignments("course1", [_ASSIGNMENT])
        fresh_db.upsert_users("course1", [_STUDENT])
        fresh_db.upsert_submissions("course1", [_make_submission(1, 80.0)])

        resp = asyncio.run(_get(app, "/api/dashboard/grade-distribution/course1"))
        data = resp.json()
        assert len(data["assignments"]) >= 1, "Expected at least one assignment"
        item = data["assignments"][0]
        for field in (
            "assignment_id",
            "assignment_name",
            "points_possible",
            "graded_count",
        ):
            assert field in item, f"Field '{field}' missing from index item: {item}"

    def test_graded_count_counts_graded_submissions(self, fresh_db):
        """graded_count reflects only graded submissions (workflow_state='graded')."""
        from main import app

        fresh_db.upsert_assignments("course1", [_ASSIGNMENT])
        fresh_db.upsert_users(
            "course1",
            [
                _STUDENT,
                {"id": 2, "name": "Bob Student", "email": "bob@example.com"},
            ],
        )
        # Two graded submissions
        fresh_db.upsert_submissions(
            "course1",
            [
                _make_submission(1, 70.0),
                _make_submission(2, 90.0),
            ],
        )

        resp = asyncio.run(_get(app, "/api/dashboard/grade-distribution/course1"))
        data = resp.json()
        assert data["assignments"][0]["graded_count"] == 2, (
            f"Expected graded_count=2, got {data['assignments'][0]['graded_count']}"
        )


# ---------------------------------------------------------------------------
# TestGradeDistributionDetail
# ---------------------------------------------------------------------------


class TestGradeDistributionDetail:
    def test_returns_200(self, fresh_db):
        """GET grade-distribution/{course_id}/{assignment_id} returns 200."""
        from main import app

        fresh_db.upsert_assignments("course1", [_ASSIGNMENT])
        fresh_db.upsert_users("course1", [_STUDENT])
        fresh_db.upsert_submissions("course1", [_make_submission(1, 80.0)])

        resp = asyncio.run(_get(app, "/api/dashboard/grade-distribution/course1/101"))
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}: {resp.text}"
        )

    def test_response_has_stats_histogram_per_ta(self, fresh_db):
        """Detail response contains stats, histogram, per_ta keys."""
        from main import app

        fresh_db.upsert_assignments("course1", [_ASSIGNMENT])
        fresh_db.upsert_users("course1", [_STUDENT])
        fresh_db.upsert_submissions("course1", [_make_submission(1, 80.0)])

        resp = asyncio.run(_get(app, "/api/dashboard/grade-distribution/course1/101"))
        data = resp.json()
        for key in ("stats", "histogram", "per_ta"):
            assert key in data, f"Response missing '{key}' key: {data}"

    def test_response_has_assignment_fields(self, fresh_db):
        """Detail response contains assignment_id, assignment_name, points_possible."""
        from main import app

        fresh_db.upsert_assignments("course1", [_ASSIGNMENT])
        fresh_db.upsert_users("course1", [_STUDENT])
        fresh_db.upsert_submissions("course1", [_make_submission(1, 80.0)])

        resp = asyncio.run(_get(app, "/api/dashboard/grade-distribution/course1/101"))
        data = resp.json()
        for key in ("assignment_id", "assignment_name", "points_possible"):
            assert key in data, f"Response missing '{key}' key: {data}"
        assert data["assignment_id"] == 101


# ---------------------------------------------------------------------------
# TestGradeStats
# ---------------------------------------------------------------------------


class TestGradeStats:
    """Stats block correctness using known scores [70.0, 80.0, 90.0]."""

    _SCORES = [70.0, 80.0, 90.0]

    def _seed(self, fresh_db):
        fresh_db.upsert_assignments("course1", [_ASSIGNMENT])
        fresh_db.upsert_users(
            "course1",
            [{"id": i + 1, "name": f"Student {i}", "email": None} for i in range(3)],
        )
        for idx, score in enumerate(self._SCORES):
            fresh_db.upsert_submissions(
                "course1",
                [
                    {
                        "id": idx + 1,
                        "user_id": idx + 1,
                        "assignment_id": 101,
                        "submitted_at": "2026-02-28T12:00:00Z",
                        "workflow_state": "graded",
                        "late": False,
                        "score": score,
                        "grader_id": None,
                        "graded_at": "2026-03-02T10:00:00Z",
                    }
                ],
            )

    def test_mean_is_correct(self, fresh_db):
        """mean of [70, 80, 90] = 80.0."""
        from main import app

        self._seed(fresh_db)
        resp = asyncio.run(_get(app, "/api/dashboard/grade-distribution/course1/101"))
        stats = resp.json()["stats"]
        assert stats["mean"] == 80.0, f"Expected mean=80.0, got {stats.get('mean')}"

    def test_median_is_correct(self, fresh_db):
        """median of [70, 80, 90] = 80.0."""
        from main import app

        self._seed(fresh_db)
        resp = asyncio.run(_get(app, "/api/dashboard/grade-distribution/course1/101"))
        stats = resp.json()["stats"]
        assert stats["median"] == 80.0, (
            f"Expected median=80.0, got {stats.get('median')}"
        )

    def test_stats_has_required_keys(self, fresh_db):
        """Stats block has n, mean, median, stdev, q1, q3, min, max."""
        from main import app

        self._seed(fresh_db)
        resp = asyncio.run(_get(app, "/api/dashboard/grade-distribution/course1/101"))
        stats = resp.json()["stats"]
        for key in ("n", "mean", "median", "stdev", "q1", "q3", "min", "max"):
            assert key in stats, f"Stats missing '{key}': {stats}"

    def test_min_max_correct(self, fresh_db):
        """min=70.0, max=90.0 for [70, 80, 90]."""
        from main import app

        self._seed(fresh_db)
        resp = asyncio.run(_get(app, "/api/dashboard/grade-distribution/course1/101"))
        stats = resp.json()["stats"]
        assert stats["min"] == 70.0, f"Expected min=70.0, got {stats.get('min')}"
        assert stats["max"] == 90.0, f"Expected max=90.0, got {stats.get('max')}"


# ---------------------------------------------------------------------------
# TestSmallSample
# ---------------------------------------------------------------------------


class TestSmallSample:
    def test_small_sample_true_when_n_lt_5(self, fresh_db):
        """small_sample=True when n=3."""
        from main import app

        fresh_db.upsert_assignments("course1", [_ASSIGNMENT])
        fresh_db.upsert_users("course1", [_STUDENT])
        fresh_db.upsert_submissions(
            "course1",
            [
                {
                    "id": i + 1,
                    "user_id": 1,
                    "assignment_id": 101,
                    "submitted_at": "2026-02-28T12:00:00Z",
                    "workflow_state": "graded",
                    "late": False,
                    "score": 80.0 + i,
                    "grader_id": None,
                    "graded_at": "2026-03-02T10:00:00Z",
                }
                for i in range(3)
            ],
        )

        resp = asyncio.run(_get(app, "/api/dashboard/grade-distribution/course1/101"))
        stats = resp.json()["stats"]
        assert stats["small_sample"] is True, (
            f"Expected small_sample=True for n=3, got {stats.get('small_sample')}"
        )

    def test_stdev_and_quartiles_none_when_n_eq_1(self, fresh_db):
        """When n=1, stdev and q1/q3 are None (not computable)."""
        from main import app

        fresh_db.upsert_assignments("course1", [_ASSIGNMENT])
        fresh_db.upsert_users("course1", [_STUDENT])
        fresh_db.upsert_submissions("course1", [_make_submission(1, 85.0)])

        resp = asyncio.run(_get(app, "/api/dashboard/grade-distribution/course1/101"))
        stats = resp.json()["stats"]
        assert stats["n"] == 1, f"Expected n=1, got {stats.get('n')}"
        assert stats["stdev"] is None, (
            f"Expected stdev=None for n=1, got {stats.get('stdev')}"
        )
        assert stats["q1"] is None, f"Expected q1=None for n=1, got {stats.get('q1')}"
        assert stats["q3"] is None, f"Expected q3=None for n=1, got {stats.get('q3')}"

    def test_small_sample_false_when_n_ge_5(self, fresh_db):
        """small_sample=False when n>=5."""
        from main import app

        fresh_db.upsert_assignments("course1", [_ASSIGNMENT])
        fresh_db.upsert_users(
            "course1", [{"id": i + 1, "name": f"S{i}", "email": None} for i in range(5)]
        )
        fresh_db.upsert_submissions(
            "course1",
            [
                {
                    "id": i + 1,
                    "user_id": i + 1,
                    "assignment_id": 101,
                    "submitted_at": "2026-02-28T12:00:00Z",
                    "workflow_state": "graded",
                    "late": False,
                    "score": 60.0 + i * 5,
                    "grader_id": None,
                    "graded_at": "2026-03-02T10:00:00Z",
                }
                for i in range(5)
            ],
        )

        resp = asyncio.run(_get(app, "/api/dashboard/grade-distribution/course1/101"))
        stats = resp.json()["stats"]
        assert stats["small_sample"] is False, (
            f"Expected small_sample=False for n=5, got {stats.get('small_sample')}"
        )


# ---------------------------------------------------------------------------
# TestHistogramBins
# ---------------------------------------------------------------------------


class TestHistogramBins:
    """Histogram bins for points_possible=100, scores=[70, 80, 90]."""

    def _seed(self, fresh_db):
        fresh_db.upsert_assignments("course1", [_ASSIGNMENT])
        fresh_db.upsert_users(
            "course1", [{"id": i + 1, "name": f"S{i}", "email": None} for i in range(3)]
        )
        for idx, score in enumerate([70.0, 80.0, 90.0]):
            fresh_db.upsert_submissions(
                "course1",
                [
                    {
                        "id": idx + 1,
                        "user_id": idx + 1,
                        "assignment_id": 101,
                        "submitted_at": "2026-02-28T12:00:00Z",
                        "workflow_state": "graded",
                        "late": False,
                        "score": score,
                        "grader_id": None,
                        "graded_at": "2026-03-02T10:00:00Z",
                    }
                ],
            )

    def test_returns_10_bins_for_points_possible_100(self, fresh_db):
        """10 bins returned for points_possible=100."""
        from main import app

        self._seed(fresh_db)
        resp = asyncio.run(_get(app, "/api/dashboard/grade-distribution/course1/101"))
        histogram = resp.json()["histogram"]
        assert len(histogram) == 10, (
            f"Expected 10 bins for points_possible=100, got {len(histogram)}"
        )

    def test_total_bin_count_equals_n(self, fresh_db):
        """Sum of bin counts equals n (total graded submissions)."""
        from main import app

        self._seed(fresh_db)
        resp = asyncio.run(_get(app, "/api/dashboard/grade-distribution/course1/101"))
        data = resp.json()
        histogram = data["histogram"]
        total = sum(b["count"] for b in histogram)
        n = data["stats"]["n"]
        assert total == n, f"Total bin count {total} != n {n}"

    def test_last_bin_includes_max_score(self, fresh_db):
        """Score equal to points_possible (100.0) falls in the last bin."""
        from main import app

        fresh_db.upsert_assignments("course1", [_ASSIGNMENT])
        fresh_db.upsert_users(
            "course1", [{"id": i + 1, "name": f"S{i}", "email": None} for i in range(2)]
        )
        # One score at max
        fresh_db.upsert_submissions(
            "course1",
            [
                {
                    "id": 1,
                    "user_id": 1,
                    "assignment_id": 101,
                    "submitted_at": "2026-02-28T12:00:00Z",
                    "workflow_state": "graded",
                    "late": False,
                    "score": 100.0,
                    "grader_id": None,
                    "graded_at": "2026-03-02T10:00:00Z",
                },
                {
                    "id": 2,
                    "user_id": 2,
                    "assignment_id": 101,
                    "submitted_at": "2026-02-28T12:00:00Z",
                    "workflow_state": "graded",
                    "late": False,
                    "score": 50.0,
                    "grader_id": None,
                    "graded_at": "2026-03-02T10:00:00Z",
                },
            ],
        )

        resp = asyncio.run(_get(app, "/api/dashboard/grade-distribution/course1/101"))
        data = resp.json()
        histogram = data["histogram"]
        total = sum(b["count"] for b in histogram)
        assert total == 2, (
            f"Expected total count=2 (score=100 must appear in a bin), got {total}"
        )
        # Last bin should have at least the score=100 entry
        assert histogram[-1]["count"] >= 1, (
            f"Expected last bin count >= 1, got {histogram[-1]['count']}"
        )

    def test_bin_items_have_required_fields(self, fresh_db):
        """Each bin has bin_start, bin_end, count, label."""
        from main import app

        self._seed(fresh_db)
        resp = asyncio.run(_get(app, "/api/dashboard/grade-distribution/course1/101"))
        histogram = resp.json()["histogram"]
        for b in histogram:
            for field in ("bin_start", "bin_end", "count", "label"):
                assert field in b, f"Bin missing '{field}': {b}"


# ---------------------------------------------------------------------------
# TestPerTaStats
# ---------------------------------------------------------------------------


class TestPerTaStats:
    def test_grader_name_groups_correctly(self, fresh_db):
        """Submissions with known grader_id are grouped under that TA's name."""
        from main import app

        fresh_db.upsert_assignments("course1", [_ASSIGNMENT])
        fresh_db.upsert_users("course1", [_STUDENT])
        fresh_db.upsert_ta_users(
            "course1",
            [
                {
                    "id": 501,
                    "name": "Alice TA",
                    "email": "alice@ta.edu",
                    "enrollment_type": "TaEnrollment",
                }
            ],
        )
        fresh_db.upsert_submissions(
            "course1",
            [
                {
                    "id": 1,
                    "user_id": 1,
                    "assignment_id": 101,
                    "submitted_at": "2026-02-28T12:00:00Z",
                    "workflow_state": "graded",
                    "late": False,
                    "score": 88.0,
                    "grader_id": 501,
                    "graded_at": "2026-03-02T10:00:00Z",
                }
            ],
        )

        resp = asyncio.run(_get(app, "/api/dashboard/grade-distribution/course1/101"))
        per_ta = resp.json()["per_ta"]
        names = [t["grader_name"] for t in per_ta]
        assert "Alice TA" in names, (
            f"Expected 'Alice TA' in per_ta grader_names, got {names}"
        )

    def test_null_grader_id_grouped_as_unknown(self, fresh_db):
        """Submissions with NULL grader_id appear under 'Unknown / Pre-Phase 6'."""
        from main import app

        fresh_db.upsert_assignments("course1", [_ASSIGNMENT])
        fresh_db.upsert_users("course1", [_STUDENT])
        fresh_db.upsert_submissions(
            "course1",
            [
                {
                    "id": 1,
                    "user_id": 1,
                    "assignment_id": 101,
                    "submitted_at": "2026-02-28T12:00:00Z",
                    "workflow_state": "graded",
                    "late": False,
                    "score": 75.0,
                    "grader_id": None,
                    "graded_at": "2026-03-02T10:00:00Z",
                }
            ],
        )

        resp = asyncio.run(_get(app, "/api/dashboard/grade-distribution/course1/101"))
        per_ta = resp.json()["per_ta"]
        names = [t["grader_name"] for t in per_ta]
        assert "Unknown / Pre-Phase 6" in names, (
            f"Expected 'Unknown / Pre-Phase 6' in per_ta, got {names}"
        )

    def test_per_ta_item_has_required_fields(self, fresh_db):
        """Each per_ta entry has grader_name, n, mean."""
        from main import app

        fresh_db.upsert_assignments("course1", [_ASSIGNMENT])
        fresh_db.upsert_users("course1", [_STUDENT])
        fresh_db.upsert_submissions("course1", [_make_submission(1, 80.0)])

        resp = asyncio.run(_get(app, "/api/dashboard/grade-distribution/course1/101"))
        per_ta = resp.json()["per_ta"]
        assert len(per_ta) >= 1
        for item in per_ta:
            for field in ("grader_name", "n", "mean"):
                assert field in item, f"per_ta item missing '{field}': {item}"

    def test_both_known_and_unknown_in_per_ta(self, fresh_db):
        """One known grader + one NULL grader both appear in per_ta list."""
        from main import app

        fresh_db.upsert_assignments("course1", [_ASSIGNMENT])
        fresh_db.upsert_users(
            "course1",
            [
                _STUDENT,
                {"id": 2, "name": "Bob Student", "email": None},
            ],
        )
        fresh_db.upsert_ta_users(
            "course1",
            [
                {
                    "id": 501,
                    "name": "Alice TA",
                    "email": None,
                    "enrollment_type": "TaEnrollment",
                }
            ],
        )
        fresh_db.upsert_submissions(
            "course1",
            [
                {
                    "id": 1,
                    "user_id": 1,
                    "assignment_id": 101,
                    "submitted_at": "2026-02-28T12:00:00Z",
                    "workflow_state": "graded",
                    "late": False,
                    "score": 88.0,
                    "grader_id": 501,
                    "graded_at": "2026-03-02T10:00:00Z",
                },
                {
                    "id": 2,
                    "user_id": 2,
                    "assignment_id": 101,
                    "submitted_at": "2026-02-28T12:00:00Z",
                    "workflow_state": "graded",
                    "late": False,
                    "score": 72.0,
                    "grader_id": None,
                    "graded_at": "2026-03-02T10:00:00Z",
                },
            ],
        )

        resp = asyncio.run(_get(app, "/api/dashboard/grade-distribution/course1/101"))
        per_ta = resp.json()["per_ta"]
        names = [t["grader_name"] for t in per_ta]
        assert "Alice TA" in names, f"Expected 'Alice TA' in per_ta, got {names}"
        assert "Unknown / Pre-Phase 6" in names, (
            f"Expected 'Unknown / Pre-Phase 6' in per_ta, got {names}"
        )
