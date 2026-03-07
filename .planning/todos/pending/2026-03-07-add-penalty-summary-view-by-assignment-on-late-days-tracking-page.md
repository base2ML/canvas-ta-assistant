---
created: 2026-03-07T07:20:39.111Z
title: Add penalty summary view by assignment on Late Days Tracking page
area: ui
files:
  - canvas-react/src/LateDaysTracking.jsx
  - main.py
---

## Problem

When TAs need to update student grades for late submissions, they currently have no way to get a quick list of which students have penalties on a specific assignment, grouped by grading TA, with the relevant penalty information. They have to scan the full late days matrix manually. Head TA wants to be able to screenshot a clean summary and send it to each grading TA so they know which students to deduct points from and by how much.

## Solution

Add a "Penalty Summary" mode or panel to the Late Days Tracking page that:

- Lets the user select a specific assignment from a dropdown
- Shows a table of students who have `penalty_days > 0` on that assignment
- Orders results by grading TA (group name), then by student name within each TA's section
- Columns: Student Name, Grading TA, Days Late, Bank Days Used, Penalty Days, Penalty %
- Clean, print/screenshot-friendly layout (minimal chrome, clear headers)
- Optional: "Copy as table" or print button for easy sharing

### Backend
- The existing `/api/dashboard/late-days/{course_id}` endpoint already returns per-assignment penalty data
- May need a dedicated endpoint filtered by assignment_id to avoid sending full matrix for large courses
- Group membership data already available via `groups` + `group_members` tables

### Frontend
- Add assignment selector to Late Days Tracking page header
- Toggle between full matrix view and penalty summary view
- Penalty summary table should be clean enough to screenshot (or trigger browser print)

### Considerations
- Student names are PII — FERPA reminder in UI if exporting/sharing
- Should handle case where selected assignment has no penalties (show empty state)
- Ordering: group by TA alphabetically, then students alphabetically within group
