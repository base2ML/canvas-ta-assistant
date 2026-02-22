---
phase: quick
plan: 2
subsystem: api
tags: [canvas-api, sqlite, sync, term, canvasapi]

requires: []
provides:
  - "canvas_sync.sync_course_data requests include=['term'] so enrollment_term is available on the course object"
  - "fetch_available_courses logs raw enrollment_term and term_name for diagnostic purposes"
affects: []

tech-stack:
  added: []
  patterns:
    - "Always pass include=['term'] when calling canvas.get_course() to receive enrollment term data"
    - "Add logger.debug lines in API loops to surface raw Canvas API response attributes"

key-files:
  created: []
  modified:
    - canvas_sync.py

key-decisions:
  - "Add include=['term'] only to sync_course_data's get_course call — fetch_available_courses already passed it correctly to get_courses"
  - "Debug logging placed before courses.append() inside the seen_ids guard — logs only new (non-duplicate) courses"

patterns-established:
  - "Canvas API term fetch: get_course(course_id, include=['term']) returns enrollment_term object with id/name/start_at/end_at"
  - "Diagnostic pattern: log raw getattr(course, 'enrollment_term', None) and getattr(course, 'term_name', None) to distinguish API absence from code errors"

requirements-completed: []

duration: 1min
completed: 2026-02-21
---

# Quick 2: Fix term info not appearing in Browse Courses dropdown and course header

**Fixed two bugs in canvas_sync.py: added include=["term"] to sync_course_data's get_course call (primary) and added enrollment_term debug logging in fetch_available_courses (secondary)**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-02-21T03:08:01Z
- **Completed:** 2026-02-21T03:09:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Fixed primary bug: `canvas.get_course(course_id)` changed to `canvas.get_course(course_id, include=["term"])` in `sync_course_data` — ensures Canvas API returns `enrollment_term` on the course object so `_get_term_name` can extract the term name and `sync_course_data` can store it in SQLite via `db.set_setting(f"course_term_{course_id}", ...)`
- Added diagnostic debug logging inside both `fetch_available_courses` loops (TA and teacher enrollment) to log raw `enrollment_term` and `term_name` values per course
- Ruff lint and format checks pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix sync_course_data to request term data and add diagnostic logging** - `01660eb` (fix)

## Files Created/Modified
- `canvas_sync.py` - Fixed `get_course(course_id, include=["term"])` call in `sync_course_data`; added `logger.debug` lines in both `fetch_available_courses` enrollment loops

## Decisions Made
- `fetch_available_courses` already passed `include=["term"]` correctly to `get_courses()` — no change needed there, only `sync_course_data` was broken
- Debug logging is placed inside the `if course_id not in seen_ids:` guard to avoid logging duplicates

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- After a sync, `sqlite3 data/canvas.db "SELECT key, value FROM settings WHERE key LIKE 'course_term_%';"` should return a non-empty row with the actual term name (e.g., `course_term_12345 | Spring 2025`)
- If `enrollment_term` is still `None` after sync, check debug logs — this would indicate Canvas is not associating courses with terms (Canvas configuration issue, not a code bug)
- `/api/canvas/courses` endpoint will now return non-null `term` field for configured courses

---
*Phase: quick*
*Completed: 2026-02-21*
