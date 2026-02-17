# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-15)

**Core value:** Safely and efficiently post accurate late day feedback to student submissions, preventing manual errors and saving TA time while ensuring students receive timely, consistent communication about their late day status.
**Current focus:** Phase 3: UI Integration

## Current Position

Phase: 3 of 3 (UI Integration)
Plan: 2 of ? in current phase
Status: In progress
Last activity: 2026-02-17 — 03-02 complete: Comment posting workflow in LateDaysTracking

Progress: [████████░░] 80%

## Performance Metrics

**Velocity:**
- Total plans completed: 4
- Average duration: 2 min
- Total execution time: 0.14 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 2 | 7 min | 4 min |
| 02 | 2 | 3 min | 2 min |

| Phase 01 P01 | 3 min | 2 tasks | 1 files |
| Phase 01 P02 | 4 min | 2 tasks | 1 files |
| Phase 02 P01 | 2 min | 2 tasks | 3 files |
| Phase 02 P02 | 1 min | 1 tasks | 1 files |
| Phase 03 P01 | 1 min | 2 tasks | 1 files |
| Phase 03 P02 | 6 min | 3 tasks | 2 files |

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

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-17
Stopped at: Completed 03-ui-integration/03-02-PLAN.md
Resume file: None
