---
phase: quick-6
plan: 01
subsystem: frontend
tags: [settings, late-days, assignment-groups, ux-fix]
dependency_graph:
  requires: []
  provides: [assignment-group-eligibility-auto-populate]
  affects: [canvas-react/src/Settings.jsx]
tech_stack:
  added: []
  patterns: [functional-setState-to-avoid-stale-closure]
key_files:
  created: []
  modified:
    - canvas-react/src/Settings.jsx
decisions:
  - "Use functional setPolicySettings(prev => ...) inside loadAssignmentGroups useCallback to read latest state rather than stale closure value"
  - "Condition on length === 0 only so users with a previously saved non-empty list see no change"
metrics:
  duration: "~2 min"
  completed_date: "2026-03-02"
---

# Quick Task 6: Fix Assignment Group Eligibility Auto-Populate Summary

**One-liner:** Auto-populate all group IDs into `late_day_eligible_groups` on load when the setting is unconfigured (empty list), aligning checkbox UI with backend "all eligible by default" semantics.

## What Was Done

When the Settings page loaded assignment groups from the API and `policySettings.late_day_eligible_groups` was `[]` (unconfigured), all checkboxes appeared unchecked. But the backend treats an empty list as "all assignments eligible," creating a confusing mismatch where the UI showed "nothing selected" while the backend behaved as if "everything selected."

The fix adds a single `setPolicySettings` functional update inside `loadAssignmentGroups` immediately after `setAssignmentGroups`:

```js
const groups = data.groups || [];
setAssignmentGroups(groups);
if (groups.length > 0) {
    setPolicySettings(prev =>
        prev.late_day_eligible_groups.length === 0
            ? { ...prev, late_day_eligible_groups: groups.map(g => g.id) }
            : prev
    );
}
```

The functional updater (`prev => ...`) is required because `loadAssignmentGroups` is a `useCallback` with `[settings.course_id]` as its only dependency. When the callback runs, `policySettings` in its closure may be stale. The functional form reads the current state at call time, ensuring the "is empty?" check is accurate even when `loadSettings` and `loadAssignmentGroups` fire close together.

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Auto-populate eligible groups when setting is unconfigured | dd017dc | canvas-react/src/Settings.jsx |

## Verification

- `npm run build` passes (822ms, no errors)
- All pre-commit hooks passed (ESLint, secrets scan, etc.)

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- File modified: `canvas-react/src/Settings.jsx` — exists and contains the fix
- Commit `dd017dc` present in git log
