---
phase: 07-add-ta-grading-deadlines
plan: 03
subsystem: api
tags: [fastapi, pydantic, sqlite, datetime, rest]

# Dependency graph
requires:
  - phase: 07-02
    provides: db.get_grading_deadlines(), db.upsert_grading_deadline(), db.upsert_grading_deadline_if_not_override()
  - phase: 07-01
    provides: test scaffolds (test_07_02_api.py, test_07_03_overdue.py) written RED
provides:
  - GET /api/settings returns default_grading_turnaround_days (default 7)
  - PUT /api/settings persists default_grading_turnaround_days
  - GET /api/dashboard/grading-deadlines/{course_id} returns assignments with deadline and is_overdue
  - PUT /api/dashboard/grading-deadlines/{course_id}/{assignment_id} sets or overrides a deadline
  - POST /api/dashboard/grading-deadlines/{course_id}/propagate-defaults creates deadline rows for assignments with due_at
  - is_overdue() helper function in main.py
affects:
  - 07-04 (Settings UI — reads default_grading_turnaround_days)
  - 07-05 (Dashboard inline editing — calls PUT and propagate-defaults endpoints)
  - 07-06 (Overdue badges — calls GET grading-deadlines)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "is_overdue() module-level helper: returns True only when datetime.now(UTC) > deadline AND pending_count > 0"
    - "Pydantic response model for list endpoint: GradingDeadlinesResponse wraps list[GradingDeadlineItem]"
    - "propagate-defaults pattern: loop assignments, skip NULL due_at, call upsert_if_not_override for atomic skip"

key-files:
  created: []
  modified:
    - main.py

key-decisions:
  - "is_overdue() named without underscore prefix so tests can import it directly from main module"
  - "GradingDeadlineItem uses deadline_at field name (not grading_deadline) to match what test_07_02_api.py asserts"
  - "raise HTTPException from e in update_grading_deadline to satisfy Ruff B904 (exception chaining)"
  - "timedelta added to existing from datetime import UTC, datetime line (no new import block)"

patterns-established:
  - "Deadline overdue check: must have both past deadline AND pending submissions > 0 — all-graded assignments are never overdue even if deadline has passed"
  - "propagate-defaults is idempotent for non-override rows: safe to call multiple times"

requirements-completed:
  - DEADLINE-SETTINGS-01
  - DEADLINE-API-01
  - DEADLINE-API-02
  - DEADLINE-API-03
  - DEADLINE-OVERDUE-01

# Metrics
duration: 8min
completed: 2026-03-15
---

# Phase 07 Plan 03: REST API Deadline Endpoints Summary

**Three grading-deadline CRUD endpoints + is_overdue() helper added to main.py, with default_grading_turnaround_days wired through settings; all 120 backend tests pass**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-15T22:40:00Z
- **Completed:** 2026-03-15T22:48:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Extended SettingsResponse and SettingsUpdateRequest with default_grading_turnaround_days (read/write via DB)
- Added module-level is_overdue() helper with correct semantics: past deadline + pending > 0
- Added GET/PUT/POST endpoints for grading deadline CRUD (14 targeted tests all GREEN)
- Full suite of 120 tests passes with no regression

## Task Commits

Each task was committed atomically:

1. **Task 1: Settings model extensions for default_grading_turnaround_days** - `25b67c0` (feat)
2. **Task 2: Deadline CRUD endpoints + overdue computation** - `c0003e4` (feat)

**Plan metadata:** (docs commit to follow)

_Note: Task 2 required a Ruff B904 fix (raise from e in except clause) before the pre-commit hook would accept the commit._

## Files Created/Modified
- `/Users/mapajr/git/cda-ta-dashboard/main.py` - Settings model extensions, is_overdue() helper, 3 new deadline endpoints, timedelta import

## Decisions Made
- `is_overdue()` named without underscore prefix so tests can import it directly from main module (test_07_03_overdue.py uses `from main import is_overdue`)
- `GradingDeadlineItem` uses `deadline_at` field name to match what test_07_02_api.py asserts (test checks for `deadline_at` not `grading_deadline`)
- Added `raise ... from e` in update_grading_deadline's except clause to satisfy Ruff B904 rule
- `timedelta` added to the existing `from datetime import UTC, datetime` import line

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Ruff B904 lint error in update_grading_deadline exception handler**
- **Found during:** Task 2 (commit attempt)
- **Issue:** `raise HTTPException(...)` inside `except` block missing `from e` chain — Ruff B904 flagged this as error
- **Fix:** Changed to `raise HTTPException(status_code=500, detail=str(e)) from e`
- **Files modified:** main.py
- **Verification:** Pre-commit Ruff check passed on second commit attempt
- **Committed in:** c0003e4 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - lint/bug)
**Impact on plan:** Minor fix required by Ruff lint rules. No scope creep.

## Issues Encountered
- Pre-commit hook formatter (ruff-format) also reformatted the dict comprehension in get_grading_deadlines() from multi-line to single-line. Accepted as-is since it is cosmetic only.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- API layer complete: all 3 deadline endpoints functional and tested
- Ready for 07-04 (Settings UI) and 07-05 (Dashboard inline editing)
- Propagate-defaults endpoint is idempotent; frontend can call it after any data sync

---
*Phase: 07-add-ta-grading-deadlines*
*Completed: 2026-03-15*
