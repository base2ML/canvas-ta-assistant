---
phase: quick/1-fix-course-selection-not-propagating-to-
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - canvas-react/src/App.jsx
  - canvas-react/src/EnhancedTADashboard.jsx
  - canvas-react/src/LateDaysTracking.jsx
  - canvas-react/src/PeerReviewTracking.jsx
  - canvas-react/src/EnrollmentTracking.jsx
  - canvas_sync.py
  - canvas-react/src/Settings.jsx
autonomous: true
requirements: []

must_haves:
  truths:
    - "Navigating away from Settings after changing course causes all dashboard pages to display data for the newly selected course"
    - "The header shows the current course name and term (e.g. 'CS 161 — Spring 2025')"
    - "The Settings 'Browse Courses' dropdown shows course name and term for each option"
  artifacts:
    - path: "canvas-react/src/App.jsx"
      provides: "activeCourseId and activeCourse derived from courses[0], passed to header and all dashboard routes"
    - path: "canvas_sync.py"
      provides: "fetch_available_courses returns term_name field alongside id, name, code"
    - path: "canvas-react/src/Settings.jsx"
      provides: "Browse Courses dropdown option label includes term_name when available"
  key_links:
    - from: "canvas-react/src/App.jsx"
      to: "EnhancedTADashboard, LateDaysTracking, PeerReviewTracking, EnrollmentTracking"
      via: "activeCourseId prop"
      pattern: "activeCourseId"
    - from: "canvas-react/src/EnhancedTADashboard.jsx"
      to: "course data APIs"
      via: "useEffect on activeCourseId change"
      pattern: "activeCourseId"
---

<objective>
Fix course selection not propagating to dashboard pages, show current course name+term in the app header, and add term info to the Settings "Browse Courses" dropdown.

Purpose: When a TA changes the configured course in Settings, every dashboard page should immediately reflect the new course on next visit — not continue showing stale data from the previous course.
Output: Correct course shown across all pages, header shows "CourseName — Term", Browse Courses dropdown shows term.
</objective>

<execution_context>
@/Users/mapajr/.claude/get-shit-done/workflows/execute-plan.md
@/Users/mapajr/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@canvas-react/src/App.jsx
@canvas-react/src/EnhancedTADashboard.jsx
@canvas-react/src/LateDaysTracking.jsx
@canvas-react/src/PeerReviewTracking.jsx
@canvas-react/src/EnrollmentTracking.jsx
@canvas-react/src/Settings.jsx
@canvas_sync.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix course propagation — pass activeCourseId to all pages and reset local selected state</name>
  <files>
    canvas-react/src/App.jsx
    canvas-react/src/EnhancedTADashboard.jsx
    canvas-react/src/LateDaysTracking.jsx
    canvas-react/src/PeerReviewTracking.jsx
    canvas-react/src/EnrollmentTracking.jsx
  </files>
  <action>
**Root cause:** Each dashboard page derives its active course from `courses[0]` with a `!selectedCourse` guard, so once selected it never resets when `courses` changes to a new course after Settings navigation.

**Fix in `App.jsx`:**
1. Derive `activeCourse` and `activeCourseId` from `courses[0]` (or null if empty):
   ```js
   const activeCourse = courses.length > 0 ? courses[0] : null;
   const activeCourseId = activeCourse?.id ?? null;
   ```
2. Pass `activeCourseId` as a prop to all route elements (EnhancedTADashboard, LateDaysTracking, PeerReviewTracking, EnrollmentTracking).
3. In the header `<h1>`, show the active course name and term:
   - Change `<h1 className="text-xl font-bold text-gray-900">Canvas TA Dashboard</h1>` to render:
     ```jsx
     <div>
       <h1 className="text-xl font-bold text-gray-900">Canvas TA Dashboard</h1>
       {activeCourse && (
         <p className="text-sm text-gray-500 leading-tight">
           {activeCourse.name}{activeCourse.term ? ` — ${activeCourse.term}` : ''}
         </p>
       )}
     </div>
     ```
   - The `term` field will be populated once `/api/canvas/courses` returns it (Task 2 adds it).

**Fix in `EnhancedTADashboard.jsx`:**
- Accept `activeCourseId` prop.
- Change the initialization `useEffect` guard from `!selectedCourse` to also fire when `activeCourseId` differs from `selectedCourse?.id`:
  ```js
  useEffect(() => {
    if (courses && courses.length > 0) {
      const target = courses.find(c => String(c.id) === String(activeCourseId)) || courses[0];
      if (!selectedCourse || String(selectedCourse.id) !== String(target.id)) {
        setSelectedCourse(target);
        loadCourseData(target.id);
      }
    }
  }, [courses, activeCourseId, loadCourseData]);
  ```
  Remove the old `courses, selectedCourse, loadCourseData` effect that had the `!selectedCourse` guard — replace entirely with the above.

**Fix in `LateDaysTracking.jsx`:**
- Accept `activeCourseId` prop.
- `currentCourse` is derived inline as `courses[0]`. This is fine as long as `courses` reflects the right course after nav away from Settings (which it does, since App.jsx reloads courses). No logic change needed here — the existing `courses[0]` derivation already works correctly once `courses` prop is updated. Keep as-is.

**Fix in `PeerReviewTracking.jsx`:**
- Accept `activeCourseId` prop.
- The initialization guard is:
  ```js
  if (courses && courses.length > 0 && !selectedCourse) {
    setSelectedCourse(courses[0].id);
  }
  ```
  Change to also reset when `activeCourseId` changes:
  ```js
  useEffect(() => {
    if (courses && courses.length > 0) {
      const targetId = activeCourseId ?? courses[0].id;
      if (!selectedCourse || String(selectedCourse) !== String(targetId)) {
        setSelectedCourse(String(targetId));
      }
    }
  }, [courses, activeCourseId]);
  ```

**Fix in `EnrollmentTracking.jsx`:**
- `currentCourse = courses[0]` inline — same pattern as LateDaysTracking. No change needed; it re-derives on each render from the courses prop.
  </action>
  <verify>
    Run `npm run lint` in `canvas-react/` — must pass with no errors.
    Manual flow: Start app, go to Settings, change course ID to a different course and click "Save &amp; Sync Now", navigate to Dashboard — data shown should be for the new course, not the old one.
    Header should show course name beneath "Canvas TA Dashboard".
  </verify>
  <done>
    All dashboard pages (EnhancedTADashboard, LateDaysTracking, PeerReviewTracking, EnrollmentTracking) reset to the newly configured course when navigating back from Settings.
    The app header shows the current course name (and term when available) beneath the main title.
  </done>
</task>

<task type="auto">
  <name>Task 2: Add term info to fetch_available_courses and surface it in the Settings dropdown and /api/canvas/courses</name>
  <files>
    canvas_sync.py
    canvas-react/src/Settings.jsx
    main.py
  </files>
  <action>
**In `canvas_sync.py` — `fetch_available_courses`:**
Add `term` field to each course dict by reading `enrollment_term` attribute from the Canvas course object:
```python
courses.append({
    "id": course_id,
    "name": getattr(course, "name", f"Course {course.id}"),
    "code": getattr(course, "course_code", ""),
    "term": getattr(getattr(course, "enrollment_term", None), "name", None) or getattr(course, "term_name", None),
})
```
The `canvasapi` library exposes the enrollment term as a nested object with a `name` attribute when the Canvas API returns it. Use `getattr(..., None)` to gracefully handle courses where term is absent (returns `None` — not an error).

**In `main.py` — `get_courses` (`/api/canvas/courses`):**
The courses returned here come from `db.get_courses()` (just course IDs), and then the name is fetched from settings. Currently no term is stored in settings. Add a `term` field populated from `db.get_setting(f"course_term_{course_id}")` (may be None initially — that is fine):
```python
course_data.append({
    "id": course_id,
    "name": course_name or f"Course {course_id}",
    "term": db.get_setting(f"course_term_{course_id}"),
    "last_updated": last_sync.get("completed_at") if last_sync else None,
})
```
Also, in `sync_course_data` result processing (the `trigger_sync` endpoint, around line 600), after syncing, store the term name in settings so subsequent `/api/canvas/courses` calls can return it. In `canvas_sync.py`'s `sync_course_data`, ensure the returned dict includes `course_term`. Then in `main.py`'s `trigger_sync`, after a successful sync:
```python
if result.get("course_term"):
    db.set_setting(f"course_term_{sync_course_id}", result["course_term"])
```
In `canvas_sync.py` `sync_course_data`, add `course_term` to the returned dict by reading `getattr(getattr(course, "enrollment_term", None), "name", None)` from the fetched course object (the function already fetches the Canvas course object — find where `course_name` is extracted and add term alongside it).

**In `canvas-react/src/Settings.jsx` — Browse Courses dropdown:**
Change the option label for each course to include term when present:
```jsx
<option key={course.id} value={course.id}>
  {course.name}{course.term ? ` — ${course.term}` : ''} ({course.code || course.id})
</option>
```
  </action>
  <verify>
    Run `uv run ruff check .` from project root — must pass.
    Run `npm run lint` in `canvas-react/` — must pass.
    After clicking "Browse Courses" in Settings, each option label should include term name if Canvas returns it (e.g. "CS 161: Intro to CS — Spring 2025 (CS161)").
    After a sync, `/api/canvas/courses` response should include a `term` field per course.
  </verify>
  <done>
    `fetch_available_courses` returns a `term` field per course (None when unavailable).
    `/api/canvas/courses` returns a `term` field per course (populated after first sync of that course).
    Settings "Browse Courses" dropdown shows "CourseName — Term (code)" format.
    App header shows "CourseName — Term" when term is available.
  </done>
</task>

</tasks>

<verification>
1. `npm run lint` in `canvas-react/` passes with no errors
2. `uv run ruff check .` passes with no errors
3. Manual flow verification:
   - Navigate to Settings page
   - Click "Browse Courses" — each dropdown option shows term info when available
   - Select a different course, click "Save &amp; Sync Now"
   - Navigate to Dashboard — data is for the new course
   - Navigate to Late Days — data is for the new course
   - Navigate to Peer Reviews — selector defaults to the new course
   - Header shows current course name beneath "Canvas TA Dashboard"
</verification>

<success_criteria>
- Course change in Settings propagates to all dashboard pages on next navigation
- App header displays current course name (and term when available)
- Settings Browse Courses dropdown shows "Name — Term (code)" per option
- No ESLint or Ruff errors introduced
</success_criteria>

<output>
After completion, create `.planning/quick/1-fix-course-selection-not-propagating-to-/1-SUMMARY.md`
</output>
