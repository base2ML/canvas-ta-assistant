# Roadmap: Canvas TA Dashboard

## Milestones

- [x] **v1.0 Late Day Comment Posting** - Phases 1-3 (shipped 2026-02-21)
- [ ] **v1.1 Unified Data Refresh** - Phase 4 (in progress)

## Phases

<details>
<summary>v1.0 Late Day Comment Posting (Phases 1-3) - SHIPPED 2026-02-21</summary>

### Phase 1: Foundation
**Goal**: Safety infrastructure and template storage exist before posting capability can be built
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-09, TMPL-01, TMPL-02, TMPL-04, TMPL-05, SAFE-01, SAFE-02, SAFE-05, CONF-01, CONF-02, CONF-04
**Success Criteria** (what must be TRUE):
  1. Database tables exist for comment templates and posting history with proper schema
  2. Template CRUD operations work (create, read, update, delete templates via Python functions)
  3. Default templates are pre-populated in database on first run with penalty/non-penalty messages
  4. Test mode toggle can be enabled/disabled in Settings to prevent accidental production posting
  5. Duplicate detection infrastructure exists (posting history table with unique constraints)
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — Database schema, template CRUD functions, history recording, default templates
- [x] 01-02-PLAN.md — Template API endpoints with validation, settings extensions (test mode, max late days)

### Phase 2: Posting Logic
**Goal**: Canvas API comment posting works with all safety mechanisms integrated
**Depends on**: Phase 1
**Requirements**: INFRA-05, INFRA-06, INFRA-07, INFRA-08, TMPL-03, POST-01, POST-02, POST-05, POST-06, SAFE-03, SAFE-06
**Success Criteria** (what must be TRUE):
  1. Comments can be posted to Canvas submissions via canvasapi library with retry logic
  2. Template variables ({days_late}, {days_remaining}, etc.) are correctly substituted with student data
  3. Preview endpoint renders templates without posting to Canvas
  4. Bulk posting endpoint processes multiple students sequentially with rate limiting (0.5-1s delays)
  5. Duplicate comments are prevented via posting history check before each post
  6. Posting errors are handled gracefully (exponential backoff on 429, detailed failure reports)
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Canvas posting function with retry, template rendering, preview endpoint, posting history endpoint
- [x] 02-02-PLAN.md — SSE bulk posting endpoint with progress streaming, rate limiting, duplicate prevention, dry run mode

### Phase 3: UI Integration
**Goal**: TAs can manage templates and post comments through dashboard UI
**Depends on**: Phase 2
**Requirements**: TMPL-06, POST-03, POST-04, POST-07, POST-08, POST-09, POST-10, SAFE-04, CONF-03
**Success Criteria** (what must be TRUE):
  1. Settings page displays template management UI with two textarea fields for penalty/non-penalty templates
  2. LateDaysTracking page shows comment posting panel with student selection and preview workflow
  3. Preview modal displays rendered comments before posting for penalty cases
  4. Confirmation dialog shows course name, assignment name, and student count before posting
  5. Progress indicator appears during bulk posting showing "Posting X/Y comments..."
  6. Posting history table displays previously posted comments with timestamps and status
  7. Individual comments can be manually edited before posting for edge cases
**Plans**: 4 plans

Plans:
- [x] 03-01-PLAN.md — Template management UI in Settings page
- [x] 03-02-PLAN.md — Comment posting panel, preview modal, confirmation dialog
- [x] 03-03-PLAN.md — Posting history table, progress streaming integration
- [x] 03-04-PLAN.md — Human verification of UI correctness and workflow UX

</details>

### v1.1 Unified Data Refresh (In Progress)

**Milestone Goal:** Replace scattered, inconsistent refresh/sync controls with a single header-level "Refresh Data" button that propagates data reload to all pages automatically.

#### Phase 4: Unified Refresh
**Goal**: A single header button triggers Canvas sync and all dashboard pages reload their data automatically, with redundant controls removed
**Depends on**: Phase 3
**Requirements**: SYNC-01, SYNC-02, SYNC-03, CLEAN-01, CLEAN-02, CLEAN-03, CLEAN-04, CLEAN-05
**Success Criteria** (what must be TRUE):
  1. Clicking "Refresh Data" in the header triggers Canvas sync and shows a loading state for the duration
  2. After sync completes, all open dashboard pages (EnhancedTADashboard, LateDaysTracking, EnrollmentTracking) reload their data without any additional user action
  3. The header displays the last synced timestamp after every sync, visible from any page
  4. The Settings page has only a "Save Settings" button — no sync trigger
  5. No per-page Refresh buttons or page-level sync timestamps appear anywhere in the dashboard
**Plans**: 3 plans

Plans:
- [ ] 04-01-PLAN.md — App.jsx: refreshTrigger + lastSyncedAt state, header timestamp display, prop threading to dashboard routes
- [ ] 04-02-PLAN.md — Settings.jsx: remove Sync Now and Save & Sync Now buttons and dead code
- [ ] 04-03-PLAN.md — Dashboard pages: consume refreshTrigger in useEffect deps, remove per-page Refresh buttons and timestamps

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 2/2 | Complete | 2026-02-15 |
| 2. Posting Logic | v1.0 | 2/2 | Complete | 2026-02-21 |
| 3. UI Integration | v1.0 | 4/4 | Complete | 2026-02-21 |
| 4. Unified Refresh | 1/3 | In Progress|  | - |
