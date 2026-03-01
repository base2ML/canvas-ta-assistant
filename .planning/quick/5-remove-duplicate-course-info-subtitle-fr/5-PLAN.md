---
phase: quick-5
plan: 5
type: execute
wave: 1
depends_on: []
files_modified:
  - canvas-react/src/LateDaysTracking.jsx
autonomous: true
requirements:
  - QUICK-05
must_haves:
  truths:
    - "Late Days Tracking page header shows only the title and subtitle, not the course name/code"
    - "The FileText icon block for courseInfo is removed from the page header"
  artifacts:
    - path: "canvas-react/src/LateDaysTracking.jsx"
      provides: "Updated page header without duplicate course info block"
  key_links:
    - from: "canvas-react/src/LateDaysTracking.jsx"
      to: "lines 378-383 (courseInfo conditional block)"
      via: "delete block"
      pattern: "courseInfo &&"
---

<objective>
Remove the duplicate course info subtitle from the Late Days Tracking page header.

Purpose: The course name and section are already displayed in the global header (added in Quick 1). Showing it again inside the page body ("Computational Data Analysis - ISYE-6740-OAN, ASY (512282)") is redundant and visually noisy.
Output: LateDaysTracking.jsx with the courseInfo block removed from the page header section.
</objective>

<execution_context>
@/Users/mapajr/.claude/get-shit-done/workflows/execute-plan.md
@/Users/mapajr/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Remove courseInfo block from page header</name>
  <files>canvas-react/src/LateDaysTracking.jsx</files>
  <action>
Delete lines 378-383 — the conditional block that renders course name and code inside the page header:

```jsx
{courseInfo && (
  <div className="flex items-center mt-2 text-sm text-gray-500">
    <FileText className="h-4 w-4 mr-1" />
    {courseInfo ? `${courseInfo.name} (${courseInfo.course_code})` : currentCourse ? `${currentCourse.name}` : 'No Course Selected'}
  </div>
)}
```

The `courseInfo` state variable and `setCourseInfo` call in `loadCourseData` (line 94) must be retained — `courseInfo` may still be referenced elsewhere in the file (line 1025 shows it used in the posting panel). Only delete the display block from the header.

After deletion, also check if the `FileText` icon import is still needed elsewhere in the file. If `FileText` is no longer used after removing this block, remove it from the lucide-react import line to keep imports clean.
  </action>
  <verify>
    <automated>cd /Users/mapajr/git/cda-ta-dashboard/canvas-react && npm run build 2>&1 | tail -5</automated>
  </verify>
  <done>
Page header renders only the h1 title and subtitle paragraph. No courseInfo div appears in the header. Build passes with no errors.
  </done>
</task>

</tasks>

<verification>
After the task completes:
- Visually confirm: page header shows "Late Days Tracking / Monitor student late day usage across assignments" with no course name line beneath
- Confirm the global header still shows the course name (unchanged — not touched by this plan)
- Build passes: `npm run build` exits 0
</verification>

<success_criteria>
The courseInfo conditional block is deleted from the LateDaysTracking page header. Unused imports (FileText if applicable) are cleaned up. Build passes clean.
</success_criteria>

<output>
After completion, create `.planning/quick/5-remove-duplicate-course-info-subtitle-fr/5-SUMMARY.md`
</output>
