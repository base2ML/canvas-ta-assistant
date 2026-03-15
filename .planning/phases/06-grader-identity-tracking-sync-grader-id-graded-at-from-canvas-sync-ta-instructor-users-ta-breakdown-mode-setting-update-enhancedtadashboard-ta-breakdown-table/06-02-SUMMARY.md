---
phase: 06-grader-identity-tracking
plan: "02"
subsystem: canvas-sync
tags: [sync, canvas-api, ta-users, grader-identity, tdd]
dependency_graph:
  requires: [06-01]
  provides: [canvas_sync.ta_users_fetch, submissions.grader_id_capture]
  affects: [database.upsert_submissions, canvas_sync.sync_course_data]
tech_stack:
  added: []
  patterns: [two-pass-deduplication, getattr-safe-extract, 11-column-upsert]
key_files:
  created: [tests/test_06_02_sync.py]
  modified: [canvas_sync.py, database.py]
decisions:
  - "Two-pass TA fetch with seen_ids set: ta enrollment first (wins on conflict), teacher second — consistent with fetch_available_courses() deduplication pattern"
  - "grader_id/graded_at captured via getattr with None default — matches existing pattern for nullable fields in submission dict"
  - "upsert_submissions extended to 11 columns; ON CONFLICT SET includes both new columns — grader_id/graded_at overwritten on re-sync"
  - "[Rule 1 - Bug] Fixed SettingsResponse.ta_breakdown_mode missing default value causing pre-existing test regression"
metrics:
  duration: 4 min
  completed: "2026-03-15"
  tasks_completed: 2
  files_modified: 3
---

# Phase 06 Plan 02: Sync TA/Instructor Users and Grader Fields Summary

**One-liner:** Two-pass Canvas API fetch for TA/instructor users with deduplication writes to ta_users; grader_id and graded_at captured from submission objects and persisted via 11-column upsert_submissions().

## Tasks Completed

| # | Name | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Wave 0 test scaffold (TDD RED) | e0e6e21 | tests/test_06_02_sync.py |
| 2 | Extend canvas_sync.py and upsert_submissions() (TDD GREEN) | e8546ad | canvas_sync.py, database.py |

## What Was Built

### canvas_sync.py Extensions

- **TA user fetch loop**: After student user fetch, two separate `course.get_users()` calls (`enrollment_type=["ta"]` then `enrollment_type=["teacher"]`) with a `seen_ta_ids` set for deduplication. First-seen enrollment type wins. Logged with timing.
- **Grader field capture**: `grader_id` and `graded_at` added to submission dict via `getattr(submission, "grader_id", None)` and `getattr(submission, "graded_at", None)`.
- **Write transaction**: `db.upsert_ta_users(course_id, ta_users_list, conn)` inserted after `upsert_users()` and before `upsert_groups()`.
- **Stats**: `"ta_users": len(ta_users_list)` added to return stats dict.

### database.py Extension

- **upsert_submissions()**: Extended from 9 to 11 columns. `grader_id` and `graded_at` added to INSERT column list, VALUES placeholders, and ON CONFLICT DO UPDATE SET clause.

## Tests

All 9 tests in `tests/test_06_02_sync.py` pass:

- `TestSyncTAUsers` (3 tests): upsert_ta_users inserts rows, deduplication via seen_ids works, enrollment_type preserved per user
- `TestSyncGraderFields` (3 tests): getattr extraction logic correctly captures grader_id/graded_at or None when absent
- `TestUpsertSubmissionsGraderFields` (3 tests): grader_id stored, graded_at stored, NULL grader_id stored as NULL

Full suite: 97 tests pass, 0 failures.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed SettingsResponse.ta_breakdown_mode missing default**
- **Found during:** Task 2 (full test suite run)
- **Issue:** Pre-existing commit (4d432cb, 06-03 work) added `ta_breakdown_mode: str` to `SettingsResponse` without a default value. The `test_05_03_settings_and_late_days.py::TestSettingsModels::test_settings_response_late_day_eligible_groups_is_list_of_int` test created a `SettingsResponse` without `ta_breakdown_mode` and failed with `ValidationError: Field required`.
- **Fix:** Changed `ta_breakdown_mode: str` to `ta_breakdown_mode: str = "group"` in `main.py`.
- **Files modified:** main.py
- **Commit:** e8546ad

**2. [Rule 3 - Blocking] Fixed pre-existing ruff lint errors in test_06_03_api.py**
- **Found during:** Task 1 TDD RED commit
- **Issue:** test_06_03_api.py (committed by prior agent for 06-03 plan) had `E501` and `ARG002` errors that caused the pre-commit ruff hook to fail on all commits.
- **Fix:** Added `# noqa: ARG002` to `test_grader_name_resolved` method signature.
- **Files modified:** tests/test_06_03_api.py
- **Commit:** e0e6e21

## Self-Check: PASSED

- canvas_sync.py: FOUND
- database.py: FOUND
- tests/test_06_02_sync.py: FOUND
- Commit e8546ad: FOUND
- Commit e0e6e21: FOUND
- 97 tests pass, 0 failures
