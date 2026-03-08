"""Tests for updated settings models and get_late_days_data() using bank summary."""


class TestSettingsModels:
    def test_settings_response_includes_new_fields(self):
        from main import SettingsResponse

        fields = SettingsResponse.model_fields
        assert "total_late_day_bank" in fields, (
            "total_late_day_bank missing from SettingsResponse"
        )
        assert "penalty_rate_per_day" in fields, "penalty_rate_per_day missing"
        assert "per_assignment_cap" in fields, "per_assignment_cap missing"
        assert "late_day_eligible_groups" in fields, "late_day_eligible_groups missing"

    def test_settings_response_existing_fields_preserved(self):
        from main import SettingsResponse

        fields = SettingsResponse.model_fields
        assert "course_id" in fields
        assert "max_late_days_per_assignment" in fields
        assert "test_mode" in fields

    def test_settings_update_request_includes_new_fields(self):
        from main import SettingsUpdateRequest

        fields = SettingsUpdateRequest.model_fields
        assert "total_late_day_bank" in fields
        assert "penalty_rate_per_day" in fields
        assert "per_assignment_cap" in fields
        assert "late_day_eligible_groups" in fields

    def test_settings_update_request_new_fields_optional(self):
        from main import SettingsUpdateRequest

        # Should not raise — all fields are optional
        req = SettingsUpdateRequest()
        assert req.total_late_day_bank is None
        assert req.penalty_rate_per_day is None
        assert req.per_assignment_cap is None
        assert req.late_day_eligible_groups is None

    def test_settings_update_request_accepts_new_values(self):
        from main import SettingsUpdateRequest

        req = SettingsUpdateRequest(
            total_late_day_bank=10,
            penalty_rate_per_day=25,
            per_assignment_cap=7,
            late_day_eligible_groups=[100, 200, 300],
        )
        assert req.total_late_day_bank == 10
        assert req.penalty_rate_per_day == 25
        assert req.per_assignment_cap == 7
        assert req.late_day_eligible_groups == [100, 200, 300]

    def test_settings_response_late_day_eligible_groups_is_list_of_int(self):
        from main import SettingsResponse

        # Should accept list[int]
        resp = SettingsResponse(
            course_id="123",
            course_name="Test Course",
            canvas_api_url="https://canvas.example.com",
            last_sync=None,
            test_mode=False,
            max_late_days_per_assignment=7,
            sandbox_course_id="sandbox123",
            timezone="UTC",
            data_path="./data",
            total_late_day_bank=10,
            penalty_rate_per_day=25,
            per_assignment_cap=7,
            late_day_eligible_groups=[100, 200],
        )
        assert resp.late_day_eligible_groups == [100, 200]
        assert resp.total_late_day_bank == 10
        assert resp.penalty_rate_per_day == 25
        assert resp.per_assignment_cap == 7


class TestNewFunctionsExist:
    def test_calculate_student_late_day_summary_exists(self):
        from main import calculate_student_late_day_summary

        assert callable(calculate_student_late_day_summary)

    def test_compute_days_late_exists(self):
        from main import _compute_days_late

        assert callable(_compute_days_late)
