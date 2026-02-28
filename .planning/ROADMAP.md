# Roadmap: Canvas TA Dashboard - Late Day Comment Posting

## Overview

This roadmap delivers automated late day comment posting to Canvas submissions, replacing manual Jupyter notebook workflows. The journey progresses through three phases: first establishing safety infrastructure and template storage (Phase 1), then building Canvas API posting logic with rate limiting and error handling (Phase 2), and finally integrating the workflow into React UI components (Phase 3). Each phase delivers complete, verifiable capabilities that can be tested independently.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Database schema, template CRUD, and safety controls
- [ ] **Phase 2: Posting Logic** - Canvas API integration, variable substitution, and bulk posting
- [ ] **Phase 3: UI Integration** - React components for template management and posting workflow

## Phase Details

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
**Plans:** 2 plans

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
**Plans:** 2 plans

Plans:
- [ ] 02-01-PLAN.md — Canvas posting function with retry, template rendering, preview endpoint, posting history endpoint
- [ ] 02-02-PLAN.md — SSE bulk posting endpoint with progress streaming, rate limiting, duplicate prevention, dry run mode

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
**Plans**: TBD

Plans:
- TBD (plans created during /gsd:plan-phase)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 2/2 | ✓ Complete | 2026-02-15 |
| 2. Posting Logic | 0/2 | Not started | - |
| 3. UI Integration | 0/? | Not started | - |
