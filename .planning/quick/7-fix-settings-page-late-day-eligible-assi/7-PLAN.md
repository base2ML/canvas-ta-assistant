---
phase: quick-7
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - canvas-react/src/Settings.jsx
autonomous: true
requirements:
  - QUICK-7
must_haves:
  truths:
    - "Unchecking a group and saving Policy Settings persists across page refresh"
    - "The Late Days Tracking page reflects only the saved eligible groups"
    - "Auto-populate (all groups checked) only fires when the DB value is actually empty (no saved groups)"
  artifacts:
    - path: canvas-react/src/Settings.jsx
      provides: "Race-condition-free eligible groups checkbox UI"
      contains: "policySettingsLoaded"
  key_links:
    - from: canvas-react/src/Settings.jsx
      to: /api/settings
      via: "savePolicySettings() PUT call with late_day_eligible_groups"
      pattern: "late_day_eligible_groups.*policySettings"
---

<objective>
Fix the race condition in Settings.jsx that causes the "Late Day Eligible Assignment Groups" checklist to always revert to all groups checked, overwriting the user's saved partial selection.

Purpose: Unchecking a group (e.g. "Project Deliverables") and saving should persist. Currently the auto-populate logic fires before loadSettings() completes, seeing an empty list and selecting all groups, which then gets saved again.

Output: Settings.jsx with policySettingsLoaded guard so auto-populate only fires after the saved DB value is confirmed empty.
</objective>

<execution_context>
@/Users/mapajr/.claude/get-shit-done/workflows/execute-plan.md
@/Users/mapajr/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/PAUSE.md
@canvas-react/src/Settings.jsx

<!-- Root cause summary from PAUSE.md:
  Race condition: loadSettings() and loadAssignmentGroups() run concurrently on mount.
  If loadAssignmentGroups() resolves first, policySettings.late_day_eligible_groups.length === 0
  (settings not yet loaded), so auto-populate fires and overwrites the DB-saved value with all
  group IDs. The user sees all groups checked even after saving a partial list.

  Partial fix is stashed at stash@{0}:
  - Added policySettingsLoaded state (bool, default false)
  - Sets setPolicySettingsLoaded(true) after settings load in loadSettings()

  Still needed (from PAUSE.md):
  - Replace the auto-populate block inside loadAssignmentGroups with a separate useEffect
    gated on policySettingsLoaded
  - Remove the inline auto-populate block from loadAssignmentGroups
-->
</context>

<tasks>

<task type="auto">
  <name>Task 1: Apply stash and complete the policySettingsLoaded race condition fix</name>
  <files>canvas-react/src/Settings.jsx</files>
  <action>
  Step 1 — Pop the stash (which has the policySettingsLoaded state and setPolicySettingsLoaded(true) already added):
  ```
  git stash pop
  ```
  The stash adds only two lines to Settings.jsx:
  - `const [policySettingsLoaded, setPolicySettingsLoaded] = useState(false);` after line 36
  - `setPolicySettingsLoaded(true);` after the setPolicySettings() call in loadSettings()

  Step 2 — Remove the inline auto-populate block from loadAssignmentGroups. Find this block (around lines 180-185 in the post-stash file) and delete it:
  ```javascript
  // DELETE THIS ENTIRE BLOCK from inside loadAssignmentGroups:
  if (groups.length > 0) {
      setPolicySettings(prev =>
          prev.late_day_eligible_groups.length === 0
              ? { ...prev, late_day_eligible_groups: groups.map(g => g.id) }
              : prev
      );
  }
  ```

  Step 3 — Add a new standalone useEffect immediately after the existing `useEffect(() => { loadAssignmentGroups(); }, [loadAssignmentGroups]);` line (around line 192):
  ```javascript
  // Auto-populate eligible groups ONLY when settings have loaded and confirmed empty
  useEffect(() => {
      if (policySettingsLoaded && assignmentGroups.length > 0) {
          setPolicySettings(prev =>
              prev.late_day_eligible_groups.length === 0
                  ? { ...prev, late_day_eligible_groups: assignmentGroups.map(g => g.id) }
                  : prev
          );
      }
  }, [policySettingsLoaded, assignmentGroups]);
  ```

  This ensures: if loadSettings() resolves first (typical), policySettingsLoaded becomes true with the real DB value. The useEffect then checks: if late_day_eligible_groups is STILL empty after loading, auto-populate. If it has saved group IDs, leave it alone.

  Step 4 — Rebuild and restart the frontend container:
  ```
  cd /Users/mapajr/git/cda-ta-dashboard && docker-compose up -d --build frontend
  ```
  </action>
  <verify>
    <automated>cd /Users/mapajr/git/cda-ta-dashboard/canvas-react && npm run lint 2>&1 | tail -5</automated>
  </verify>
  <done>
  - Settings.jsx has policySettingsLoaded state
  - setPolicySettingsLoaded(true) is called inside loadSettings() success path
  - loadAssignmentGroups() no longer contains any auto-populate block
  - A separate useEffect gated on policySettingsLoaded handles auto-populate
  - Frontend container rebuilt successfully
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>Race condition fix for Late Day Eligible Assignment Groups persistence</what-built>
  <how-to-verify>
    1. Open Settings page at http://localhost:3000 → navigate to Settings
    2. In the Late Day Policy section, uncheck one or more groups (e.g. "Project Deliverables")
    3. Click "Save Policy Settings" — confirm the green success banner appears
    4. Refresh the page (Cmd+R or F5)
    5. EXPECTED: The unchecked groups remain unchecked after refresh
    6. EXPECTED: The Late Days Tracking page now marks assignments in unchecked groups as "Not Accepted" for late submissions
    7. NEGATIVE TEST: If ALL groups are unchecked then saved, refresh should still show all unchecked (empty means all eligible per backward compat — but that is correct behavior, not a bug)
  </how-to-verify>
  <resume-signal>Type "approved" if unchecked groups persist after refresh, or describe what's still broken</resume-signal>
</task>

</tasks>

<verification>
- git stash pop succeeds with no conflicts
- Settings.jsx lint passes (npm run lint exits 0)
- No auto-populate block remains inside loadAssignmentGroups callback
- New useEffect is gated on [policySettingsLoaded, assignmentGroups]
- Docker frontend container rebuilds and starts healthy
</verification>

<success_criteria>
Uncheck any assignment group, click Save Policy Settings, refresh the page — the unchecked group stays unchecked. The Late Days Tracking page reflects the saved eligible groups in its calculations.
</success_criteria>

<output>
After completion, create `.planning/quick/7-fix-settings-page-late-day-eligible-assi/7-SUMMARY.md` with:
- What was fixed (race condition description)
- Files modified
- Commit hash
Then delete `.planning/PAUSE.md` and update `.planning/STATE.md` quick tasks table.
</output>
