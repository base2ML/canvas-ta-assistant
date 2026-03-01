# Canvas TA Dashboard

## What This Is

A Canvas LMS TA Dashboard that helps Teaching Assistants manage grading workflows and automate posting late day feedback comments directly to student submissions via the Canvas API. The dashboard displays assignment status, TA workload, late days tracking, peer review monitoring, enrollment trends, and provides a complete template management and comment posting workflow with safety controls — all synced from Canvas via a single global refresh button and stored locally in SQLite.

## Core Value

Safely and efficiently post accurate late day feedback to student submissions, preventing manual errors and saving TA time while ensuring students receive timely, consistent communication about their late day status.

## Requirements

### Validated

<!-- Shipped and confirmed valuable -->

- ✓ Canvas LMS data synchronization (assignments, users, submissions, groups) — existing
- ✓ SQLite local database with automatic sync on startup and manual refresh — existing
- ✓ FastAPI REST API with Pydantic models and error handling — existing
- ✓ React 19.1.1 frontend with Tailwind CSS v4 — existing
- ✓ Docker deployment with Nginx reverse proxy — existing
- ✓ Settings page for course configuration and sync history — existing
- ✓ Late days tracking calculation and display (penalty_days, late_days_remaining, penalty_percent) — existing
- ✓ TA grading workload management with group assignments — existing
- ✓ Peer review tracking — existing
- ✓ Enrollment tracking with status history and SVG line chart — existing + v1.1
- ✓ Post late day comments to Canvas submissions via Canvas API — v1.0
- ✓ Configurable message templates in Settings page (two templates: penalty and non-penalty) — v1.0
- ✓ Pre-populated default templates based on existing logic with variable placeholders — v1.0
- ✓ Variable substitution in templates: {days_late}, {days_remaining}, {penalty_days}, {penalty_percent}, {max_late_days} — v1.0
- ✓ Bulk posting workflow: select assignment, post comments to all students — v1.0 (SSE streaming)
- ✓ Preview modal for penalty cases before posting (high-stakes messages) — v1.0
- ✓ Safety mechanisms: test mode toggle in Settings + confirmation dialog showing course name — v1.0 (plus production warning banner)
- ✓ Duplicate prevention: track posted comments in database, show "Already posted" status — v1.0
- ✓ Error handling: graceful failures with detailed error reports after batch completes — v1.0 (exponential backoff on rate limits)
- ✓ Dry run mode for safe testing without actual API calls — v1.0
- ✓ Manual comment override for edge cases (edit individual comments before posting) — v1.0
- ✓ Max late days per assignment configuration in Settings — v1.0
- ✓ Single global "Refresh Data" button in header bar — v1.1
- ✓ Header displays last synced timestamp, consistent across all pages — v1.1
- ✓ After sync, all dashboard pages automatically reload their data (refreshTrigger cascade) — v1.1
- ✓ Settings page retains "Save Settings" only (no sync trigger in Settings) — v1.1

### Active

<!-- Next milestone scope — v1.2, TBD -->

*(Defined during `/gsd:new-milestone`)*

### Out of Scope

- Automated scheduling of comment posting — manual trigger only, no cron/background jobs
- Comment editing after posting — use Canvas UI directly
- Multi-course bulk operations — posting is per-course only
- Email notifications to students — Canvas handles this natively when comments are posted
- Comment templates with rich formatting — plain text only
- Auto-refresh on a timer — sync is user-initiated by design
- PeerReview "Refresh" button removal — peer review analysis is parameterized and independent of Canvas sync

## Context

**Current State (v1.1 shipped 2026-03-01):**
- Unified data refresh: one global header button syncs Canvas data and cascades to all dashboard pages
- Late day comment posting fully integrated with template management and safety controls
- Enrollment tracking page with changes-only timeline and SVG trend chart
- Codebase: ~8,033 lines total (Python + JavaScript)
- Tech stack: FastAPI + SQLite + React 19.1.1 + Tailwind CSS v4 + canvasapi + SSE

**Architecture notes:**
- `refreshTrigger` integer counter in App.jsx is the global sync signal pattern — increment to trigger all consumers
- SSE bulk posting at `/api/comments/post/{assignment_id}` needs Nginx `proxy_buffering off` for Docker (see tech debt in v1.1 audit)
- All Canvas sync goes through `POST /api/canvas/sync`; status pre-populated from `GET /api/canvas/sync/status` on mount

**Testing:**
- CRITICAL: All testing must be done on sandbox Canvas course (ID: 20960000000447574)
- Never test on live course with real students

**Student Data:**
- Comments include student names, late day calculations, penalty information
- All data is PII and educational records protected under FERPA

## Constraints

- **Tech Stack**: FastAPI backend, React frontend, SQLite database, Canvas API via canvasapi library
- **Safety**: Must never accidentally post to live course during development/testing
- **Canvas API**: Rate limits apply (use slowapi middleware), API token required
- **Security**: Canvas API token stored in .env file, never committed
- **Data Privacy**: Handle student PII per FERPA guidelines
- **Deployment**: Local Docker-only, no cloud dependencies
- **Testing**: Sandbox course ID 20960000000447574 for all testing

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Two separate message templates (penalty vs non-penalty) | Simpler than conditional templating, works well with textarea editing | ✓ Good — v1.0 shipped with two template types, TAs can edit independently |
| Preview modal shows all students, not just penalty | Changed from original "selective preview" to show all for transparency | ✓ Good — v1.0 preview shows all selected students with rendered comments |
| Test mode toggle + confirmation dialogs + production warning | Defense in depth — multiple safety layers prevent accidental live posting | ✓ Good — v1.0 has 3 safety layers (test mode, production banner, confirmation dialog) |
| Track posting history in SQLite | Prevents duplicate posts, provides audit trail | ✓ Good — v1.0 tracks all posts with status (posted/failed/skipped/dry_run) |
| Simple textarea editing with variable placeholders | Matches TA technical comfort level, no complex template syntax needed | ✓ Good — v1.0 uses str.format() with 5 allowed variables |
| Pre-populated default templates | TAs can use immediately, edit as needed, no blank slate | ✓ Good — v1.0 auto-populates penalty/non-penalty templates in init_db() |
| Dry run mode for testing | Safe testing without actual API calls before sandbox verification | ✓ Good — v1.0 dry run skips Canvas API calls, shows "DRY RUN" badge |
| SSE streaming for bulk posting | Real-time progress feedback during long operations | ✓ Good — v1.0 uses Server-Sent Events with "Posting X/Y comments..." |
| Edit-only template UI (no create/delete) | Templates always pre-populated, no recovery path from delete | ✓ Good — v1.0 Settings shows 2 textareas, no create/delete buttons |
| UNIQUE constraint for duplicate prevention | Database-level enforcement instead of application logic | ✓ Good — v1.0 uses UNIQUE(course_id, assignment_id, user_id, template_id) |
| refreshTrigger integer counter (not boolean) | Allows consumers to detect every sync, not just state changes | ✓ Good — v1.1 all dashboard pages re-fetch on every increment |
| Best-effort inner try/catch for sync-status fetch | Silent failure if backend unavailable — lastSyncedAt null default is safe | ✓ Good — v1.1 pre-populates timestamp on mount without blocking render |
| activeCourseId derived at App.jsx level, passed as prop | Consistent course context for all pages without duplicate state | ✓ Good — pattern extended in v1.1 for refreshTrigger/lastSyncedAt |
| Remove course-comparison guard from EnhancedTADashboard | refreshTrigger causes unconditional reload — simpler and correct | ✓ Good — v1.1 removes unnecessary optimization that blocked re-fetches |

---
*Last updated: 2026-03-01 after v1.1 milestone*
