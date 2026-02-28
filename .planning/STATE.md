# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-21)

**Core value:** Safely and efficiently post accurate late day feedback to student submissions, preventing manual errors and saving TA time while ensuring students receive timely, consistent communication about their late day status.
**Current focus:** Milestone v1.0 complete — ready for sandbox testing and next milestone planning

## Current Position

Milestone: v1.0 Late Day Comment Posting (COMPLETE)
Phases: 3/3 complete (8 plans total)
Status: Shipped
Last activity: 2026-02-22 - Filtered enrollment timeline to changes-only and added SVG enrollment line chart

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 6 (all phases complete)
- Average duration: 2 min
- Total execution time: 0.16 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 2 | 7 min | 4 min |
| 02 | 2 | 3 min | 2 min |
| 03 | 4 | ~10 min | ~2.5 min |

| Phase 01 P01 | 3 min | 2 tasks | 1 files |
| Phase 01 P02 | 4 min | 2 tasks | 1 files |
| Phase 02 P01 | 2 min | 2 tasks | 3 files |
| Phase 02 P02 | 1 min | 1 tasks | 1 files |
| Phase 03 P01 | 1 min | 2 tasks | 1 files |
| Phase 03 P02 | 6 min | 3 tasks | 2 files |
| Phase 03 P03 | 3 min | 1 tasks | 1 files |
| Phase 03-ui-integration P04 | 0 | 1 tasks | 0 files |
| Quick 1 | 3 min | 2 tasks | 6 files |
| Quick 2 | 1 min | 1 tasks | 1 files |
| Quick 3 | 2 min | 1 tasks | 1 files |
| Quick 4 | 3 min | 1 tasks | 1 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Two separate message templates (penalty vs non-penalty) — simpler than conditional templating
- Test mode toggle + confirmation dialogs — defense in depth prevents accidental live posting
- Track posting history in SQLite — prevents duplicate posts, provides audit trail
- Pre-populated default templates — TAs can use immediately, no blank slate
- Dry run mode for testing — safe testing without actual API calls before sandbox verification
- [Phase 01]: UNIQUE constraint on (course_id, assignment_id, user_id, template_id) for duplicate prevention at database level
- [Phase 01]: ON CONFLICT DO UPDATE for upsert behavior to allow comment corrections without duplicates
- [Phase 01]: Auto-populate default templates in init_db() so TAs can use immediately without manual setup
- [Phase 01 P02]: Test-render templates with dummy data to catch syntax errors — simpler than regex parsing
- [Phase 01 P02]: Allow partial updates for settings with optional fields — frontend can update one setting at a time
- [Phase 01 P02]: Separate validate_posting_safety function (not middleware) — posting endpoints will explicitly call validation for clear control flow
- [Phase 02 P01]: Retry only 429 errors with exponential backoff — other errors (401/403/404) raise immediately for fast failure
- [Phase 02 P01]: render_template uses str.format() with ALLOWED_TEMPLATE_VARIABLES context dict — prevents undefined variable injection
- [Phase 02 P01]: calculate_late_days_for_user replicates existing get_late_days_data logic — ensures consistency between dashboard and preview
- [Phase 02 P01]: Preview endpoint enforces validate_posting_safety() — test mode applies to preview too (defense in depth)
- [Phase 02 P02]: Pre-flight validation before SSE generator — enables HTTP 4xx errors for top-level failures (safety, missing template, missing assignment) rather than SSE error events
- [Phase 02 P02]: users list not fetched in post_comments — events use user_id only, frontend has user data, avoids unused variable
- [Phase 02 P02]: Rate limiting after successful posts only — 0.5s delay applied only for real Canvas API calls, not skips/errors/dry_runs
- [Phase 03 P01]: Edit-only scope for templates (CONF-03) — templates always pre-populated, no create/delete path needed
- [Phase 03 P01]: No re-fetch after template save — preserves textarea focus and cursor position
- [Phase 03 P01]: Button disabled when template id is null — guards against PUT to /api/templates/null before load completes
- [Phase 03 P02]: Tasks 2+3 combined into one commit — ESLint no-unused-vars blocks committing state/handlers without JSX usage
- [Phase 03 P02]: React Fragment wrapper (<></>) for modal rendering — fixed-position overlays need fragment sibling root context
- [Phase 03 P02]: onDry_run handler naming preserves underscore to match backend SSE event name exactly
- [Phase 03 P02]: Settings fetch on mount is best-effort (silent catch) — production warning is advisory, not blocking
- [Phase 03 P03]: loadPostingHistory depends on postAssignmentId — useCallback re-creates when assignment changes, triggering useEffect re-fetch automatically
- [Phase 03 P03]: History table only renders when showPostingPanel && postingHistory.length > 0 — avoids empty-state clutter
- [Phase 03 P03]: History table limited to 50 most recent entries — keeps table lightweight
- [Phase 03 P04]: Human verification required for visual UI correctness — automated tests cannot verify rendering quality and workflow UX
- [Quick 1]: activeCourseId derived at App.jsx level from courses[0] and passed as prop — single source of truth for course selection across all pages
- [Quick 1]: selectedCourse excluded from useEffect deps in EnhancedTADashboard and PeerReviewTracking — used only as comparison guard, not reactive input; eslint-disable comment added with explanation
- [Quick 1]: course_term stored in SQLite settings after each sync as course_term_{course_id} — enables /api/canvas/courses to return term without extra Canvas API calls
- [Quick 2]: include=["term"] added only to sync_course_data's get_course call — fetch_available_courses already passed it correctly to get_courses
- [Quick 2]: Debug logging placed inside seen_ids guard in fetch_available_courses — logs only new (non-duplicate) courses, helps diagnose when Canvas returns enrollment_term=None
- [Quick 3]: Canvas API returns term data under 'term' key (not 'enrollment_term') when include=["term"] is passed — _get_term_name() previously only checked enrollment_term so term was always None; fixed by iterating both attribute names
- [Quick 4]: Best-effort inner try/catch for sync-status fetch in loadCourseData — prevents sync-status failure from breaking main data load; falls back to new Date()
- [Quick 4]: IIFE pattern used for chart and filter sections in EnrollmentTracking — keeps derived variables scoped without polluting component scope

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 1 | Fix course selection not propagating to dashboard pages and add course name with term to header and settings | 2026-02-21 | 10dc439 | [1-fix-course-selection-not-propagating-to-](./quick/1-fix-course-selection-not-propagating-to-/) |
| 2 | Fix term information not appearing in Browse Courses dropdown and course header | 2026-02-22 | 01660eb | [2-research-the-canvas-api-and-determine-wh](./quick/2-research-the-canvas-api-and-determine-wh/) |
| 3 | Fix Last Updated timestamp to show actual Canvas sync time instead of browser clock | 2026-02-22 | 3736c35 | [3-the-last-updated-time-on-the-main-dashbo](./quick/3-the-last-updated-time-on-the-main-dashbo/) |
| 4 | Filter enrollment timeline to changes-only and add SVG enrollment line chart | 2026-02-22 | 48ca026 | [4-filter-enrollment-sync-history-to-only-s](./quick/4-filter-enrollment-sync-history-to-only-s/) |

## Session Continuity

Last session: 2026-02-22
Stopped at: Completed quick/4-filter-enrollment-sync-history-to-only-s/4-PLAN.md
Resume file: None
