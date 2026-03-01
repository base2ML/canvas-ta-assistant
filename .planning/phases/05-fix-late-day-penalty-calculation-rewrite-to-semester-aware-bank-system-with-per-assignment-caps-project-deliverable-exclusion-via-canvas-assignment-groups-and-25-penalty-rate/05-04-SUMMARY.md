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
  - "Added dedicated Save Policy Settings button in Late Day Policy card (post-checkpoint fix) instead of relying on Course Configuration save button"
  - "assignment_groups table was missing from DB — applied init_db() migration to create it and add assignment_group_id column"

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

- **Duration:** ~15 min (including post-checkpoint debug and fixes)
- **Started:** 2026-03-01T17:45:25Z
- **Completed:** 2026-03-01 (post-checkpoint fix session)
- **Tasks:** 2 + post-checkpoint fixes
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

**2. [Post-checkpoint] Settings persistence UX fix and DB schema migration**
- **Found during:** Human verification checkpoint — user reported settings not saving, groups not appearing
- **Root cause A (UX):** The "Save Settings" button lives in the Course Configuration card (top of page). The Late Day Policy section is below Sync Status and Sync History. Users changed policy values and had no nearby save button.
- **Fix A:** Added dedicated `savePolicySettings()` function and "Save Policy Settings" button inside the Late Day Policy card with inline success/error feedback. Also added note directing user to reload Late Days Tracking after saving.
- **Root cause B (DB schema):** The `assignment_groups` table was missing from the SQLite database. `init_db()` adds it via `CREATE TABLE IF NOT EXISTS`, but it had not been run since the table was added in plan 05-01. The endpoint `/api/canvas/assignment-groups/{course_id}` was silently returning `{"groups": [], "count": 0}`.
- **Fix B:** Ran `init_db()` programmatically to create `assignment_groups` table and migrate `assignment_group_id` column into `assignments`. Database confirmed correct after migration. Groups will populate on next Canvas sync (no full re-sync required — existing sync flow calls `upsert_assignment_groups()`).
- **Root cause C (calculations):** Not a code bug — calculations update correctly once settings are saved (Fix A). The Late Days Tracking page requires a manual refresh after settings change, which is expected.
- **Files modified:** canvas-react/src/Settings.jsx (fix A); database migrated in-place (fix B)
- **Committed in:** 6d8ecec

---

**Total deviations:** 1 auto-fixed (lint) + 2 post-checkpoint fixes (UX + DB schema)
**Impact on plan:** UX fix necessary for correct operation; DB schema fix prerequisite for groups feature to work.

## Issues Encountered
- Post-checkpoint: assignment_groups table missing from DB required manual init_db() migration
- Post-checkpoint: Settings save UX confusion required dedicated Save button in Late Day Policy card

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 05 is complete — all four plans executed
- Human verification checkpoint pending (Task 3 checkpoint:human-verify)
- After verification, the full semester bank system is deployed end-to-end: algorithm (05-01/02), backend API (05-03), UI (05-04)

---
*Phase: 05-fix-late-day-penalty-calculation*
*Completed: 2026-03-01*
