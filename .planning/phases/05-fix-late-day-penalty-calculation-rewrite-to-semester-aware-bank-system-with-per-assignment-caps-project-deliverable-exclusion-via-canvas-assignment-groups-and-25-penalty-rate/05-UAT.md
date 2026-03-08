---
status: testing
phase: 05-fix-late-day-penalty-calculation
source: 05-01-SUMMARY.md, 05-02-SUMMARY.md, 05-03-SUMMARY.md, 05-04-SUMMARY.md
started: 2026-03-02T04:14:00Z
updated: 2026-03-02T04:14:00Z
---

## Current Test

number: 7
name: Late Days Tracking — Not Accepted badge for project deliverables
expected: |
  If an assignment group is NOT in the "allows late days" list (project deliverable), and
  a student submitted late, that assignment cell shows a red "NA" badge instead of
  green/red circles. The student's bank balance is unchanged.
result: issue
reported: "I have unselected Homework as an allowable group, saved the settings, navigated to the late day page, but Homework did not switch to NA and is still calculating the days"
severity: major

## Tests

### 1. Late Day Policy section in Settings
expected: Navigate to Settings. Between "Course Configuration" and "Comment Templates" there should be a "Late Day Policy" section with three numeric inputs: total bank (default 10), penalty rate % (default 25), per-assignment cap (default 7). Below the inputs is a checkbox list of Canvas assignment groups and a "Save Policy Settings" button.
result: pass

### 2. Assignment groups load in Settings
expected: After triggering a Canvas sync (via the Refresh Data button), open Settings. The Late Day Policy section's checkbox list should show the actual Canvas assignment groups for your course (e.g., "Homework", "Projects", "Labs"). Before sync they may be empty.
result: pass

### 3. Policy settings save and persist
expected: Change the total bank to a different number (e.g., 8), check/uncheck a group, click "Save Policy Settings". A green success message appears inline. Reload the Settings page — the values you saved are still there.
result: pass

### 4. Late Days Tracking — bank balance per student
expected: Open Late Days Tracking. Each student row should show a bank balance indicator below their total late days count, e.g. "7/10 bank left" or "3/10 bank left". Students who have used no late days show "10/10 bank left".
result: pass

### 5. Late Days Tracking — green cells for bank-covered days
expected: For a student who submitted late but within their bank, the assignment cell shows green circles equal to the number of bank days used. No red circles appear (no penalty).
result: pass

### 6. Late Days Tracking — red cells for penalty days
expected: For a student who exhausted their bank and submitted late, the assignment cell shows red circles for the penalty days (days beyond bank coverage). If they also used some bank days, green circles appear too (stacked green-over-red).
result: pass

### 7. Late Days Tracking — Not Accepted badge for project deliverables
expected: If an assignment group is NOT in the "allows late days" list (project deliverable), and a student submitted late, that assignment cell shows a red "NA" badge instead of green/red circles. The student's bank balance is unchanged.
result: [pending]

### 8. Late Days Tracking — color legend
expected: Below the Late Days Tracking table there is a color legend explaining the visual indicators: green = bank-covered, red = penalty, NA = not accepted.
result: [pending]

### 9. Comment preview uses correct bank-aware penalty
expected: In the Late Days Tracking page, click the comment preview for a student who submitted 3 days late with 2 bank days remaining. The preview shows 2 bank days used, 1 penalty day, and a 25% penalty (not 30% from the old 10%/day rate). Template variables like {bank_days_used}, {bank_remaining}, {penalty_percent} render with correct values.
result: [pending]

### 10. Post comments skips project deliverables
expected: When posting comments via the SSE bulk post flow, project deliverable assignments (not_accepted=true) are skipped — the post log shows a "skipped" entry for those assignments rather than attempting to post a comment.
result: [pending]

## Summary

total: 10
passed: 6
issues: 1
pending: 3
skipped: 0

## Gaps

- truth: "Unselecting an assignment group from 'allows late days' causes its assignments to show NA badge on Late Days Tracking page"
  status: failed
  reason: "User reported: I have unselected Homework as an allowable group, saved the settings, navigated to the late day page, but Homework did not switch to NA and is still calculating the days"
  severity: major
  test: 7
  root_cause: "Canvas sync has not run with Phase 05-02 code active: assignment_groups table is empty (0 rows), all 23 assignments have NULL assignment_group_id. Without group data, Settings shows no checkboxes and the algorithm has no group IDs to compare against. eligible_set is empty set (from stored '[]') which triggers backward-compat all-eligible mode."
  artifacts:
    - path: "canvas_sync.py:273-287"
      issue: "sync code correct but hasn't run since 05-02 deployed"
    - path: "database.py:972-985"
      issue: "get_assignments SELECT includes assignment_group_id but all values are NULL"
  missing:
    - "Trigger a Canvas sync (Refresh Data button) to populate assignment_groups table and annotation on assignments"
    - "After sync: configure eligible groups in Settings, then reload Late Days Tracking"
  debug_session: ""
