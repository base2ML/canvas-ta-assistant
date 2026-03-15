---
phase: 06-grader-identity-tracking
plan: "01"
subsystem: database
tags: [sqlite, schema-migration, upsert, ta-users, grader-identity]

requires: []
provides:
  - ta_users table DDL with id, course_id, name, email, enrollment_type, synced_at columns
  - idx_ta_users_course index on ta_users(course_id)
  - grader_id INTEGER column on submissions table (idempotent migration)
  - graded_at TIMESTAMP column on submissions table (idempotent migration)
  - upsert_ta_users() function following established upsert_users() pattern
  - clear_refreshable_data() updated to delete ta_users per course_id
affects:
  - 06-02 (canvas_sync.py: call upsert_ta_users with TA/instructor enrollments)
  - 06-03 (API endpoint to expose ta_users lookup)
  - 06-04 (EnhancedTADashboard: TA breakdown by grader_id)

tech-stack:
  added: []
  patterns:
    - "TDD (Red→Green) for schema changes: write failing tests first, then implement"
    - "idempotent ALTER TABLE migration via try/except sqlite3.OperationalError"
    - "upsert with ON CONFLICT(id) DO UPDATE SET following upsert_users() signature"

key-files:
  created:
    - tests/test_06_01_schema.py
  modified:
    - database.py

key-decisions:
  - "Placed ta_users table and migrations immediately after submissions table/indexes in init_db() for locality"
  - "Used try/except sqlite3.OperationalError pattern (not contextlib.suppress) for grader_id/graded_at migrations, consistent with assignment_group_id migration"
  - "upsert_ta_users() accepts optional conn parameter, uses inner _upsert() pattern identical to upsert_users()"
  - "clear_refreshable_data() clears ta_users per course_id since TA users are re-fetched on every sync"

patterns-established:
  - "New tables in init_db() placed after logically related table (ta_users after submissions)"
  - "Column migrations immediately follow the table they extend in init_db()"

requirements-completed: [GRADER-DB-01]

duration: 3min
completed: "2026-03-15"
---

# Phase 06 Plan 01: ta_users Schema Foundation Summary

**SQLite ta_users lookup table and submissions grader_id/graded_at columns added via idempotent migrations, with upsert_ta_users() function for Canvas TA/instructor sync**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-15T02:50:26Z
- **Completed:** 2026-03-15T02:53:11Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments

- Created ta_users table with 6-column schema and course_id index for grader identity resolution
- Added grader_id and graded_at columns to submissions via idempotent ALTER TABLE migrations
- Implemented upsert_ta_users() following the established inner-function pattern from upsert_users()
- Updated clear_refreshable_data() to include ta_users, so TA users refresh on every Canvas sync
- All 11 new tests pass; 79-test suite remains green (no regressions)

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 test scaffold — ta_users schema and upsert** - `53c7155` (test)
2. **Task 2: Implement ta_users table, column migrations, upsert_ta_users, clear update** - `0f8c469` (feat)

_Note: TDD tasks — test commit (RED) then implementation commit (GREEN)_

## Files Created/Modified

- `tests/test_06_01_schema.py` - 11 tests across 4 classes: TestTAUsersTable, TestSubmissionsMigration, TestUpsertTAUsers, TestClearRefreshableData
- `database.py` - ta_users DDL, idx_ta_users_course index, grader_id/graded_at migrations, upsert_ta_users(), clear_refreshable_data() update

## Decisions Made

- Placed ta_users table and its migrations immediately after submissions table/indexes in init_db() for logical proximity
- Used try/except sqlite3.OperationalError migration pattern (not contextlib.suppress) for grader_id/graded_at migrations, consistent with assignment_group_id migration
- upsert_ta_users() uses the same inner `_upsert()` function pattern and optional `conn` parameter as upsert_users() — Plan 02 can call it within a transaction
- clear_refreshable_data() clears ta_users per course_id since TA roster may change between syncs

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Ruff E501 (line too long) triggered on docstrings and SQL strings during pre-commit hook. Fixed by shortening docstrings and reformatting the INSERT SQL across multiple lines. No logic impact.

## Next Phase Readiness

- Plan 02 (canvas_sync.py) can import and call `db.upsert_ta_users()` directly
- The `grader_id` and `graded_at` columns are ready to receive values from Canvas submission data
- clear_refreshable_data() will automatically flush stale ta_users on each sync cycle

---
*Phase: 06-grader-identity-tracking*
*Completed: 2026-03-15*
