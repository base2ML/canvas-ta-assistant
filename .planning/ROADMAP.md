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
**Plans:** 4 plans

Plans:
- [ ] 06-01-PLAN.md — DB schema: ta_users table, submissions grader_id/graded_at migration, upsert_ta_users(), clear_refreshable_data update
- [ ] 06-02-PLAN.md — Canvas sync: fetch TA/instructor users, capture grader_id/graded_at on submissions, extend upsert_submissions()
- [ ] 06-03-PLAN.md — Backend API: get_submissions() LEFT JOIN ta_users for grader_name, settings models + endpoints for ta_breakdown_mode
- [ ] 06-04-PLAN.md — Frontend: App.jsx threads ta_breakdown_mode, Settings.jsx TA Dashboard card, EnhancedTADashboard mode branch
