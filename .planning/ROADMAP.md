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

### 📋 v1.2 (Planned)

*Next milestone — TBD after `/gsd:new-milestone`*

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 2/2 | ✅ Complete | 2026-02-15 |
| 2. Posting Logic | v1.0 | 2/2 | ✅ Complete | 2026-02-21 |
| 3. UI Integration | v1.0 | 4/4 | ✅ Complete | 2026-02-21 |
| 4. Unified Refresh | v1.1 | 3/3 | ✅ Complete | 2026-03-01 |
