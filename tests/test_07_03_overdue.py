"""
Tests for Phase 07 overdue computation helper.

Covers:
- TestIsOverdue: is_overdue() helper function behavior in main.py
"""

import pytest


# ---------------------------------------------------------------------------
# TestIsOverdue
# ---------------------------------------------------------------------------


class TestIsOverdue:
    """Tests for the is_overdue helper function imported from main."""

    @pytest.fixture(autouse=True)
    def import_helper(self):
        """Import the overdue helper from main module."""
        from main import is_overdue as _is_overdue

        self.is_overdue = _is_overdue

    def test_overdue_when_past_deadline_with_pending(self):
        """Returns True when deadline is in the past and pending_count >= 1."""
        past_deadline = "2026-01-01T00:00:00Z"
        result = self.is_overdue(past_deadline, pending_count=1)
        assert result is True, (
            f"Expected True for past deadline with pending, got {result}"
        )

    def test_not_overdue_when_no_pending(self):
        """Returns False when deadline is in the past but pending_count == 0."""
        past_deadline = "2026-01-01T00:00:00Z"
        result = self.is_overdue(past_deadline, pending_count=0)
        assert result is False, (
            f"Expected False when no pending submissions, got {result}"
        )

    def test_not_overdue_when_future(self):
        """Returns False when deadline is in the future even with pending."""
        future_deadline = "2099-12-31T23:59:59Z"
        result = self.is_overdue(future_deadline, pending_count=5)
        assert result is False, f"Expected False for future deadline, got {result}"

    def test_not_overdue_when_no_deadline(self):
        """Returns False when deadline_at_str is None."""
        result = self.is_overdue(None, pending_count=1)
        assert result is False, f"Expected False when deadline is None, got {result}"

    def test_handles_invalid_date_string(self):
        """Returns False (not raises) when deadline_at_str is not a valid date."""
        result = self.is_overdue("not-a-date", pending_count=1)
        assert result is False, f"Expected False for invalid date string, got {result}"
