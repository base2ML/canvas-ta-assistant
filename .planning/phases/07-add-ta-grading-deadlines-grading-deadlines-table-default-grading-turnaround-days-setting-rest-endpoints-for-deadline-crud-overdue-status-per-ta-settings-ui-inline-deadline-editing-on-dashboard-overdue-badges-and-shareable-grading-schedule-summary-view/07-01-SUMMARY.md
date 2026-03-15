---
phase: 07-add-ta-grading-deadlines
plan: 01
subsystem: testing
tags: [pytest, vitest, react-testing-library, sqlite, fastapi, wave0, tdd]

# Dependency graph
requires:
  - phase: 06-grader-identity-tracking
    provides: grader_id/graded_at in submissions, ta_users table, upsert patterns
provides:
  - 23 pytest test scaffolds covering grading_deadlines schema, API endpoints, overdue helper
  - 8 Vitest test scaffolds covering AssignmentStatusBreakdown deadline editor and GradingScheduleSummary
  - All tests RED (expected Wave 0 state)
affects:
  - 07-02 (schema/db implementation turns test_07_01_schema.py GREEN)
  - 07-03 (API implementation turns test_07_02_api.py GREEN)
  - 07-04 (frontend implementation turns AssignmentStatusBreakdown.test.jsx GREEN)
  - 07-05 (GradingScheduleSummary implementation turns GradingScheduleSummary.test.jsx GREEN)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - fresh_db fixture via monkeypatch on DB_PATH (consistent with phase 06 pattern)
    - AsyncClient httpx pattern for FastAPI endpoint tests (consistent with test_06_03_api.py)
    - Vitest + React Testing Library for frontend component tests

key-files:
  created:
    - tests/test_07_01_schema.py
    - tests/test_07_02_api.py
    - tests/test_07_03_overdue.py
    - canvas-react/src/components/AssignmentStatusBreakdown.test.jsx
    - canvas-react/src/components/GradingScheduleSummary.test.jsx
  modified: []

key-decisions:
  - "Wave 0 test scaffolds written before any implementation — all RED by design"
  - "test_07_01_schema.py uses fresh_db fixture via DATA_DIR monkeypatch (same as test_06_01_schema.py)"
  - "test_07_02_api.py uses DB_PATH monkeypatch pattern (same as test_06_03_api.py) plus asyncio.run + httpx ASGITransport"
  - "AssignmentStatusBreakdown.test.jsx added as new file (component exists but lacks deadline props)"
  - "GradingScheduleSummary.test.jsx scaffolded against non-existent component — fails on import (valid RED)"
  - "Excluded 'renders TA group names' test per plan note: GradingDeadlineItem has no ta_groups field"

patterns-established:
  - "Wave 0 pattern: write all tests first across 3 backend + 2 frontend files before any code"
  - "SQL strings split across lines with implicit concatenation to stay under 88-char ruff limit"

requirements-completed:
  - DEADLINE-DB-01
  - DEADLINE-DB-02
  - DEADLINE-SETTINGS-01
  - DEADLINE-API-01
  - DEADLINE-API-02
  - DEADLINE-API-03
  - DEADLINE-OVERDUE-01
  - DEADLINE-UI-01
  - DEADLINE-UI-02
  - DEADLINE-SUMMARY-01

# Metrics
duration: 6min
completed: 2026-03-15
---

# Phase 7 Plan 01: Wave 0 Test Scaffolds Summary

**23 pytest + 8 Vitest failing test scaffolds covering all phase 7 grading deadline requirements, written before implementation begins**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-15T22:26:57Z
- **Completed:** 2026-03-15T22:32:23Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Created 3 pytest files (23 tests total) covering schema, API, and overdue computation
- Created 2 Vitest files (8 tests total) covering inline deadline editor and summary component
- All tests confirmed RED via pytest --co and Vitest --run (expected Wave 0 state)
- Ruff lint/format pass on all Python test files

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend test scaffolds (schema + API + overdue)** - `51e9419` (test)
2. **Task 2: Frontend test scaffolds (AssignmentStatusBreakdown + GradingScheduleSummary)** - `9b96ccb` (test)

**Plan metadata:** (next commit)

## Files Created/Modified

- `tests/test_07_01_schema.py` - grading_deadlines table, unique constraint, index, upsert functions (9 tests)
- `tests/test_07_02_api.py` - settings turnaround field, GET/PUT deadline endpoints, propagate-defaults (9 tests)
- `tests/test_07_03_overdue.py` - is_overdue() helper: past/future deadline, null, invalid date (5 tests)
- `canvas-react/src/components/AssignmentStatusBreakdown.test.jsx` - inline editor + overdue badge (5 tests)
- `canvas-react/src/components/GradingScheduleSummary.test.jsx` - name, deadline date, overdue badge (3 tests)

## Decisions Made

- Used DATA_DIR monkeypatch in test_07_01_schema.py (same pattern as test_06_01_schema.py) for fresh DB isolation
- Used DB_PATH monkeypatch in test_07_02_api.py (same pattern as test_06_03_api.py) for API tests
- Removed unused `vi` import from GradingScheduleSummary.test.jsx after ESLint pre-commit hook failure
- Split long SQL strings using implicit string concatenation to satisfy ruff E501 (88-char limit)
- Dropped unused `row1` variable from test_update_on_conflict (ruff F841)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed ruff E501 and F841 violations blocking commit**
- **Found during:** Task 1 (pre-commit hook failure)
- **Issue:** SQL string literals exceeded 88-char line length limit; unused variable `row1`
- **Fix:** Split SQL strings with implicit concatenation; removed unused variable; shortened docstrings
- **Files modified:** tests/test_07_01_schema.py, tests/test_07_02_api.py, tests/test_07_03_overdue.py
- **Verification:** `uv run ruff check` passes with "All checks passed!"
- **Committed in:** 51e9419 (Task 1 commit)

**2. [Rule 3 - Blocking] Fixed ESLint no-unused-vars in GradingScheduleSummary.test.jsx**
- **Found during:** Task 2 (pre-commit hook failure)
- **Issue:** `vi` imported but not used in GradingScheduleSummary.test.jsx
- **Fix:** Removed `vi` from imports
- **Files modified:** canvas-react/src/components/GradingScheduleSummary.test.jsx
- **Verification:** ESLint pre-commit hook passes
- **Committed in:** 9b96ccb (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both blocking — pre-commit hook lint failures)
**Impact on plan:** Lint fixes only. Test content and coverage unchanged.

## Issues Encountered

None beyond the auto-fixed lint issues above.

## Next Phase Readiness

- All test scaffolds in place — implementation plans (07-02 through 07-05) can run tests as GREEN targets
- test_07_01_schema.py becomes GREEN when database.py gains grading_deadlines table + upsert functions
- test_07_02_api.py becomes GREEN when main.py gains deadline CRUD endpoints + turnaround setting
- test_07_03_overdue.py becomes GREEN when main.py exposes is_overdue() helper
- AssignmentStatusBreakdown.test.jsx becomes GREEN when component gains deadline editing props
- GradingScheduleSummary.test.jsx becomes GREEN when GradingScheduleSummary component is created

---
*Phase: 07-add-ta-grading-deadlines*
*Completed: 2026-03-15*
