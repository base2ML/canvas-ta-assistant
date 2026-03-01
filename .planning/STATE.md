---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Late Day Bank System
status: in_progress
last_updated: "2026-03-01T17:26:49Z"
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 4
  completed_plans: 1
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-01)

**Core value:** Safely and efficiently post accurate late day feedback to student submissions, preventing manual errors and saving TA time while ensuring students receive timely, consistent communication about their late day status.
**Current focus:** Phase 05 — Fix late day penalty calculation (semester-aware bank system)

## Current Position

Phase: 05 — fix-late-day-penalty-calculation (Plan 2 of 4)
Status: In progress — 05-01 complete, 05-02 through 05-04 remaining
Last activity: 2026-03-01 — 05-01-PLAN.md complete (SQLite schema for assignment_groups)

Progress: [███░░░░░░░] 25% (1/4 plans complete in phase 05)

## Performance Metrics

**Velocity:**
- Total plans completed: 9 (v1.0 phases 1-3, plus 5 quick tasks)
- Average duration: ~2 min
- Total execution time: ~0.3 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 2 | 7 min | 4 min |
| 02 | 2 | 3 min | 2 min |
| 03 | 4 | ~10 min | ~2.5 min |

*Updated after each plan completion*
| Phase 04-unified-refresh P02 | 5 | 1 tasks | 1 files |
| Phase 04-unified-refresh P03 | 14 | 2 tasks | 3 files |
| Phase 05 P01 (05-01) | 3 min | 2 tasks | 3 files |

## Accumulated Context

### Decisions

All decisions from v1.0 and v1.1 archived in PROJECT.md Key Decisions table.

**Phase 05 decisions (in progress):**
- Used try/except sqlite3.OperationalError migration pattern (not contextlib.suppress) for assignment_group_id column, consistent with enrollment_status migration
- Placed assignment_groups table CREATE immediately after assignments table in init_db() for logical organization
- Added conftest.py to tests/ (new directory) to support pytest backend module imports

### Pending Todos

6 todos captured (2026-03-01):
1. **Fix late day penalty calculation logic** (bug — incorrect penalty math)
2. Add grader identity tracking (foundation — build first)
3. Add TA grading deadlines (depends on #2)
4. Add grade distribution visualizations (depends on #2)
5. Add student at-risk alerts
6. Add exportable reports CSV and PDF (build last)

### Roadmap Evolution

- Phase 5 added: Fix late day penalty calculation — rewrite to semester-aware bank system with per-assignment caps, project deliverable exclusion via Canvas assignment groups, and 25% penalty rate

### Blockers/Concerns

None yet.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 1 | Fix course selection not propagating to dashboard pages and add course name with term to header and settings | 2026-02-21 | 10dc439 | [1-fix-course-selection-not-propagating-to-](./quick/1-fix-course-selection-not-propagating-to-/) |
| 2 | Fix term information not appearing in Browse Courses dropdown and course header | 2026-02-22 | 01660eb | [2-research-the-canvas-api-and-determine-wh](./quick/2-research-the-canvas-api-and-determine-wh/) |
| 3 | Fix Last Updated timestamp to show actual Canvas sync time instead of browser clock | 2026-02-22 | 3736c35 | [3-the-last-updated-time-on-the-main-dashbo](./quick/3-the-last-updated-time-on-the-main-dashbo/) |
| 4 | Filter enrollment timeline to changes-only and add SVG enrollment line chart | 2026-02-22 | 48ca026 | [4-filter-enrollment-sync-history-to-only-s](./quick/4-filter-enrollment-sync-history-to-only-s/) |
| 5 | Remove duplicate course info subtitle from Late Days Tracking page header | 2026-03-01 | 9aaa308 | [5-remove-duplicate-course-info-subtitle-fr](./quick/5-remove-duplicate-course-info-subtitle-fr/) |

## Session Continuity

Last session: 2026-03-01
Stopped at: Completed 05-01-PLAN.md (SQLite schema for assignment_groups table and upsert functions)
Resume file: None
