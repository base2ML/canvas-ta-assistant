# Roadmap: Canvas TA Dashboard

## Milestones

- ✅ **v1.0 Late Day Comment Posting** — Phases 1-3 (shipped 2026-02-21)
- ✅ **v1.1 Unified Data Refresh** — Phase 4 (shipped 2026-03-01)
- 📋 **v1.2** — TBD (planned)

## Phases

<details>
<summary>✅ v1.0 Late Day Comment Posting (Phases 1-3) — SHIPPED 2026-02-21</summary>

### Phase 1: Foundation
**Goal**: Safety infrastructure and template storage exist before posting capability can be built
**Depends on**: Nothing (first phase)
**Plans**: 2 plans

- [x] 01-01-PLAN.md — Database schema, template CRUD functions, history recording, default templates
- [x] 01-02-PLAN.md — Template API endpoints with validation, settings extensions (test mode, max late days)

### Phase 2: Posting Logic
**Goal**: Canvas API comment posting works with all safety mechanisms integrated
**Depends on**: Phase 1
**Plans**: 2 plans

- [x] 02-01-PLAN.md — Canvas posting function with retry, template rendering, preview endpoint, posting history endpoint
- [x] 02-02-PLAN.md — SSE bulk posting endpoint with progress streaming, rate limiting, duplicate prevention, dry run mode

### Phase 3: UI Integration
**Goal**: TAs can manage templates and post comments through dashboard UI
**Depends on**: Phase 2
**Plans**: 4 plans

- [x] 03-01-PLAN.md — Template management UI in Settings page
- [x] 03-02-PLAN.md — Comment posting panel, preview modal, confirmation dialog
- [x] 03-03-PLAN.md — Posting history table, progress streaming integration
- [x] 03-04-PLAN.md — Human verification of UI correctness and workflow UX

</details>

<details>
<summary>✅ v1.1 Unified Data Refresh (Phase 4) — SHIPPED 2026-03-01</summary>

### Phase 4: Unified Refresh
**Goal**: A single header button triggers Canvas sync and all dashboard pages reload their data automatically, with redundant controls removed
**Depends on**: Phase 3
**Plans**: 3 plans

- [x] 04-01-PLAN.md — App.jsx: refreshTrigger + lastSyncedAt state, header timestamp display, prop threading to dashboard routes
- [x] 04-02-PLAN.md — Settings.jsx: remove Sync Now and Save & Sync Now buttons and dead code
- [x] 04-03-PLAN.md — Dashboard pages: consume refreshTrigger in useEffect deps, remove per-page Refresh buttons and timestamps

</details>

### Phase 5: Fix late day penalty calculation — rewrite to semester-aware bank system with per-assignment caps, project deliverable exclusion via Canvas assignment groups, and 25% penalty rate

**Goal**: Late day tracking correctly implements the semester bank model: students draw from a shared 10-day bank (sorted chronologically by due date), capped per assignment, with 25%/day penalty on uncovered days, and project deliverables (Canvas assignment groups) excluded from bank eligibility
**Requirements**: LATE-DB-01, LATE-SYNC-01, LATE-API-GROUPS-01, LATE-ALGO-01, LATE-SETTINGS-01, LATE-TEMPLATE-01, LATE-POSTING-01, LATE-UI-01, LATE-UI-02
**Depends on:** Phase 4
**Plans:** 4/4 plans complete

Plans:
- [x] 05-01-PLAN.md — DB schema: assignment_groups table, assignment_group_id migration, upsert/clear functions
- [x] 05-02-PLAN.md — Canvas sync: fetch assignment groups, annotate assignments; add /api/canvas/assignment-groups endpoint
- [x] 05-03-PLAN.md — Backend algorithm: calculate_student_late_day_summary(), settings models, get_late_days_data(), preview/posting flow
- [x] 05-04-PLAN.md — Frontend: Settings Late Day Policy section + LateDaysTracking bank/penalty/Not Accepted display

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 2/2 | ✅ Complete | 2026-02-15 |
| 2. Posting Logic | v1.0 | 2/2 | ✅ Complete | 2026-02-21 |
| 3. UI Integration | v1.0 | 4/4 | ✅ Complete | 2026-02-21 |
| 4. Unified Refresh | v1.1 | 3/3 | ✅ Complete | 2026-03-01 |
| 5. Late Day Penalty Fix | 4/4 | Complete   | 2026-03-02 | 2026-03-01 |

### Phase 6: Grader identity tracking: sync grader_id/graded_at from Canvas, sync TA/instructor users, ta_breakdown_mode setting, update EnhancedTADashboard TA breakdown table

**Goal:** Actual grader data from Canvas (grader_id) is stored and optionally used in the TA grading breakdown table, giving TAs visibility into who actually graded each submission vs who was group-assigned
**Requirements**: GRADER-DB-01, GRADER-SYNC-01, GRADER-API-01, GRADER-SETTINGS-01, GRADER-UI-01, GRADER-SETTINGS-UI-01
**Depends on:** Phase 5
**Plans:** 4/4 plans complete

Plans:
- [ ] 06-01-PLAN.md — DB schema: ta_users table, submissions grader_id/graded_at migration, upsert_ta_users(), clear_refreshable_data update
- [ ] 06-02-PLAN.md — Canvas sync: fetch TA/instructor users, capture grader_id/graded_at on submissions, extend upsert_submissions()
- [ ] 06-03-PLAN.md — Backend API: get_submissions() LEFT JOIN ta_users for grader_name, settings models + endpoints for ta_breakdown_mode
- [ ] 06-04-PLAN.md — Frontend: App.jsx threads ta_breakdown_mode, Settings.jsx TA Dashboard card, EnhancedTADashboard mode branch

### Phase 7: Add TA grading deadlines: grading_deadlines table, default_grading_turnaround_days setting, REST endpoints for deadline CRUD, overdue status per TA, Settings UI, inline deadline editing on Dashboard, overdue badges, and shareable Grading Schedule Summary view

**Goal:** TAs can see and manage grading deadlines per assignment: a configurable default turnaround produces deadlines from due dates, inline editing allows per-assignment overrides, overdue badges flag stalled grading work, and a shareable /grading-schedule view provides a read-only snapshot of the grading schedule
**Requirements**: DEADLINE-DB-01, DEADLINE-DB-02, DEADLINE-SETTINGS-01, DEADLINE-API-01, DEADLINE-API-02, DEADLINE-API-03, DEADLINE-OVERDUE-01, DEADLINE-UI-01, DEADLINE-UI-02, DEADLINE-SUMMARY-01
**Depends on:** Phase 6
**Plans:** 4/5 plans executed

Plans:
- [ ] 07-01-PLAN.md — Wave 0: test scaffolds for all phase 7 requirements (pytest + Vitest, RED state)
- [ ] 07-02-PLAN.md — database.py: grading_deadlines table, upsert_grading_deadline, upsert_grading_deadline_if_not_override, get_grading_deadlines
- [ ] 07-03-PLAN.md — main.py: default_grading_turnaround_days settings extension, 3 deadline endpoints, _is_overdue() helper
- [ ] 07-04-PLAN.md — Frontend: Settings.jsx turnaround field + propagate button, EnhancedTADashboard deadline fetch, AssignmentStatusBreakdown inline editing + overdue badges
- [ ] 07-05-PLAN.md — Frontend: GradingScheduleSummary.jsx new component + /grading-schedule route in App.jsx

### Phase 8: Add grade distribution visualizations: grade-distribution endpoint with per-assignment stats and per-TA stats, Grade Analysis page with histograms and box plots, assignment selector, summary stats, and small-sample warnings

**Goal:** Grade distribution data from Canvas submissions is surfaced through a Grade Analysis page, giving TAs visibility into score distributions per assignment (histogram, box plot, summary stats) and per-TA grading patterns, with small-sample warnings when n < 5
**Requirements**: GRADE-DB-01, GRADE-API-01, GRADE-API-02, GRADE-STATS-01, GRADE-STATS-02, GRADE-HIST-01, GRADE-TA-01, GRADE-UI-01, GRADE-UI-02, GRADE-UI-03, GRADE-UI-04, GRADE-NAV-01
**Depends on:** Phase 7
**Plans:** 4 plans

Plans:
- [ ] 08-01-PLAN.md — Wave 0: test scaffolds (pytest + Vitest RED state) for all 12 requirements
- [ ] 08-02-PLAN.md — main.py: grade-distribution index + detail endpoints, Pydantic models, compute_histogram_bins helper
- [ ] 08-03-PLAN.md — Frontend SVG components: GradeHistogram.jsx + GradeBoxPlot.jsx (pure SVG, no recharts)
- [ ] 08-04-PLAN.md — Frontend page + wiring: GradeAnalysis.jsx, /grade-analysis route in App.jsx, Navigation.jsx link
