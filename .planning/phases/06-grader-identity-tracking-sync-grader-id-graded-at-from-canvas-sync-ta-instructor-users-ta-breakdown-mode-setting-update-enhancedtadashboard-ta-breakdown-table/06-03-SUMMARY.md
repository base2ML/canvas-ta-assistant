---
phase: 06-grader-identity-tracking
plan: 03
subsystem: api, database
tags: [sqlite, fastapi, pydantic, grader-identity, submissions, settings]

# Dependency graph
requires:
  - phase: 06-01
    provides: ta_users table with grader_id/graded_at columns on submissions
provides:
  - get_submissions() returns grader_id, graded_at, and grader_name via LEFT JOIN ta_users
  - GET /api/settings returns ta_breakdown_mode field (default 'group')
  - PUT /api/settings validates and persists ta_breakdown_mode ('group' | 'actual')
affects:
  - 06-04 (EnhancedTADashboard TA breakdown table reads grader_name from submissions)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - LEFT JOIN ta_users on get_submissions() scoped by course_id to prevent cross-course collisions
    - Settings string enum pattern with explicit validation in update_settings()

key-files:
  created:
    - tests/test_06_03_api.py
  modified:
    - database.py
    - main.py

key-decisions:
  - "upsert_submissions() extended to persist grader_id and graded_at alongside the existing
    submission fields — required for test fixture setup and general correctness when syncing
    via non-Canvas-API paths"
  - "asyncio.run() used for async httpx tests (no pytest-asyncio) — matches zero-dependency
    test style used in rest of test suite"
  - "ta_breakdown_mode stored as plain string in settings table; normalized to 'group' if
    value missing or unrecognized (defensive default)"

patterns-established:
  - "String enum setting pattern: db.get_setting() -> validate in ('a','b') else default -> SettingsResponse field"

requirements-completed:
  - GRADER-API-01
  - GRADER-SETTINGS-01

# Metrics
duration: 5min
completed: 2026-03-15
---

# Phase 06 Plan 03: API Extensions for grader_name JOIN and ta_breakdown_mode Settings Summary

**LEFT JOIN ta_users in get_submissions() exposes grader_name on submissions; ta_breakdown_mode added to GET/PUT /api/settings with 'group'|'actual' validation**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-15T02:55:30Z
- **Completed:** 2026-03-15T02:59:35Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 3

## Accomplishments

- `get_submissions()` now returns `grader_id`, `graded_at`, and `grader_name` on every submission dict via LEFT JOIN to `ta_users` scoped by `course_id`
- `grader_name` is `None` when `grader_id` is `None` or not found in `ta_users`
- `GET /api/settings` returns `ta_breakdown_mode` with default `"group"`
- `PUT /api/settings` accepts and persists `ta_breakdown_mode`, rejecting invalid values with HTTP 400
- All 9 tests in `test_06_03_api.py` pass; full suite 97 tests green

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 test scaffold** - `e0e6e21` (test)
2. **Task 2: Extend get_submissions() JOIN and settings models/endpoints** - `4d432cb` (feat)

_Note: TDD tasks have two commits (test RED -> feat GREEN)_

## Files Created/Modified

- `tests/test_06_03_api.py` - 9 tests: TestSubmissionsGraderName (4) + TestTABreakdownModeSetting (5)
- `database.py` - get_submissions() both SELECT branches replaced with LEFT JOIN; upsert_submissions() extended for grader_id/graded_at
- `main.py` - SettingsResponse.ta_breakdown_mode, SettingsUpdateRequest.ta_breakdown_mode, get_settings() read+default, update_settings() validate+persist

## Decisions Made

- `upsert_submissions()` was missing `grader_id`/`graded_at` in its INSERT — extended as a Rule 1 auto-fix so test data could be inserted with those fields
- Used `asyncio.run()` for async httpx ASGI tests rather than `anyio.from_thread.run_sync()` (which requires an existing event loop) — consistent with zero-extra-dependency test style
- `ta_breakdown_mode` defaults to `"group"` on `SettingsResponse` (Pydantic default) and in `get_settings()` runtime logic

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] upsert_submissions() missing grader_id/graded_at columns**
- **Found during:** Task 2 (GREEN implementation)
- **Issue:** `upsert_submissions()` INSERT omitted `grader_id` and `graded_at` columns even though the schema had them. Test data inserted via `upsert_submissions()` always had `grader_id=None`, breaking the JOIN test.
- **Fix:** Added `grader_id` and `graded_at` to the INSERT tuple, column list, VALUES placeholders, and ON CONFLICT UPDATE clause in `upsert_submissions()`
- **Files modified:** `database.py`
- **Verification:** `test_grader_name_resolved` passes; all 97 tests green
- **Committed in:** `4d432cb` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix was necessary for both test correctness and production correctness (sync path via non-Canvas routes). No scope creep.

## Issues Encountered

- Initial test approach used `anyio.from_thread.run_sync()` which requires an existing event loop — replaced with `asyncio.run()` as tests run in synchronous pytest context

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `grader_name` is now available on every submission dict from `GET /api/canvas/submissions/{course_id}`
- `ta_breakdown_mode` is persisted and returned by settings endpoints
- Plan 04 (EnhancedTADashboard TA breakdown table) can now consume `grader_name` directly from submission objects and read `ta_breakdown_mode` from settings

## Self-Check: PASSED

All files exist and all commits verified.

---
*Phase: 06-grader-identity-tracking*
*Completed: 2026-03-15*
