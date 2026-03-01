"""Tests for _compute_days_late() and calculate_student_late_day_summary()."""

from datetime import UTC, datetime


def make_due_at(year=2025, month=1, day=10) -> str:
    return datetime(year, month, day, 23, 59, tzinfo=UTC).isoformat()


def make_submitted_at(year=2025, month=1, day=10, hour=23, minute=59) -> str:
    return datetime(year, month, day, hour, minute, tzinfo=UTC).isoformat()


class TestComputeDaysLate:
    def test_none_submission_returns_zero(self):
        from main import _compute_days_late

        assert _compute_days_late(None, make_due_at()) == 0

    def test_unsubmitted_workflow_state_returns_zero(self):
        from main import _compute_days_late

        sub = {
            "workflow_state": "unsubmitted",
            "submitted_at": make_submitted_at(day=15),
        }
        assert _compute_days_late(sub, make_due_at()) == 0

    def test_on_time_submission_returns_zero(self):
        from main import _compute_days_late

        # Submitted on the exact due date (not late)
        sub = {"workflow_state": "graded", "submitted_at": make_submitted_at(day=10)}
        assert _compute_days_late(sub, make_due_at()) == 0

    def test_one_day_late_returns_one(self):
        from main import _compute_days_late

        # Submitted exactly 1 day late
        sub = {
            "workflow_state": "graded",
            "submitted_at": make_submitted_at(day=11, hour=23, minute=59),
        }
        assert _compute_days_late(sub, make_due_at()) == 1

    def test_partial_day_late_beyond_grace_returns_one(self):
        # Submitted 30 minutes after due date (beyond 15-min grace period)
        # ceiling to 1 day
        from datetime import timedelta

        from main import _compute_days_late

        due = datetime(2025, 1, 10, 23, 59, tzinfo=UTC)
        submitted = due + timedelta(minutes=30)
        sub = {"workflow_state": "graded", "submitted_at": submitted.isoformat()}
        assert _compute_days_late(sub, due.isoformat()) == 1

    def test_no_submitted_at_returns_zero(self):
        from main import _compute_days_late

        sub = {"workflow_state": "graded", "submitted_at": None}
        assert _compute_days_late(sub, make_due_at()) == 0

    def test_pending_review_returns_zero(self):
        from main import _compute_days_late

        sub = {
            "workflow_state": "pending_review",
            "submitted_at": make_submitted_at(day=15),
        }
        assert _compute_days_late(sub, make_due_at()) == 0


class TestCalculateStudentLateDaySummary:
    def _make_assignment(
        self, assignment_id: int, day: int, group_id: int = 10
    ) -> dict:
        return {
            "id": assignment_id,
            "due_at": make_due_at(day=day),
            "assignment_group_id": group_id,
        }

    def _make_submission(
        self, assignment_id: int, user_id: int, submitted_day: int
    ) -> dict:
        return {
            "assignment_id": assignment_id,
            "user_id": user_id,
            "submitted_at": make_submitted_at(day=submitted_day),
            "workflow_state": "graded",
        }

    def test_example1_nine_days_late_full_bank(self):
        """9 days late, bank=10, cap=7, rate=25.

        Expected: bank_used=7, penalty_days=2, penalty_percent=50, remaining=3.
        """
        from main import calculate_student_late_day_summary

        due = make_due_at(day=10)
        submitted = make_submitted_at(day=19)
        assignments = [{"id": 1, "due_at": due, "assignment_group_id": 10}]
        submissions = [
            {
                "assignment_id": 1,
                "user_id": 42,
                "submitted_at": submitted,
                "workflow_state": "graded",
            }
        ]

        result = calculate_student_late_day_summary(
            42, assignments, submissions, 10, 7, 25, {10}
        )
        r = result[1]
        assert r["bank_days_used"] == 7, f"Expected 7, got {r['bank_days_used']}"
        assert r["penalty_days"] == 2, f"Expected 2, got {r['penalty_days']}"
        assert r["penalty_percent"] == 50, f"Expected 50, got {r['penalty_percent']}"
        assert r["bank_remaining"] == 3, f"Expected 3, got {r['bank_remaining']}"
        assert r["not_accepted"] is False

    def test_example2_three_days_late_one_bank_day(self):
        """3 days late, bank=1, cap=7, rate=25.

        Expected: bank_used=1, penalty_days=2, penalty_percent=50, remaining=0.
        """
        from main import calculate_student_late_day_summary

        due = make_due_at(day=10)
        submitted = make_submitted_at(day=13)
        assignments = [{"id": 2, "due_at": due, "assignment_group_id": 10}]
        submissions = [
            {
                "assignment_id": 2,
                "user_id": 42,
                "submitted_at": submitted,
                "workflow_state": "graded",
            }
        ]

        result = calculate_student_late_day_summary(
            42, assignments, submissions, 1, 7, 25, {10}
        )
        r = result[2]
        assert r["bank_days_used"] == 1
        assert r["penalty_days"] == 2
        assert r["penalty_percent"] == 50
        assert r["bank_remaining"] == 0

    def test_project_deliverable_not_accepted(self):
        """Ineligible group: not_accepted=True, bank_days_used=0, bank unchanged."""
        from main import calculate_student_late_day_summary

        due = make_due_at(day=10)
        submitted = make_submitted_at(day=12)
        assignments = [{"id": 3, "due_at": due, "assignment_group_id": 99}]
        submissions = [
            {
                "assignment_id": 3,
                "user_id": 42,
                "submitted_at": submitted,
                "workflow_state": "graded",
            }
        ]

        result = calculate_student_late_day_summary(
            42, assignments, submissions, 10, 7, 25, {10}
        )
        r = result[3]
        assert r["not_accepted"] is True
        assert r["bank_days_used"] == 0
        assert r["bank_remaining"] == 10  # bank not consumed

    def test_empty_eligible_groups_all_eligible(self):
        """If eligible_group_ids is empty set, all assignments are eligible."""
        from main import calculate_student_late_day_summary

        due = make_due_at(day=10)
        submitted = make_submitted_at(day=12)
        assignments = [{"id": 4, "due_at": due, "assignment_group_id": 99}]
        submissions = [
            {
                "assignment_id": 4,
                "user_id": 42,
                "submitted_at": submitted,
                "workflow_state": "graded",
            }
        ]

        # Empty eligible set → all eligible
        result = calculate_student_late_day_summary(
            42, assignments, submissions, 10, 7, 25, set()
        )
        r = result[4]
        assert r["not_accepted"] is False
        assert r["bank_days_used"] > 0

    def test_no_due_at_excluded_from_result(self):
        """Assignments with no due_at are excluded from the result dict."""
        from main import calculate_student_late_day_summary

        assignments = [{"id": 5, "due_at": None, "assignment_group_id": 10}]
        submissions = []

        result = calculate_student_late_day_summary(
            42, assignments, submissions, 10, 7, 25, {10}
        )
        assert 5 not in result

    def test_assignments_sorted_by_due_at_for_bank_deduction(self):
        """Bank deduction follows chronological order of assignments."""
        from main import calculate_student_late_day_summary

        # Assignment 1 due Jan 5 (earlier), Assignment 2 due Jan 10 (later)
        assignments = [
            {"id": 1, "due_at": make_due_at(day=10), "assignment_group_id": 10},
            {"id": 2, "due_at": make_due_at(day=5), "assignment_group_id": 10},
        ]
        # Assignment 2 (Jan 5) is 5 days late, assignment 1 (Jan 10) is 5 days late
        submissions = [
            {
                "assignment_id": 1,
                "user_id": 42,
                "submitted_at": make_submitted_at(day=15),
                "workflow_state": "graded",
            },
            {
                "assignment_id": 2,
                "user_id": 42,
                "submitted_at": make_submitted_at(day=10),
                "workflow_state": "graded",
            },
        ]

        # bank=6, cap=7, rate=25 → assign2 (Jan5) goes first: 5 bank used, 1 remaining
        # then assign1 (Jan10): 1 bank used (remaining), 4 penalty days
        result = calculate_student_late_day_summary(
            42, assignments, submissions, 6, 7, 25, {10}
        )

        # Assignment 2 (earlier due date) should be processed first
        r2 = result[2]
        assert r2["bank_days_used"] == 5
        assert r2["bank_remaining"] == 1

        r1 = result[1]
        assert r1["bank_days_used"] == 1
        assert r1["bank_remaining"] == 0
        assert r1["penalty_days"] == 4

    def test_penalty_percent_capped_at_100(self):
        """5 penalty days × 25% = 125% → capped at 100%."""
        from main import calculate_student_late_day_summary

        due = make_due_at(day=10)
        # 12 days late, bank=0 → 12 penalty days → 300% → capped at 100%
        submitted = make_submitted_at(day=22)
        assignments = [{"id": 6, "due_at": due, "assignment_group_id": 10}]
        submissions = [
            {
                "assignment_id": 6,
                "user_id": 42,
                "submitted_at": submitted,
                "workflow_state": "graded",
            }
        ]

        result = calculate_student_late_day_summary(
            42, assignments, submissions, 0, 7, 25, {10}
        )
        r = result[6]
        assert r["penalty_percent"] <= 100, (
            f"penalty_percent should be capped: {r['penalty_percent']}"
        )

    def test_on_time_submission_zero_values(self):
        """On-time submission has all zero values and bank unchanged."""
        from main import calculate_student_late_day_summary

        due = make_due_at(day=10)
        submitted = make_submitted_at(day=10)
        assignments = [{"id": 7, "due_at": due, "assignment_group_id": 10}]
        submissions = [
            {
                "assignment_id": 7,
                "user_id": 42,
                "submitted_at": submitted,
                "workflow_state": "graded",
            }
        ]

        result = calculate_student_late_day_summary(
            42, assignments, submissions, 10, 7, 25, {10}
        )
        r = result[7]
        assert r["days_late"] == 0
        assert r["bank_days_used"] == 0
        assert r["penalty_days"] == 0
        assert r["penalty_percent"] == 0
        assert r["not_accepted"] is False
        assert r["bank_remaining"] == 10


class TestAllowedTemplateVariables:
    def test_new_bank_variables_present(self):
        from main import ALLOWED_TEMPLATE_VARIABLES

        assert "bank_days_used" in ALLOWED_TEMPLATE_VARIABLES
        assert "bank_remaining" in ALLOWED_TEMPLATE_VARIABLES
        assert "total_bank" in ALLOWED_TEMPLATE_VARIABLES

    def test_backward_compat_variables_present(self):
        from main import ALLOWED_TEMPLATE_VARIABLES

        assert "days_late" in ALLOWED_TEMPLATE_VARIABLES
        assert "days_remaining" in ALLOWED_TEMPLATE_VARIABLES
        assert "penalty_days" in ALLOWED_TEMPLATE_VARIABLES
        assert "penalty_percent" in ALLOWED_TEMPLATE_VARIABLES
        assert "max_late_days" in ALLOWED_TEMPLATE_VARIABLES
