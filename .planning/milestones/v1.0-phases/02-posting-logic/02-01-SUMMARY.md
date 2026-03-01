---
phase: 02-posting-logic
plan: 01
subsystem: api
tags: [fastapi, canvasapi, sqlite, sse-starlette, pydantic, retry-logic, templates]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "comment_templates table, comment_posting_history table, check_duplicate_posting(), get_posting_history(), get_template_by_id(), get_templates()"
provides:
  - post_submission_comment() in canvas_sync.py with exponential backoff retry
  - render_template() function for variable substitution
  - calculate_late_days_for_user() helper for per-student late day data
  - resolve_template() helper for template lookup by ID or type
  - POST /api/comments/preview/{assignment_id} endpoint
  - GET /api/comments/history endpoint
  - sse-starlette dependency (ready for Plan 02 SSE streaming)
affects:
  - 02-02 (SSE bulk posting endpoint will call post_submission_comment and render_template)

# Tech tracking
tech-stack:
  added: [sse-starlette>=2.0]
  patterns:
    - Exponential backoff retry (1s, 2s, 4s) only for 429 rate limit errors
    - Template rendering via Python str.format() with controlled variable set
    - Grace period subtraction before late day calculation (ceiling division)
    - Preview-before-post pattern with duplicate detection per user

key-files:
  created: []
  modified:
    - pyproject.toml
    - canvas_sync.py
    - main.py

key-decisions:
  - "Retry only 429 errors with exponential backoff — other errors (401/403/404) raise immediately for fast failure"
  - "render_template uses str.format() with ALLOWED_TEMPLATE_VARIABLES context dict — prevents undefined variable injection"
  - "calculate_late_days_for_user replicates existing get_late_days_data logic — ensures consistency between dashboard and preview"
  - "resolve_template raises 404 for missing templates and 400 if neither template_id nor template_type provided"
  - "preview endpoint calls validate_posting_safety() — test mode enforcement applies to preview too"

patterns-established:
  - "Canvas API posting: get_canvas_client() -> get_course() -> get_assignment() -> get_submission() -> submission.edit()"
  - "Late day calculation: grace period subtraction, math.ceil(total_seconds/86400), penalty_days=min(days_late, max_late_days)"
  - "Template resolution: try template_id first, fall back to template_type, error on neither"

# Metrics
duration: 2min
completed: 2026-02-17
---

# Phase 2 Plan 01: Posting Infrastructure Summary

**Canvas posting function with exponential backoff retry, template rendering with late day variable substitution, and preview/history endpoints for safe comment inspection before bulk posting**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-17T01:06:33Z
- **Completed:** 2026-02-17T01:08:41Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `post_submission_comment()` in canvas_sync.py handles Canvas API posting with 429 retry (1s, 2s, 4s) and immediate fail for other errors
- `render_template()`, `calculate_late_days_for_user()`, `resolve_template()` helper functions established for Plan 02 to consume
- Preview endpoint (`POST /api/comments/preview/{assignment_id}`) renders templates with real student data and shows duplicate status per user without touching Canvas API
- History endpoint (`GET /api/comments/history`) returns posting history filterable by course, assignment, and status
- sse-starlette 3.2.0 installed, ready for Plan 02 SSE streaming endpoint

## Task Commits

Each task was committed atomically:

1. **Task 1: Add sse-starlette dependency and Canvas posting function with retry** - `dc53ed8` (feat)
2. **Task 2: Add template rendering, preview endpoint, and history endpoint** - `cb98ca8` (feat)

**Plan metadata:** TBD (docs: complete plan)

## Files Created/Modified
- `pyproject.toml` - Added sse-starlette>=2.0 dependency
- `canvas_sync.py` - Added datetime import, post_submission_comment() function with exponential backoff
- `main.py` - Added PostCommentsRequest/CommentPreview/PreviewResponse models, render_template(), calculate_late_days_for_user(), resolve_template(), preview endpoint, history endpoint

## Decisions Made
- Retry only 429 errors with exponential backoff — other Canvas errors (401, 403, 404) raise immediately so callers fail fast
- `render_template` uses `str.format()` with a controlled ALLOWED_TEMPLATE_VARIABLES context dict to prevent undefined variable injection
- `calculate_late_days_for_user` replicates existing `get_late_days_data` endpoint logic exactly, ensuring dashboard and preview produce consistent numbers
- Preview endpoint enforces `validate_posting_safety()` — test mode restrictions apply even for read-only preview calls (defense in depth)
- `resolve_template` parses `template_variables` JSON string to list before returning, matching the existing pattern in `get_templates` endpoint

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Ruff `E501` (line too long) on two strings — fixed by breaking f-strings across lines and shortening docstrings
- Pre-commit ruff formatter removed unnecessary parentheses on one-line f-string — staged and re-committed

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Canvas posting function, template rendering, and preview endpoint are ready for Plan 02 SSE bulk posting endpoint to consume
- sse-starlette is installed and importable
- No blockers

## Self-Check: PASSED

- canvas_sync.py: FOUND
- main.py: FOUND
- pyproject.toml: FOUND
- 02-01-SUMMARY.md: FOUND
- Commit dc53ed8 (Task 1): FOUND
- Commit cb98ca8 (Task 2): FOUND

---
*Phase: 02-posting-logic*
*Completed: 2026-02-17*
