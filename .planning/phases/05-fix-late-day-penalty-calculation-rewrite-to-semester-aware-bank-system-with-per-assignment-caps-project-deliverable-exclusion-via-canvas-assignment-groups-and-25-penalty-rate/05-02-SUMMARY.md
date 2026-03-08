---
phase: 05-fix-late-day-penalty-calculation
plan: 02
subsystem: api
tags: [canvas-api, sqlite, assignment-groups, sync, fastapi]

# Dependency graph
requires:
  - phase: 05-01
    provides: assignment_groups table schema and upsert_assignment_groups() function
provides:
  - canvas_sync.py fetches Canvas assignment groups and annotates each assignment dict with assignment_group_id
  - database.get_assignment_groups() query function for stored groups
  - GET /api/canvas/assignment-groups/{course_id} endpoint returning {groups, count}
affects:
  - 05-03 (late day algorithm reads assignment_group_id from assignments)
  - 05-04 (Settings UI uses /api/canvas/assignment-groups endpoint for group selector)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - course.get_assignment_groups() canvasapi call for Canvas syllabus categories
    - Safe getattr attribute access for Canvas API objects (getattr(obj, attr, None))
    - Fetch block pattern with logger.info(duration + count) matching existing sync blocks
    - db.upsert_*() called inside transaction block before dependent data

key-files:
  created:
    - tests/test_05_02_sync_assignment_groups.py
    - tests/test_05_02_assignment_groups_endpoint.py
  modified:
    - canvas_sync.py
    - database.py
    - main.py

key-decisions:
  - "Fetch assignment groups between assignments and users fetch blocks (after assignments, before users) for logical data dependency ordering"
  - "upsert_assignment_groups() called before upsert_assignments() inside transaction so foreign-key-style relationship is consistent"
  - "Test normalized whitespace comparison for getattr pattern to handle ruff line-splitting"

patterns-established:
  - "Fetch block pattern: start_time variable, loop with getattr, logger.info(duration + count)"
  - "Endpoint pattern: try/except with logger.error(exc_info=True) and HTTP 500, returns {groups, count}"

requirements-completed:
  - LATE-SYNC-01
  - LATE-API-GROUPS-01

# Metrics
duration: 3min
completed: 2026-03-01
---

# Phase 05 Plan 02: Assignment Groups Sync and API Endpoint Summary

**Canvas assignment groups fetched during sync and annotated onto assignment dicts; GET /api/canvas/assignment-groups/{course_id} wires groups to Settings UI**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-01T17:29:33Z
- **Completed:** 2026-03-01T17:32:32Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 5 (canvas_sync.py, database.py, main.py, 2 test files)

## Accomplishments

- Extended `sync_course_data()` in canvas_sync.py to call `course.get_assignment_groups()`, build `assignment_groups_data` list, and call `db.upsert_assignment_groups()` inside the transaction block before `upsert_assignments()`
- Added `assignment_group_id` field to each assignment dict using `getattr(assignment, "assignment_group_id", None)` — the canonical safe attribute access pattern
- Added `database.get_assignment_groups()` querying `assignment_groups` table ordered by position ASC, name ASC
- Added `GET /api/canvas/assignment-groups/{course_id}` endpoint in main.py returning `{"groups": [...], "count": N}` with HTTP 500 error handling

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: failing tests for annotation and sync** - `8751b23` (test)
2. **Task 1 GREEN: fetch assignment groups and annotate assignments** - `ea4b10f` (feat)
3. **Task 2 RED: failing tests for assignment-groups endpoint** - `0e3137f` (test)
4. **Task 2 GREEN: GET /api/canvas/assignment-groups endpoint** - `223de42` (feat)

_Note: TDD tasks have separate test and implementation commits_

## Files Created/Modified

- `canvas_sync.py` - Added assignment groups fetch block and assignment_group_id annotation in sync_course_data()
- `database.py` - Added get_assignment_groups() query function
- `main.py` - Added GET /api/canvas/assignment-groups/{course_id} endpoint
- `tests/test_05_02_sync_assignment_groups.py` - 7 tests verifying canvas_sync.py changes
- `tests/test_05_02_assignment_groups_endpoint.py` - 8 tests verifying database.py and main.py changes

## Decisions Made

- Ordered fetch blocks: assignment groups fetched after assignments (since assignment_group_id is on the assignment object, not the group) and before users for logical organization
- `upsert_assignment_groups()` placed before `upsert_assignments()` inside the transaction so group rows exist before assignment rows reference them
- Test for `getattr` pattern uses normalized whitespace comparison to handle ruff auto-formatting splitting long lines

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Ruff pre-commit hook reformatted test file on first commit attempt — fixed E501 and SIM102 violations in test file before re-committing
- Test assertion for exact `getattr(assignment, "assignment_group_id", None)` string failed because ruff formatter split the call across lines — updated test to check for `"assignment_group_id"` string literal presence (semantically equivalent, formatter-safe)

## Next Phase Readiness

- Plan 05-03 (late day algorithm) can now read `assignment_group_id` from assignments and use excluded group IDs from Settings
- Plan 05-04 (Settings UI) can call `/api/canvas/assignment-groups/{course_id}` to populate the multi-select group picker
- All 34 tests pass; main.py imports cleanly; ruff passes on all modified files

---
*Phase: 05-fix-late-day-penalty-calculation*
*Completed: 2026-03-01*
