---
phase: quick-6
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - canvas-react/src/Settings.jsx
autonomous: true
requirements:
  - QUICK-6-eligibility-sync
must_haves:
  truths:
    - "When assignment groups load and no eligible groups are saved, all group checkboxes appear checked"
    - "User can uncheck specific groups (e.g., Homework) and save to exclude them from late day calculations"
    - "Unchecking a group and saving persists the partial list so the backend applies it correctly"
  artifacts:
    - path: "canvas-react/src/Settings.jsx"
      provides: "Auto-populate eligible groups on load when setting is unconfigured"
      contains: "setPolicySettings"
  key_links:
    - from: "loadAssignmentGroups (Settings.jsx)"
      to: "policySettings.late_day_eligible_groups"
      via: "setPolicySettings updater after setAssignmentGroups"
      pattern: "setPolicySettings\\(prev"
---

<objective>
Fix the UI/backend mismatch where an empty `late_day_eligible_groups` list causes all assignment group checkboxes to appear unchecked in Settings, while the backend treats an empty list as "all assignments eligible." This confuses users who think unchecked = excluded, when actually unchecked + empty = all included.

Purpose: Align the UI's visual state with the backend's "all eligible by default" semantics so users can meaningfully exclude groups.
Output: When groups load and `policySettings.late_day_eligible_groups` is empty (`[]`), auto-populate it with all group IDs, making every checkbox checked. The user can then uncheck specific groups and save to exclude them.
</objective>

<execution_context>
@/Users/mapajr/.claude/get-shit-done/workflows/execute-plan.md
@/Users/mapajr/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

<interfaces>
<!-- From canvas-react/src/Settings.jsx — relevant state and callbacks -->

State:
  assignmentGroups: []        // set by setAssignmentGroups(data.groups || [])
  policySettings: {
    total_late_day_bank: number,
    penalty_rate_per_day: number,
    per_assignment_cap: number,
    late_day_eligible_groups: number[],  // empty [] means unconfigured
  }

loadAssignmentGroups (lines 174-182):
  const loadAssignmentGroups = useCallback(async () => {
      if (!settings.course_id) return;
      try {
          const data = await apiFetch(`/api/canvas/assignment-groups/${settings.course_id}`);
          setAssignmentGroups(data.groups || []);
          // <-- FIX GOES HERE
      } catch (err) {
          console.error('Error loading assignment groups:', err);
      }
  }, [settings.course_id]);

loadSettings (lines 39-58):
  setPolicySettings({
      ...
      late_day_eligible_groups: data.late_day_eligible_groups ?? [],
  });
  // loadSettings and loadAssignmentGroups are independent useEffects;
  // loadSettings fires first (on mount), loadAssignmentGroups fires
  // when settings.course_id changes. By the time groups load,
  // policySettings is already set from the API response.
</interfaces>

Backend behavior (confirmed, Phase 05 decision):
  Empty late_day_eligible_group_ids → all assignments eligible (backward compat).
  Non-empty list → only assignments in those groups are eligible.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Auto-populate eligible groups when setting is unconfigured</name>
  <files>canvas-react/src/Settings.jsx</files>
  <action>
In `loadAssignmentGroups` (around line 174), after `setAssignmentGroups(data.groups || [])`, add a `setPolicySettings` functional update that fills in all group IDs when the current eligible list is empty.

The condition must check: groups loaded successfully (non-empty) AND current `policySettings.late_day_eligible_groups` is empty (`length === 0`).

Use the functional form of `setPolicySettings` to read the latest `prev` state (avoids stale closure on `policySettings`):

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

Do NOT change `loadSettings`, the save handler, or any other logic. This single addition is the entire fix.

Why functional updater: `loadAssignmentGroups` is a `useCallback` with `[settings.course_id]` dependency. When it runs, `policySettings` may have been freshly set by `loadSettings`. The functional `setPolicySettings(prev => ...)` reads the current state at call time rather than the stale closure value, ensuring the "is empty?" check is accurate even if both effects fire close together.
  </action>
  <verify>
    <automated>cd /Users/mapajr/git/cda-ta-dashboard/canvas-react && npm run build 2>&1 | tail -5</automated>
  </verify>
  <done>
    - Build succeeds with no errors
    - In Settings UI: when assignment groups load and no groups were previously saved, all group checkboxes appear checked
    - Unchecking "Homework" and saving sends a non-empty list to the backend, which now correctly excludes Homework assignments from late day calculations
    - If groups were previously saved (non-empty list in DB), existing checkboxes are unaffected (condition is `length === 0`)
  </done>
</task>

</tasks>

<verification>
1. `npm run build` passes (no lint or compile errors)
2. Open Settings in browser: Late Day Policy section shows all assignment group checkboxes as CHECKED on first load (or after clearing the setting)
3. Uncheck one group → click "Save Policy Settings" → reload page → that group remains unchecked
4. Verify the late day calculation now respects the exclusion (navigate to Late Days Tracking — assignments in the excluded group should not consume late days)
</verification>

<success_criteria>
- Settings UI checkboxes visually match backend semantics: empty saved list → all checked, partial list → only saved IDs checked
- Saving a partial list (e.g., excluding Homework) persists and applies to the late day algorithm
- No regression: users with an already-configured non-empty eligible list see no change
</success_criteria>

<output>
After completion, create `.planning/quick/6-fix-assignment-group-eligibility-not-app/6-SUMMARY.md`
</output>
