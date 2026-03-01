---
phase: quick-4
plan: 4
type: execute
wave: 1
depends_on: []
files_modified:
  - canvas-react/src/EnrollmentTracking.jsx
autonomous: true
requirements: [QUICK-4]
must_haves:
  truths:
    - "Enrollment Timeline only shows sync snapshots where enrollment actually changed (at least one add or drop)"
    - "A line chart appears above the timeline showing active enrollment count over time"
    - "Syncs with no enrollment change are silently omitted — no message needed unless ALL syncs had zero changes"
  artifacts:
    - path: "canvas-react/src/EnrollmentTracking.jsx"
      provides: "Updated enrollment tracking view with filtered timeline and SVG line chart"
      contains: "changedSnapshots"
  key_links:
    - from: "canvas-react/src/EnrollmentTracking.jsx"
      to: "enrollmentData.snapshots"
      via: "filter(s => s.newly_enrolled_count > 0 || s.newly_dropped_count > 0)"
      pattern: "newly_enrolled_count|newly_dropped_count"
---

<objective>
Filter the Enrollment Timeline to show only syncs where enrollment changed (adds or drops occurred), and add an SVG line plot showing active enrollment count across all snapshots over the semester.

Purpose: The current timeline shows every sync, most of which are identical — making it hard to spot actual enrollment changes. The line chart gives a visual overview of enrollment trend over time.
Output: Updated EnrollmentTracking.jsx with filtered timeline and inline SVG line chart.
</objective>

<execution_context>
@/Users/mapajr/.claude/get-shit-done/workflows/execute-plan.md
@/Users/mapajr/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@canvas-react/src/EnrollmentTracking.jsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Filter enrollment timeline to changes-only and add SVG line chart</name>
  <files>canvas-react/src/EnrollmentTracking.jsx</files>
  <action>
Make two changes to EnrollmentTracking.jsx:

**1. Filter the Enrollment Timeline section**

Before the `enrollmentData.snapshots.map(...)` call, derive a filtered list:

```js
const changedSnapshots = (enrollmentData.snapshots || []).filter(
  s => s.newly_enrolled_count > 0 || s.newly_dropped_count > 0
);
```

Replace the existing condition and map:
- Change `enrollmentData.snapshots && enrollmentData.snapshots.length > 0` guard to `changedSnapshots.length > 0`
- Map over `changedSnapshots` instead of `enrollmentData.snapshots`
- Update the section heading to "Enrollment Changes" (was "Enrollment Timeline")
- In the empty state check at the bottom, keep the existing `events` fallback unchanged — only change the snapshots half to `changedSnapshots.length === 0`

**2. Add SVG line chart above the Enrollment Changes section**

Use ALL snapshots (not filtered) for the chart so the full trend is visible. Snapshots are ordered newest-first, so reverse them for chronological order:

```js
const chronologicalSnapshots = [...(enrollmentData.snapshots || [])].reverse();
```

Render the chart only when `chronologicalSnapshots.length >= 2`. Use a self-contained inline SVG — no external library. Implementation approach:

- Chart dimensions: viewBox="0 0 600 160", rendered as `<svg viewBox="0 0 600 160" className="w-full h-40">`
- Padding: left=50, right=20, top=16, bottom=32
- X axis: map index to x position across the plot width
- Y axis: compute min/max of active_count across all snapshots; add 5% padding above/below. If min===max, use min-1 / max+1 to avoid division by zero
- Plot a single polyline for `active_count` using `stroke="#2563eb"` (blue-600), `strokeWidth="2"`, `fill="none"`
- Add dots at each data point: `<circle r="3" fill="#2563eb" />`
- X-axis labels: show formatted date (`toLocaleDateString()`) for first and last snapshot only, rendered as `<text>` at bottom; `fontSize="10"` `fill="#6b7280"`
- Y-axis labels: min and max active_count values on the left, `fontSize="10"` `fill="#6b7280"`
- Wrap the SVG in a card: `<div className="bg-white rounded-lg shadow-sm border p-6 mb-6">` with heading `<h2 className="text-lg font-semibold text-gray-900 mb-4">Enrollment Over Time</h2>`

Place this chart card ABOVE the "Enrollment Changes" section (above the existing snapshots card).
  </action>
  <verify>
Run `npm run lint` from `canvas-react/` — must pass with no errors.
Visually: load http://localhost:5173/enrollment (or the Enrollment Tracking page). If at least 2 syncs exist, the chart appears. The timeline below it should only list rows where students enrolled or dropped.
  </verify>
  <done>
- Enrollment Timeline renamed "Enrollment Changes" and only shows rows with newly_enrolled_count > 0 OR newly_dropped_count > 0
- An SVG line chart titled "Enrollment Over Time" appears above the changes list, plotting active_count chronologically
- ESLint passes cleanly
  </done>
</task>

</tasks>

<verification>
1. `npm run lint` from `canvas-react/` passes with no errors
2. In the UI: if all syncs had zero changes, the "Enrollment Changes" section shows an empty-state message (existing behavior from the bottom empty state check)
3. The line chart renders with a polyline + dots + first/last date labels + y-axis min/max labels
</verification>

<success_criteria>
- Enrollment Timeline filtered to changes-only using newly_enrolled_count and newly_dropped_count fields already returned by the API
- SVG line chart visible above the timeline, using no external charting dependency
- ESLint clean
</success_criteria>

<output>
After completion, create `.planning/quick/4-filter-enrollment-sync-history-to-only-s/4-SUMMARY.md`
</output>
