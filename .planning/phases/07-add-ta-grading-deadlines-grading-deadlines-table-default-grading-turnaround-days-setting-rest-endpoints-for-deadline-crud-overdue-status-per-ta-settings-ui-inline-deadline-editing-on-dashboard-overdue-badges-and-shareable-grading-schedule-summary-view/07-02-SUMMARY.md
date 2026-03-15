---
phase: 07-add-ta-grading-deadlines
plan: 02
subsystem: database
tags: [sqlite, python, schema, crud, grading-deadlines]

# Dependency graph
requires:
  - phase: 07-01
    provides: test scaffolds for Phase 07 schema and API

provides:
  - grading_deadlines table with UNIQUE(course_id, assignment_id) constraint and index
  - upsert_grading_deadline() function with optional-conn pattern
  - upsert_grading_deadline_if_not_override() preserving is_override=1 rows via CASE WHEN
  - get_grading_deadlines() returning ordered list of dicts per course

affects:
  - 07-03 (API endpoints for deadline CRUD will call these functions)
  - 07-04 (overdue status logic reads from grading_deadlines)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Optional-conn pattern for all grading_deadline functions (same as upsert_ta_users)"
    - "CASE WHEN is_override = 1 THEN ... in ON CONFLICT DO UPDATE to preserve override flag"
    - "CREATE TABLE IF NOT EXISTS for idempotent migrations"

key-files:
  created: []
  modified:
    - database.py
    - tests/test_07_01_schema.py

key-decisions:
  - "Placed grading_deadlines table after ta_users block in init_db() for logical proximity to phase-06 grader identity tables"
  - "clear_refreshable_data() does NOT delete grading_deadlines — overrides survive sync by design"
  - "upsert_grading_deadline_if_not_override() uses CASE WHEN SQL inside ON CONFLICT DO UPDATE to conditionally skip is_override=1 rows in a single atomic operation"
  - "Fixed test scaffold bug: test_update_on_conflict selected only 2 columns but asserted on turnaround_days (a third column) — extended SELECT to include turnaround_days"

patterns-established:
  - "Optional-conn pattern: def f(conn: sqlite3.Connection | None = None) -> ..., with inner _upsert(c) dispatching on conn presence"
  - "Override-safe upsert: ON CONFLICT DO UPDATE SET col = CASE WHEN is_override = 1 THEN col ELSE excluded.col END"

requirements-completed:
  - DEADLINE-DB-01
  - DEADLINE-DB-02

# Metrics
duration: 5min
completed: 2026-03-15
---

# Phase 07 Plan 02: grading_deadlines DB Layer Summary

**SQLite grading_deadlines table with three CRUD functions (upsert, override-safe upsert, get) added to database.py; overrides survive sync by design**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-15T22:33:41Z
- **Completed:** 2026-03-15T22:37:55Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Added `grading_deadlines` table (9 columns, UNIQUE constraint, course index) to `init_db()` using `CREATE TABLE IF NOT EXISTS` for idempotent migration
- Implemented `upsert_grading_deadline()` with full insert/update-on-conflict logic and the optional-conn pattern established in Phase 06
- Implemented `upsert_grading_deadline_if_not_override()` using `CASE WHEN is_override = 1` in `ON CONFLICT DO UPDATE` to skip override rows atomically
- Implemented `get_grading_deadlines()` returning list of dicts ordered by assignment_id
- Confirmed `clear_refreshable_data()` does NOT touch grading_deadlines (overrides survive Canvas sync)
- All 9 new tests GREEN; full 106-test backend suite passing with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: grading_deadlines table + CRUD functions in database.py** - `fb7bc38` (feat)

**Plan metadata:** (docs commit below)

_Note: TDD task — tests were pre-written RED in 07-01, implementation turned them GREEN here._

## Files Created/Modified

- `database.py` - Added grading_deadlines table in init_db(), plus upsert_grading_deadline(), upsert_grading_deadline_if_not_override(), get_grading_deadlines()
- `tests/test_07_01_schema.py` - Fixed test scaffold: SELECT missing turnaround_days column in test_update_on_conflict

## Decisions Made

- Placed grading_deadlines table after ta_users block in init_db() for logical proximity to Phase 06 grader identity tables
- clear_refreshable_data() leaves grading_deadlines untouched — manual overrides must survive sync
- CASE WHEN approach in ON CONFLICT DO UPDATE is the cleanest way to implement conditional update in SQLite (no two-phase read+write needed)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test scaffold SELECT missing turnaround_days column**
- **Found during:** Task 1 (GREEN phase — running tests)
- **Issue:** test_update_on_conflict ran `SELECT updated_at, deadline_at FROM grading_deadlines` but then asserted `row2["turnaround_days"] == 5`, causing `IndexError: No item with that key` since turnaround_days was not in the result set
- **Fix:** Extended SELECT to `SELECT updated_at, deadline_at, turnaround_days FROM grading_deadlines`
- **Files modified:** tests/test_07_01_schema.py
- **Verification:** Test passes GREEN after fix; all 9 tests pass
- **Committed in:** fb7bc38 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug in test scaffold)
**Impact on plan:** Minimal — single-line SQL fix in pre-written test. No scope creep.

## Issues Encountered

None beyond the test scaffold column selection bug documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- grading_deadlines data layer complete; 07-03 can implement REST endpoints calling `upsert_grading_deadline()` and `get_grading_deadlines()`
- All three CRUD functions exported from database.py and ready for import in main.py
- No blockers

---
*Phase: 07-add-ta-grading-deadlines*
*Completed: 2026-03-15*
