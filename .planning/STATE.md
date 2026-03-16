---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: verifying
stopped_at: Completed 08-03-PLAN.md
last_updated: "2026-03-16T03:33:20.530Z"
last_activity: "2026-03-03 — Quick-7: fix Settings page race condition where eligible groups checkbox reverted to all-checked on refresh"
progress:
  total_phases: 8
  completed_phases: 3
  total_plans: 17
  completed_plans: 16
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-01)

**Core value:** Safely and efficiently post accurate late day feedback to student submissions, preventing manual errors and saving TA time while ensuring students receive timely, consistent communication about their late day status.
**Current focus:** Phase 05 — Fix late day penalty calculation (semester-aware bank system)

## Current Position

Phase: 05 — fix-late-day-penalty-calculation (Plan 4 of 4)
Status: Complete — all 4 plans executed; checkpoint:human-verify APPROVED; SQL SELECT bug fixed (80dc14a)
Last activity: 2026-03-03 — Quick-7: fix Settings page race condition where eligible groups checkbox reverted to all-checked on refresh

Progress: [██████████] 100% (4/4 plans complete in phase 05)

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
| Phase 05 P02 | 3 | 2 tasks | 5 files |
| Phase 05 P03 | 7 min | 3 tasks | 4 files |
| Phase 05 P04 | 2 min | 2 tasks | 2 files |
| Phase 06 P01 | 3 | 2 tasks | 2 files |
| Phase 06 P03 | 5 | 2 tasks | 3 files |
| Phase 06 P02 | 4 min | 2 tasks | 3 files |
| Phase 06 P04 | 15 | 5 tasks | 7 files |
| Phase 07 P01 | 6 | 2 tasks | 5 files |
| Phase 07 P02 | 5 | 1 tasks | 2 files |
| Phase 07 P03 | 8 | 2 tasks | 1 files |
| Phase 07 P04 | 3 | 3 tasks | 3 files |
| Phase 08 P01 | 4 | 2 tasks | 4 files |
| Phase 08 P02 | 4 | 2 tasks | 1 files |
| Phase 08 P03 | 4 | 2 tasks | 2 files |

## Accumulated Context

### Decisions

All decisions from v1.0 and v1.1 archived in PROJECT.md Key Decisions table.

**Phase 05 decisions (in progress):**
- Used try/except sqlite3.OperationalError migration pattern (not contextlib.suppress) for assignment_group_id column, consistent with enrollment_status migration
- Placed assignment_groups table CREATE immediately after assignments table in init_db() for logical organization
- Added conftest.py to tests/ (new directory) to support pytest backend module imports
- [Phase 05]: Fetched Canvas assignment groups between assignments and users in sync_course_data(), called upsert_assignment_groups() before upsert_assignments() inside transaction
- [Phase 05]: Added get_assignment_groups() to database.py ordering by position ASC, name ASC; endpoint returns {groups, count} with HTTP 500 on error
- [Phase 05-03]: Preserved old calculate_late_days_for_user() without deleting; pre-compute bank_summaries before SSE generator for closure capture
- [Phase 05-03]: Empty late_day_eligible_group_ids means all assignments eligible (backward compat); per_assignment_cap falls back to max_late_days_per_assignment if not in DB
- [Phase 05-04]: Placed Late Day Policy section between Course Configuration and Comment Templates; stacked green/red split cell for mixed bank+penalty cases
- [Phase 05-04]: Sort for assignment_ columns uses entry.days_late (not entry object) for numeric comparison
- [Phase 05]: Added dedicated Save Policy Settings button in Late Day Policy card to fix settings persistence UX confusion where users didn't realize Course Configuration save button applied to policy fields
- [Phase 05]: DB schema migration: assignment_groups table and assignment_group_id column were missing from local DB — applied init_db() to migrate; groups will populate on next sync
- [Phase 05-04]: get_assignments() SELECT omitted assignment_group_id — calculate_student_late_day_summary() received None and marked all assignments not_accepted; fixed in 80dc14a (all 70 tests pass)
- [Phase 06]: Placed ta_users table and migrations after submissions table in init_db() for logical proximity
- [Phase 06]: [06-01]: Used try/except sqlite3.OperationalError pattern for grader_id/graded_at migrations, consistent with assignment_group_id migration
- [Phase 06]: [06-01]: upsert_ta_users() uses optional conn parameter + inner _upsert() pattern identical to upsert_users() for transaction-aware usage
- [Phase 06]: [06-01]: clear_refreshable_data() clears ta_users per course_id since TA roster may change between syncs
- [Phase 06]: [06-03]: upsert_submissions() extended to persist grader_id/graded_at; asyncio.run() used for async httpx tests; ta_breakdown_mode defaults to 'group' at model level and in get_settings()
- [Phase 06]: [06-02]: Two-pass TA fetch with seen_ids: ta enrollment first, teacher second; upsert_submissions extended to 11 columns with grader_id/graded_at
- [Phase 06]: match grader_id against ta_users.id for actual-mode count (not grader_name); fallback to name string match; new /api/canvas/ta-users endpoint
- [Phase 07]: Wave 0: test scaffolds written before implementation — all 23 pytest + 8 Vitest tests RED by design
- [Phase 07]: [07-01]: test_07_01_schema.py uses DATA_DIR monkeypatch; test_07_02_api.py uses DB_PATH monkeypatch (consistent with phase 06 patterns)
- [Phase 07]: [07-01]: GradingScheduleSummary.test.jsx excludes 'renders TA group names' test — GradingDeadlineItem has no ta_groups field
- [Phase 07]: grading_deadlines table placed after ta_users block in init_db(); clear_refreshable_data() does NOT touch grading_deadlines (overrides survive sync); upsert_grading_deadline_if_not_override uses CASE WHEN SQL in ON CONFLICT DO UPDATE for atomic override-safe upsert
- [Phase 07]: is_overdue() named without underscore prefix so tests can import directly from main module
- [Phase 07]: GradingDeadlineItem uses deadline_at field name to match test_07_02_api.py assertions
- [Phase 07]: [07-03]: raise from e in update_grading_deadline except clause to satisfy Ruff B904
- [Phase 07]: [07-04]: Used settings.course_id inside Settings.jsx for propagate-defaults call; deadline fetch in Promise.all with fallback; renamed taUsers to _taUsers for ESLint compliance
- [Phase 08]: pytest file uses DB_PATH monkeypatch (not DATA_DIR) — tests API layer, consistent with test_07_02_api.py
- [Phase 08]: GradeAnalysis.test.jsx uses _testData prop pattern for small-sample test to avoid fetch mock complexity
- [Phase 08]: Used local import statistics as _stats inside endpoint body to avoid ruff F811 clash with Pydantic field names (mean, median, stdev)
- [Phase 08]: [08-02]: statistics.quantiles(scores, n=4) returns [Q1, Q2, Q3]; q1=qs[0], q3=qs[2]; guard stdev/quantiles with n>=2 check
- [Phase 08]: [08-03]: Used pointsPossible in aria-label on GradeHistogram SVG to satisfy ESLint no-unused-vars while keeping prop in interface for future axis labeling
- [Phase 08]: [08-03]: GradeBoxPlot clamped scale Math.min(1, v/pointsPossible) prevents SVG elements outside viewBox for floating point edge cases

### Pending Todos

7 todos captured:
1. **Fix late day penalty calculation logic** (bug — incorrect penalty math) ✓ Done (Phase 05)
2. Add grader identity tracking (foundation — build first)
3. Add TA grading deadlines (depends on #2)
4. Add grade distribution visualizations (depends on #2)
5. Add student at-risk alerts
6. Add exportable reports CSV and PDF (build last)
7. Add penalty summary view by assignment on Late Days Tracking page (2026-03-07) — filtered table of students with penalties on a specific assignment, ordered by grading TA, for screenshot sharing

### Roadmap Evolution

- Phase 5 added: Fix late day penalty calculation — rewrite to semester-aware bank system with per-assignment caps, project deliverable exclusion via Canvas assignment groups, and 25% penalty rate
- Phase 6 added: Grader identity tracking: sync grader_id/graded_at from Canvas, sync TA/instructor users, ta_breakdown_mode setting, update EnhancedTADashboard TA breakdown table
- Phase 7 added: Add TA grading deadlines: grading_deadlines table, default_grading_turnaround_days setting, REST endpoints for deadline CRUD, overdue status per TA, Settings UI, inline deadline editing on Dashboard, overdue badges, and shareable Grading Schedule Summary view
- Phase 8 added: Add grade distribution visualizations: grade-distribution endpoint with per-assignment stats and per-TA stats, Grade Analysis page with histograms and box plots, assignment selector, summary stats, and small-sample warnings

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
| 6 | Fix assignment group eligibility not applying to Late Days calculations after settings change | 2026-03-03 | f3702ec | [6-fix-assignment-group-eligibility-not-app](./quick/6-fix-assignment-group-eligibility-not-app/) |
| 7 | Fix Settings page Late Day Eligible Assignment Groups race condition causing all-groups revert on refresh | 2026-03-03 | aa0ae6b | [7-fix-settings-page-late-day-eligible-assi](./quick/7-fix-settings-page-late-day-eligible-assi/) |
| 8 | Fix bank_days_used to cumulative semantics, remove alias template variables (days_remaining, max_late_days), update default templates and Settings UI | 2026-03-06 | 1812a4f | [8-review-the-calculations-for-the-differen](./quick/8-review-the-calculations-for-the-differen/) |

## Session Continuity

Last session: 2026-03-16T03:33:20.528Z
Stopped at: Completed 08-03-PLAN.md
Resume file: None
