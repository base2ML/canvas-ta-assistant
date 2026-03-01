---
phase: 05-fix-late-day-penalty-calculation
plan: 04
subsystem: ui
tags: [react, tailwind, settings, late-days, bank-system, canvas-assignment-groups]

# Dependency graph
requires:
  - phase: 05-03
    provides: semester bank algorithm, new API response shape with bank_days_used/penalty_days/not_accepted per assignment, bank_remaining/total_bank per student
provides:
  - Settings.jsx Late Day Policy section with three integer inputs and assignment group checkbox list
  - LateDaysTracking.jsx bank/penalty cell rendering with NA badge for project deliverables
  - Color legend below late days table
affects: [late-days-tracking, settings, comment-posting]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Policy settings loaded from GET /api/settings and saved via PUT /api/settings with four new fields"
    - "Assignment groups fetched via useCallback/useEffect from /api/canvas/assignment-groups/{course_id}"
    - "Entry-object pattern for assignment cells: entry.bank_days_used, entry.penalty_days, entry.not_accepted"

key-files:
  created: []
  modified:
    - canvas-react/src/Settings.jsx
    - canvas-react/src/LateDaysTracking.jsx

key-decisions:
  - "Placed Late Day Policy section between Course Configuration and Comment Templates for logical flow"
  - "Stacked green/red split cell for mixed bank+penalty days (bankDays > 0 and penaltyDays > 0)"
  - "Removed unused getLateDaysColor helper (Rule 1 auto-fix) since entry-object cells replaced flat-number cells"

patterns-established:
  - "Assignment cell rendering: check entry object fields (not raw number) for bank/penalty/not_accepted state"
  - "Sort for assignment_ columns uses entry.days_late (not entry itself) for numeric comparison"

requirements-completed:
  - LATE-UI-01
  - LATE-UI-02

# Metrics
duration: 2min
completed: 2026-03-01
---

# Phase 05 Plan 04: Late Day Policy UI and Bank/Penalty Cell Rendering Summary

**Settings Late Day Policy section (4 configurable fields + group checkbox list) and LateDaysTracking updated with NA badge, green/red bank/penalty circles, and bank_remaining per student**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-01T17:45:25Z
- **Completed:** 2026-03-01T17:47:25Z
- **Tasks:** 2 (plus checkpoint awaiting human verification)
- **Files modified:** 2

## Accomplishments
- Added Late Day Policy section to Settings.jsx with three integer inputs (total bank, penalty rate %, per-assignment cap) and assignment group checkbox list with load from /api/canvas/assignment-groups/{course_id}
- Updated comment variable reference list to include {bank_days_used}, {bank_remaining}, {total_bank}
- Rewrote LateDaysTracking.jsx assignment cell rendering to handle entry objects with bank_days_used, penalty_days, not_accepted, days_late fields
- NA badge rendered in red for not_accepted (project deliverable) assignments
- Green circles for bank-covered late days, red circles for penalty days, stacked split for mixed
- bank_remaining/total_bank shown below student total column
- Color legend added below the table

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Late Day Policy section to Settings.jsx** - `f20236e` (feat)
2. **Task 2: Update LateDaysTracking.jsx for bank/penalty distinction and Not Accepted badge** - `d48ee83` (feat)

## Files Created/Modified
- `canvas-react/src/Settings.jsx` - Added policySettings state, loadAssignmentGroups callback, Late Day Policy UI section, updated variable list
- `canvas-react/src/LateDaysTracking.jsx` - Replaced flat lateDays reads with entry object, added NA/green/red/split cell rendering, bank_remaining display, color legend

## Decisions Made
- Placed Late Day Policy section between Course Configuration and Comment Templates for logical grouping
- Used stacked green-over-red split indicator for mixed bank+penalty cases (bankDays > 0 and penaltyDays > 0)
- Sort for assignment_ columns uses `entry.days_late` to maintain numeric sort behavior with new object shape

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused getLateDaysColor helper**
- **Found during:** Task 2 (ESLint verification)
- **Issue:** getLateDaysColor was only used by the old flat-number cell rendering. After replacing all cells with entry-object logic, ESLint reported it as unused, causing a lint error.
- **Fix:** Removed the function entirely — it was no longer needed since all coloring is now inline in the cell renderers.
- **Files modified:** canvas-react/src/LateDaysTracking.jsx
- **Verification:** ESLint passes, build succeeds
- **Committed in:** d48ee83 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug/lint)
**Impact on plan:** Fix necessary for ESLint to pass. No scope creep.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 05 is complete — all four plans executed
- Human verification checkpoint pending (Task 3 checkpoint:human-verify)
- After verification, the full semester bank system is deployed end-to-end: algorithm (05-01/02), backend API (05-03), UI (05-04)

---
*Phase: 05-fix-late-day-penalty-calculation*
*Completed: 2026-03-01*
