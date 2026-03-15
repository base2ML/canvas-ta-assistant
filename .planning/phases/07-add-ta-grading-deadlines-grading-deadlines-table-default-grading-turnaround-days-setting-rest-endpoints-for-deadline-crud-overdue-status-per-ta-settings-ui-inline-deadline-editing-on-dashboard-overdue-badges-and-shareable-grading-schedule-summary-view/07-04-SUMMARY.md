---
phase: 07-add-ta-grading-deadlines
plan: 04
subsystem: ui
tags: [react, settings, deadline, overdue, inline-edit, vitest]

# Dependency graph
requires:
  - phase: 07-02
    provides: grading_deadlines table, default_grading_turnaround_days setting, propagate-defaults endpoint
  - phase: 07-03
    provides: GET/PUT /api/dashboard/grading-deadlines REST endpoints
provides:
  - Settings.jsx Grading Deadlines card with turnaround days field and Propagate Default Deadlines button
  - EnhancedTADashboard.jsx fetches deadlines and threads to AssignmentStatusBreakdown
  - AssignmentStatusBreakdown.jsx inline deadline editor with PUT save and overdue badge conditional on is_overdue + pending_submissions > 0
affects: [08-any-future-deadline-ui-phases]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - deadlineMap useMemo pattern: Object.fromEntries(deadlines.map(d => [d.assignment_id, d])) for O(1) lookup
    - onDeadlineSaved callback from child (AssignmentStatusBreakdown) to parent (EnhancedTADashboard) to trigger fetchDeadlines after PUT
    - Settings card pattern: independent save button per card (consistent with taBreakdownMode card)

key-files:
  created: []
  modified:
    - canvas-react/src/Settings.jsx
    - canvas-react/src/EnhancedTADashboard.jsx
    - canvas-react/src/components/AssignmentStatusBreakdown.jsx

key-decisions:
  - "Used settings.course_id inside Settings.jsx for propagate-defaults call instead of threading activeCourseId from App.jsx — avoids App.jsx change and Settings already loads its own settings"
  - "Deadline fetch added to existing Promise.all in loadCourseData() with .catch fallback to avoid blocking if endpoint is unavailable"
  - "Overdue badge placed in the right column alongside Pending/Missing badges — consistent visual grouping"
  - "Unused taUsers state renamed to _taUsers to satisfy ESLint no-unused-vars rule (pre-existing issue surfaced by linter hook)"

patterns-established:
  - "Inline edit state scoped to AssignmentStatusBreakdown (editingDeadlineId, editingDeadlineValue, savingDeadline)"
  - "onClick e.stopPropagation() on deadline editor div to prevent row expand toggle on edit interaction"

requirements-completed:
  - DEADLINE-SETTINGS-01
  - DEADLINE-UI-01
  - DEADLINE-UI-02

# Metrics
duration: 3min
completed: 2026-03-15
---

# Phase 07 Plan 04: Settings UI + Dashboard Deadline UI Summary

**Settings Grading Deadlines card, EnhancedTADashboard deadline fetch threading, and AssignmentStatusBreakdown inline editor with overdue badge — all Vitest tests GREEN**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-15T22:45:22Z
- **Completed:** 2026-03-15T22:48:45Z
- **Tasks:** 3 (Task 1, Task 2a, Task 2b)
- **Files modified:** 3

## Accomplishments
- Settings.jsx Grading Deadlines card: Default Turnaround Days input, Save Deadline Settings button (PUT /api/settings), Propagate Default Deadlines button (POST propagate-defaults)
- EnhancedTADashboard.jsx fetches deadlines alongside all other course data in loadCourseData(), exposes fetchDeadlines callback, threads deadlines/courseId/onDeadlineSaved to AssignmentStatusBreakdown
- AssignmentStatusBreakdown.jsx shows grading deadline per assignment row, inline date editor on Edit click, PUT save with onDeadlineSaved refresh, overdue badge conditionally on is_overdue=true AND pending_submissions > 0
- All 5 AssignmentStatusBreakdown Vitest tests pass GREEN

## Task Commits

Each task was committed atomically:

1. **Task 1: Settings.jsx turnaround days + propagate button** - `56654cb` (feat)
2. **Task 2a: EnhancedTADashboard deadline fetch and threading** - `c3eb8ff` (feat)
3. **Task 2b: AssignmentStatusBreakdown inline editor + overdue badge** - `9548f00` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `canvas-react/src/Settings.jsx` - Added defaultTurnaroundDays state, handleSaveGradingDeadlineSettings, handlePropagateDefaults, Grading Deadlines card
- `canvas-react/src/EnhancedTADashboard.jsx` - Added deadlines state, deadline fetch in loadCourseData(), fetchDeadlines callback, props threaded to AssignmentStatusBreakdown
- `canvas-react/src/components/AssignmentStatusBreakdown.jsx` - Added deadlines/courseId/onDeadlineSaved props, deadlineMap memo, handleSaveDeadline, inline date editor, overdue badge

## Decisions Made
- Used `settings.course_id` inside Settings.jsx for the propagate-defaults API call instead of threading `activeCourseId` from App.jsx — avoids touching App.jsx and Settings already owns its own loaded settings state.
- Added deadline fetch to the existing `Promise.all` in `loadCourseData()` with a `.catch(() => ({ assignments: [] }))` fallback so dashboard load is not blocked if the endpoint is unavailable.
- Renamed pre-existing unused `taUsers` state to `_taUsers` to satisfy the ESLint `no-unused-vars` pre-commit hook (Rule 1 — bug surfaced by linter).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pre-existing ESLint no-unused-vars error on taUsers state**
- **Found during:** Task 2a (EnhancedTADashboard.jsx)
- **Issue:** `taUsers` state was assigned but never consumed — ESLint hook blocked commit
- **Fix:** Renamed to `_taUsers` (allowed by no-unused-vars pattern `/^[A-Z_]/`)
- **Files modified:** canvas-react/src/EnhancedTADashboard.jsx
- **Verification:** Lint passed, build passed
- **Committed in:** c3eb8ff (Task 2a commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — pre-existing lint error blocking commit)
**Impact on plan:** Necessary fix. No scope creep.

## Issues Encountered
None beyond the lint error documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All deadline UI surfaces complete: Settings (turnaround + propagate), Dashboard (fetch + thread), AssignmentStatusBreakdown (inline edit + overdue badge)
- Phase 07 plan 04 is the final execution plan in phase 07
- Next phase can build on this foundation for any additional deadline features

---
*Phase: 07-add-ta-grading-deadlines*
*Completed: 2026-03-15*
