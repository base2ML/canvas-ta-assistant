---
phase: quick/1-fix-course-selection-not-propagating-to-
plan: 01
subsystem: ui
tags: [react, fastapi, canvas-api, routing, state-management]

requires: []
provides:
  - Course propagation from Settings to all dashboard pages on navigation
  - Active course name and term displayed in app header
  - Term info surfaced in /api/canvas/courses and Settings Browse Courses dropdown
affects: [EnhancedTADashboard, LateDaysTracking, PeerReviewTracking, EnrollmentTracking, Settings]

tech-stack:
  added: []
  patterns:
    - "activeCourseId prop derived from courses[0] in App.jsx and threaded to all route elements"
    - "useEffect comparison guard (not in deps array) to detect course change and reset local selection"

key-files:
  created: []
  modified:
    - canvas-react/src/App.jsx
    - canvas-react/src/EnhancedTADashboard.jsx
    - canvas-react/src/PeerReviewTracking.jsx
    - canvas_sync.py
    - main.py
    - canvas-react/src/Settings.jsx

key-decisions:
  - "activeCourseId derived at App.jsx level from courses[0] and passed as prop — single source of truth"
  - "selectedCourse excluded from useEffect deps in EnhancedTADashboard and PeerReviewTracking — used only as comparison guard to prevent redundant resets, not as reactive input"
  - "course_term stored in SQLite settings as course_term_{course_id} key after each sync — enables /api/canvas/courses to return term without extra Canvas API calls"
  - "LateDaysTracking and EnrollmentTracking need no logic change — they derive currentCourse from courses[0] inline on every render and reset naturally when parent courses prop updates"

requirements-completed: []

duration: 3min
completed: 2026-02-21
---

# Quick Fix 1: Course Selection Not Propagating Summary

**Course change in Settings now propagates to all dashboard pages; header shows active course name and term; Browse Courses dropdown includes term info alongside course name**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-21T00:31:43Z
- **Completed:** 2026-02-21T00:34:49Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- All dashboard pages (EnhancedTADashboard, PeerReviewTracking) now reset to the newly configured course when navigating back from Settings — previously they retained stale course selection
- App header shows current course name and term beneath "Canvas TA Dashboard" title
- Settings "Browse Courses" dropdown shows "CourseName — Term (code)" format when term is available
- Backend stores and returns term info per course via SQLite settings

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix course propagation to all pages** - `b484771` (feat)
2. **Task 2: Add term info to course data and Settings dropdown** - `aba2f68` (feat)

**Plan metadata:** (see final commit below)

## Files Created/Modified
- `canvas-react/src/App.jsx` - Derives activeCourse/activeCourseId from courses[0], shows course name+term in header, passes activeCourseId to all route elements
- `canvas-react/src/EnhancedTADashboard.jsx` - Accepts activeCourseId prop; resets selectedCourse when activeCourseId changes, not just on first load
- `canvas-react/src/PeerReviewTracking.jsx` - Accepts activeCourseId prop; resets selectedCourse when activeCourseId changes
- `canvas_sync.py` - fetch_available_courses returns term field; sync_course_data extracts and stores course_term in settings
- `main.py` - /api/canvas/courses includes term field from settings per course
- `canvas-react/src/Settings.jsx` - Browse Courses option label includes term when available

## Decisions Made
- activeCourseId is derived at the App level from `courses[0]` and passed down as a prop rather than re-derived in each child — this creates a single authoritative source and ensures all pages respond to the same course change signal
- `selectedCourse` omitted from useEffect deps in the initialization/reset effects — adding it would create an infinite loop since the effect itself sets selectedCourse; the comparison guard is sufficient
- Term stored in SQLite settings after each sync so /api/canvas/courses can return it cheaply without extra Canvas API calls on every page load

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ESLint pre-commit hook enforces zero warnings**
- **Found during:** Task 1 commit attempt
- **Issue:** Pre-commit hook has `maxWarnings: 0`; react-hooks/exhaustive-deps warnings for intentional dep omissions caused commit failure
- **Fix:** Added `// eslint-disable-line react-hooks/exhaustive-deps` with explanatory comment on the relevant useEffect calls; also split long Python lines exceeding E501 for Ruff
- **Files modified:** canvas-react/src/EnhancedTADashboard.jsx, canvas-react/src/PeerReviewTracking.jsx, canvas_sync.py
- **Verification:** Both `npm run lint` and `uv run ruff check .` pass with zero warnings
- **Committed in:** b484771 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (blocking)
**Impact on plan:** Deviation was a pre-commit enforcement issue — the logic was correct but required suppression comments to satisfy the zero-warning policy. No scope creep.

## Issues Encountered
None beyond the pre-commit warning issue documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Course propagation bug is resolved; all dashboard pages will reflect Settings changes on next navigation
- Term info will appear in the header and Browse Courses dropdown after the next sync (requires Canvas API to return enrollment_term in course objects)
- No blockers for subsequent work

---
*Phase: quick/1-fix-course-selection-not-propagating-to-*
*Completed: 2026-02-21*
