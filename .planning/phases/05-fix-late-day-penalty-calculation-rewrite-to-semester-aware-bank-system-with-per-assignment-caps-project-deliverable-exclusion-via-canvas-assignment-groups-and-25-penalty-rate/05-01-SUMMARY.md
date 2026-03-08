---
phase: "05-fix-late-day-penalty-calculation"
plan: "01"
subsystem: "database"
tags: ["sqlite", "schema", "migration", "assignment-groups", "tdd"]
dependency_graph:
  requires: []
  provides:
    - "assignment_groups table in SQLite"
    - "assignment_group_id column on assignments table"
    - "upsert_assignment_groups() function"
    - "clear functions delete assignment_groups rows"
  affects:
    - "canvas_sync.py (next plan: call upsert_assignment_groups)"
    - "late day algorithm (uses assignment_group_id for project exclusion)"
    - "frontend Settings UI (reads group names)"
tech_stack:
  added: []
  patterns:
    - "TDD: RED (failing tests) -> GREEN (implementation) -> verify"
    - "SQLite migration via try/except sqlite3.OperationalError"
    - "ON CONFLICT DO UPDATE SET upsert pattern"
    - "Inner _upsert() closure with conn=None fallback"
key_files:
  created:
    - "tests/conftest.py"
    - "tests/test_05_01_schema.py"
  modified:
    - "database.py"
decisions:
  - "Used established try/except sqlite3.OperationalError migration pattern (not contextlib.suppress) for assignment_group_id column, consistent with enrollment_status migration"
  - "Placed assignment_groups table CREATE immediately after assignments table block in init_db() for logical schema organization"
  - "Placed DELETE FROM assignment_groups after DELETE FROM assignments in both clear functions to maintain consistent ordering"
metrics:
  duration: "3 min"
  completed_date: "2026-03-01"
  tasks_completed: 2
  files_modified: 3
---

# Phase 05 Plan 01: SQLite Schema — assignment_groups Table and Migration Summary

**One-liner:** Extended SQLite schema with assignment_groups table and idempotent migration adding assignment_group_id to assignments, enabling the semester-bank late day system's project exclusion logic.

## What Was Built

Added the foundational database layer required by the semester-aware late day bank system. All downstream plans (sync, algorithm, frontend) depend on `assignment_group_id` being stored on assignments and group names being queryable.

### Changes to `database.py`

**`init_db()` additions:**
- `assignment_groups` table with columns: `id` (INTEGER PK), `course_id` (TEXT NOT NULL), `name` (TEXT NOT NULL), `position` (INTEGER), `synced_at` (TIMESTAMP)
- `idx_assignment_groups_course` index on `assignment_groups(course_id)`
- Idempotent migration: `ALTER TABLE assignments ADD COLUMN assignment_group_id INTEGER` wrapped in `try/except sqlite3.OperationalError` with `logger.info` on success

**New function `upsert_assignment_groups(course_id, groups, conn=None)`:**
- Mirrors `upsert_assignments()` pattern exactly (inner `_upsert()` closure, `conn=None` default, `get_db_connection()` fallback)
- `ON CONFLICT(id) DO UPDATE SET` for idempotent upsert
- Returns `len(groups)` count

**Extended `upsert_assignments()`:**
- Data tuple now includes `assignment.get("assignment_group_id")` after `html_url`
- Both INSERT column list and ON CONFLICT UPDATE SET include `assignment_group_id`

**Updated `clear_refreshable_data()`:**
- Added `DELETE FROM assignment_groups WHERE course_id = ?` after assignments DELETE

**Updated `clear_course_data()`:**
- Added `DELETE FROM assignment_groups WHERE course_id = ?` after assignments DELETE inside `_clear()`

## Tests Written (TDD)

19 tests in `tests/test_05_01_schema.py` covering:
- `TestAssignmentGroupsTableCreation` (6 tests): table exists, columns, index, migration, idempotency, NULL default
- `TestUpsertAssignmentGroups` (6 tests): count, insert, ON CONFLICT update, conn=None, conn=existing, missing position
- `TestUpsertAssignmentsWithGroupId` (3 tests): saves field, updates on conflict, null ok
- `TestClearFunctions` (4 tests): refreshable clear, course isolation, nuclear clear, re-insert after clear

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 53d1ba4 | test | Add failing tests (RED phase) |
| 1275656 | feat | Add assignment_groups table and migration (Task 1 GREEN) |
| a98377e | feat | Add upsert_assignment_groups() and extend clear/upsert functions (Task 2 GREEN) |

## Verification

All 19 tests pass. Ruff lint and format checks pass on `database.py`.

```
19 passed, 39 warnings in 0.17s
```

Plan verification scripts from PLAN.md both output `PASS`.

## Deviations from Plan

None — plan executed exactly as written. The `conftest.py` file was a necessary addition (Rule 3: blocking issue) since no test infrastructure existed; adding it was a prerequisite to running tests rather than a deviation from plan scope.

## Self-Check: PASSED

Files exist:
- `database.py` — FOUND
- `tests/test_05_01_schema.py` — FOUND
- `tests/conftest.py` — FOUND

Commits exist:
- 53d1ba4 — FOUND (test RED phase)
- 1275656 — FOUND (Task 1 feat)
- a98377e — FOUND (Task 2 feat)

Success criteria verified:
- [x] assignment_groups table exists after init_db()
- [x] assignments table has assignment_group_id column after init_db()
- [x] Migration is idempotent (no error on repeated init_db() calls)
- [x] upsert_assignment_groups() works standalone and within a transaction
- [x] upsert_assignments() saves assignment_group_id
- [x] clear_refreshable_data() and clear_course_data() delete assignment_groups rows
- [x] All existing tests continue to pass (19/19)
- [x] Ruff lint and format checks pass
