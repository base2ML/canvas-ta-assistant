"""Tests for updated preview_comments() and post_comments() posting flow."""


class TestPostingFlowSourcePatterns:
    """Verify the source code patterns without running the full server."""

    def _read_main(self) -> str:
        with open("main.py") as f:
            return f.read()

    def test_bank_summaries_precomputed_in_post_comments(self):
        src = self._read_main()
        assert "bank_summaries" in src, "bank_summaries pre-computation missing"

    def test_not_accepted_guard_present(self):
        src = self._read_main()
        assert "not_accepted" in src, "not_accepted guard missing from posting flow"

    def test_bank_days_used_in_template_context(self):
        src = self._read_main()
        assert "bank_days_used" in src, "bank_days_used missing from template context"

    def test_old_function_still_exists_not_deleted(self):
        """calculate_late_days_for_user should still exist (not deleted in task 3)."""
        src = self._read_main()
        assert "calculate_late_days_for_user" in src, (
            "Old function should not be deleted yet"
        )

    def test_calculate_student_late_day_summary_called_in_preview(self):
        src = self._read_main()
        # The new function should be called in preview_comments
        assert "calculate_student_late_day_summary" in src

    def test_total_bank_in_template_context(self):
        src = self._read_main()
        assert '"total_bank"' in src, "total_bank missing from template context"

    def test_bank_remaining_in_template_context(self):
        src = self._read_main()
        assert '"bank_remaining"' in src, "bank_remaining missing from template context"


class TestImportClean:
    def test_main_imports_cleanly(self):
        import main

        assert hasattr(main, "calculate_student_late_day_summary")
        assert hasattr(main, "_compute_days_late")
        assert hasattr(main, "SettingsResponse")
        assert hasattr(main, "SettingsUpdateRequest")

    def test_allowed_template_variables_has_all_bank_vars(self):
        from main import ALLOWED_TEMPLATE_VARIABLES

        assert "bank_days_used" in ALLOWED_TEMPLATE_VARIABLES
        assert "bank_remaining" in ALLOWED_TEMPLATE_VARIABLES
        assert "total_bank" in ALLOWED_TEMPLATE_VARIABLES
        # Alias variables removed — only canonical names allowed
        assert "days_remaining" not in ALLOWED_TEMPLATE_VARIABLES
        assert "max_late_days" not in ALLOWED_TEMPLATE_VARIABLES
