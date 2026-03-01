# Phase 4: Unified Refresh - Research

**Researched:** 2026-02-28
**Domain:** React state propagation — refreshTrigger pattern, prop drilling vs. Context API, Vitest component testing
**Confidence:** HIGH

## Summary

Phase 4 is a pure frontend refactor with no backend changes. The work is entirely in `canvas-react/src/`: add a `refreshTrigger` counter and `lastSyncedAt` timestamp to the `App.jsx` header, pass them as props to all dashboard pages, and remove the redundant per-page refresh buttons and timestamps. The backend sync endpoint (`POST /api/canvas/sync`) already exists and works correctly.

The architecture pattern to use is **prop-based refreshTrigger** — the same pattern already established in this codebase for `activeCourseId` propagation (Quick Task 1 decision logged in STATE.md). App.jsx holds the `refreshTrigger` counter; each dashboard page runs its `loadCourseData()` inside a `useEffect` that depends on `refreshTrigger`, so clicking "Refresh Data" in the header auto-increments the counter, which re-fires the effect and reloads data in every mounted page.

The Settings page cleanup is simple: remove the "Sync Now" button from the Sync Status section and rename "Save & Sync Now" to "Save Settings" (call `saveSettings()` only). The per-page display items to remove (CLEAN-03, CLEAN-04, CLEAN-05) are precisely located in the codebase and are small, isolated deletes.

**Primary recommendation:** Use a single `refreshTrigger` integer in App.jsx state, passed as a prop to all four dashboard pages, consumed in each page's `useEffect` dependency array alongside `currentCourse`.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SYNC-01 | Header "Refresh Data" button triggers Canvas data sync and shows loading state while running | App.jsx already has `handleRefreshData` with `setSyncing(true)` — needs `refreshTrigger` increment after sync resolves |
| SYNC-02 | Header displays last synced timestamp after any sync completes, visible from all pages | Add `lastSyncedAt` state to App.jsx; set it in `handleRefreshData` on success; render in header; replace per-page timestamps |
| SYNC-03 | After sync completes, all dashboard pages automatically reload their data without user action | Pass `refreshTrigger` prop to all four pages; add to each page's `useEffect` dependency array |
| CLEAN-01 | Settings "Sync Now" button removed | Remove the "Sync Now" button (lines ~343-354) from the Sync Status section in Settings.jsx |
| CLEAN-02 | Settings "Save & Sync Now" replaced with "Save Settings" only | Remove the `saveAndSync` button (lines ~324-336) in Settings.jsx Course Configuration section |
| CLEAN-03 | EnhancedTADashboard "Refresh" button and page-level "Last Updated" timestamp removed | Remove `refreshData` function, the `<button onClick={refreshData}>` and `{lastUpdated && ...}` block (lines ~209-253) in EnhancedTADashboard.jsx |
| CLEAN-04 | EnrollmentTracking "Refresh" button and "Last updated"/"Load time" display removed | Remove Refresh button (lines ~97-105) and the `lastUpdated`/`loadTime` spans (lines ~108-113) in EnrollmentTracking.jsx |
| CLEAN-05 | LateDaysTracking page-level "⚡ Loaded in Xs" and "🕒 Cached: time" removed | Remove `loadTime` and `lastUpdated` display blocks (lines ~396-405) in LateDaysTracking.jsx |
</phase_requirements>

---

## Standard Stack

### Core (already installed — no new packages needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19.1.1 | Component state and hooks | Already in use |
| react-router-dom | 7.9.6 | Routing (already in App.jsx) | Already in use |
| Vitest | 4.0.14 | Frontend test runner | Already configured in vite.config.js |
| @testing-library/react | 16.3.0 | Component rendering in tests | Already in use |

**No new packages required.** This phase is a refactor of existing code using existing dependencies.

**Installation:**
```bash
# No new installations needed
```

---

## Architecture Patterns

### Recommended File Changes

```
canvas-react/src/
├── App.jsx                    # ADD: refreshTrigger state, lastSyncedAt state; MODIFY: pass as props; MODIFY: header to show lastSyncedAt
├── EnhancedTADashboard.jsx    # ADD: refreshTrigger prop; ADD to useEffect dep array; REMOVE: refreshData fn, Refresh button, lastUpdated display
├── LateDaysTracking.jsx       # ADD: refreshTrigger prop; ADD to useEffect dep array; REMOVE: loadTime/lastUpdated display
├── EnrollmentTracking.jsx     # ADD: refreshTrigger prop; ADD to useEffect dep array; REMOVE: Refresh button, lastUpdated/loadTime display
└── Settings.jsx               # REMOVE: Sync Now button; REMOVE: Save & Sync Now button
```

TAGradingDashboard does not exist as a file in `canvas-react/src/` — it is not a routed page in the current codebase. The ROADMAP success criterion references it, but searching the codebase shows it does not exist. The four actual dashboard pages are: `EnhancedTADashboard`, `LateDaysTracking`, `EnrollmentTracking`, `PeerReviewTracking`. Per REQUIREMENTS.md, PeerReviewTracking is explicitly out of scope (parameterized, independent of Canvas sync).

### Pattern 1: refreshTrigger Counter in App.jsx

**What:** An integer counter stored in App.jsx state. When the header "Refresh Data" button fires sync, the counter is incremented after sync resolves. Pages depend on this counter in their `useEffect`, causing data reload.

**When to use:** When you need to signal all mounted children to re-fetch data from a parent event, without using Context or a state management library.

**Why this pattern:** STATE.md explicitly records that `activeCourseId` was established at the App.jsx level and passed as prop — the same pattern applies for `refreshTrigger/lastSynced`. This is the project's established convention.

**Example:**
```jsx
// App.jsx — add these two state variables
const [refreshTrigger, setRefreshTrigger] = useState(0);
const [lastSyncedAt, setLastSyncedAt] = useState(null);

// Modify handleRefreshData — increment counter and record timestamp after sync
const handleRefreshData = async () => {
  setSyncing(true);
  setSyncMessage(null);
  try {
    const data = await apiFetch('/api/canvas/sync', { method: 'POST' });
    setSyncMessage({
      type: 'success',
      text: `Synced ${data.stats?.assignments || 0} assignments, ${data.stats?.users || 0} users`,
    });
    setLastSyncedAt(new Date());       // NEW: record sync completion time
    setRefreshTrigger(prev => prev + 1); // NEW: signal all pages to reload
    loadSettings();
    loadCourses();
  } catch (err) {
    console.error('Sync failed:', err);
    setSyncMessage({
      type: 'error',
      text: err.message || 'Failed to connect to server',
    });
  } finally {
    setSyncing(false);
  }
};
```

### Pattern 2: Pass refreshTrigger to Dashboard Pages

**What:** Add `refreshTrigger` as a prop to each dashboard route element. Each page adds it to its primary data-loading `useEffect` dependency array.

**Example:**
```jsx
// App.jsx — Routes section (add refreshTrigger prop to each page)
<Route
  path="/"
  element={
    <EnhancedTADashboard
      courses={courses}
      onLoadCourses={loadCourses}
      loadingCourses={loading}
      activeCourseId={activeCourseId}
      refreshTrigger={refreshTrigger}   // NEW
    />
  }
/>
<Route
  path="/late-days"
  element={
    <LateDaysTracking
      courses={courses}
      onLoadCourses={loadCourses}
      activeCourseId={activeCourseId}
      refreshTrigger={refreshTrigger}   // NEW
    />
  }
/>
<Route
  path="/enrollment"
  element={
    <EnrollmentTracking
      courses={courses}
      onLoadCourses={loadCourses}
      activeCourseId={activeCourseId}
      refreshTrigger={refreshTrigger}   // NEW
    />
  }
/>
```

### Pattern 3: useEffect with refreshTrigger in each Page

**What:** Each dashboard page receives `refreshTrigger` prop and includes it in the dependency array of its primary data-loading `useEffect`.

**Example (EnhancedTADashboard):**
```jsx
// EnhancedTADashboard.jsx
const EnhancedTADashboard = ({ courses = [], onLoadCourses, loadingCourses, activeCourseId, refreshTrigger }) => {
  // ... existing state ...

  // EXISTING useEffect — add refreshTrigger to deps
  useEffect(() => {
    if (courses && courses.length > 0) {
      const target = courses.find(c => String(c.id) === String(activeCourseId)) || courses[0];
      // On refreshTrigger change, force reload even if same course
      setSelectedCourse(target);
      loadCourseData(target.id);
    }
  }, [courses, activeCourseId, loadCourseData, refreshTrigger]); // ADD refreshTrigger
};
```

**Example (LateDaysTracking and EnrollmentTracking):**
```jsx
// LateDaysTracking.jsx
const LateDaysTracking = ({ courses, onLoadCourses, activeCourseId, refreshTrigger }) => {
  // ...
  useEffect(() => {
    if (currentCourse) {
      loadCourseData();
    } else if ((!courses || courses.length === 0) && onLoadCourses) {
      onLoadCourses();
    }
  }, [currentCourse, loadCourseData, courses, onLoadCourses, refreshTrigger]); // ADD refreshTrigger
};
```

### Pattern 4: lastSyncedAt Timestamp in Header

**What:** After sync, App.jsx sets `lastSyncedAt` state. The header renders it persistently, replacing the auto-dismissing `syncMessage`.

**Example:**
```jsx
// App.jsx header — add lastSyncedAt display
<div className="flex items-center gap-4">
  {syncMessage && (
    <span className={`text-sm ${syncMessage.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
      {syncMessage.text}
    </span>
  )}
  {lastSyncedAt && !syncMessage && (
    <span className="text-xs text-gray-500">
      Synced: {formatDate(lastSyncedAt)}
    </span>
  )}
  <button
    onClick={handleRefreshData}
    disabled={syncing}
    className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
  >
    <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
    {syncing ? 'Syncing...' : 'Refresh Data'}
  </button>
</div>
```

Note: `formatDate` from `./utils/dates` is already imported in App.jsx and respects the configured timezone.

### Pattern 5: Settings.jsx Button Cleanup

**What:** Remove two sync-triggering buttons from Settings.jsx. Keep only "Save Settings".

**Buttons to remove:**
1. "Save & Sync Now" button (in Course Configuration section, calls `saveAndSync()`)
2. "Sync Now" button (in Sync Status section, calls `triggerSync()`)

**Functions that become dead code after removal:**
- `triggerSync` function
- `saveAndSync` function
- `syncing` state variable (and `setSyncing`)

**Functions to keep:**
- `saveSettings` — still needed
- `loadSyncStatus` — still needed (Sync History display remains)
- The Sync Status section itself — keep as read-only display; just remove the trigger button

### Anti-Patterns to Avoid

- **React Context for refreshTrigger:** Do not reach for Context API. The project uses prop drilling for `activeCourseId` and this phase should use the same pattern. Adding Context now would be architectural inconsistency.
- **Calling sync from page components:** Pages must ONLY reload their data after sync. They must NOT trigger `POST /api/canvas/sync` themselves. The sync call lives only in `handleRefreshData` in App.jsx.
- **Removing the `syncing` state from App.jsx:** Keep it — it controls the button's loading animation and `disabled` state per SYNC-01.
- **Removing `triggerSync`/`syncing` from Settings.jsx before removing button references:** ESLint will fail on unused vars. Remove button JSX first, then remove the functions/state.
- **EnhancedTADashboard's refreshData function:** This function calls `POST /api/canvas/sync` directly (duplicating the header). Remove the entire function, not just the button.
- **Losing the Sync History table:** The Sync History table in Settings.jsx must be preserved. Only the trigger buttons are removed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-component data refresh notification | Custom event bus, pub/sub, or custom hook | refreshTrigger integer prop + useEffect dep | Project convention established; no additional complexity needed |
| Formatted timestamp display | Custom date formatter | `formatDate()` from `./utils/dates` | Already imported in App.jsx, respects timezone setting |
| API sync call | New fetch implementation | `apiFetch('/api/canvas/sync', { method: 'POST' })` | Centralized error handling already in `api.js` |

**Key insight:** This phase involves removing code, not adding libraries. The entire implementation is prop threading + JSX deletion.

---

## Common Pitfalls

### Pitfall 1: ESLint Unused Variable Errors After Removing Buttons

**What goes wrong:** After removing the "Sync Now" and "Save & Sync Now" buttons from Settings.jsx, ESLint will flag `syncing`, `setSyncing`, `triggerSync`, and `saveAndSync` as unused variables/functions, failing `npm run lint`.

**Why it happens:** The ESLint config uses `eslint-plugin-react-hooks`. Variables declared with `useState` but never referenced in JSX/logic become unused.

**How to avoid:** Remove button JSX AND the corresponding functions/state together in the same edit. Specifically in Settings.jsx:
- Remove `syncing` / `setSyncing` state declaration
- Remove `triggerSync` function
- Remove `saveAndSync` function
- Remove the `syncing` prop from `setSaving` logic (check for cross-references)

**Warning signs:** `npm run lint` fails after removing buttons.

### Pitfall 2: EnhancedTADashboard useEffect Guard Prevents Reload on refreshTrigger

**What goes wrong:** EnhancedTADashboard's existing `useEffect` has a guard: `if (!selectedCourse || String(selectedCourse.id) !== String(target.id))`. If the same course is already selected when refreshTrigger fires, the guard short-circuits and `loadCourseData` is never called.

**Why it happens:** The guard was added to prevent redundant resets. It compares `selectedCourse` against the target and skips if they match. When refreshTrigger increments but course stays the same, the guard fires.

**How to avoid:** When `refreshTrigger` changes, force reload regardless of course comparison. One approach: only use the guard for course-change logic, not for refreshTrigger-driven reloads. A clean solution:

```jsx
useEffect(() => {
  if (courses && courses.length > 0) {
    const target = courses.find(c => String(c.id) === String(activeCourseId)) || courses[0];
    setSelectedCourse(target);
    loadCourseData(target.id);  // Always reload when refreshTrigger changes
  }
}, [courses, activeCourseId, loadCourseData, refreshTrigger]); // eslint-disable-line react-hooks/exhaustive-deps
```

Remove the `selectedCourse` guard entirely — it is only needed to prevent double-loading on mount, which React 19's strict mode already handles correctly.

**Warning signs:** After clicking "Refresh Data", EnhancedTADashboard data does not update.

### Pitfall 3: currentCourse Derivation Prevents refreshTrigger Re-render

**What goes wrong:** LateDaysTracking and EnrollmentTracking derive `currentCourse` from `courses` and `activeCourseId` at render time (not in state). The `useEffect` depends on `currentCourse`. If `currentCourse` doesn't change when `refreshTrigger` fires, the effect won't re-run.

**Why it happens:** `currentCourse` is a derived value. When refreshTrigger changes but courses/activeCourseId stays the same, `currentCourse` is the same object reference only if `courses` array reference is stable. In React, each render of a parent that passes `courses` as a prop may produce a new array reference.

**How to avoid:** Add `refreshTrigger` directly to the `useEffect` dependency array:

```jsx
useEffect(() => {
  if (currentCourse) {
    loadCourseData();
  } else if ((!courses || courses.length === 0) && onLoadCourses) {
    onLoadCourses();
  }
}, [currentCourse, loadCourseData, courses, onLoadCourses, refreshTrigger]); // refreshTrigger added
```

**Warning signs:** Clicking "Refresh Data" doesn't reload LateDaysTracking or EnrollmentTracking data.

### Pitfall 4: refreshTrigger Fires on Initial Mount

**What goes wrong:** If refreshTrigger starts at 0 and pages include it in deps, the effect fires immediately on mount (expected), but also fires again if App.jsx re-renders and changes refreshTrigger to 1 (on first sync). This double-load is harmless but can cause flicker.

**Why it happens:** useEffect fires on mount (refreshTrigger=0) and again when refreshTrigger=1. Pages already load on mount via their existing `currentCourse` effect, so the refreshTrigger=0 effect is redundant on startup.

**How to avoid:** Initialize `refreshTrigger` at 0. Pages' existing mount-time load is driven by `currentCourse` changing from null to a value. refreshTrigger will only increment on user-triggered sync, not on mount. No special handling needed — the double-load is at most one extra API call on first sync click and is acceptable.

### Pitfall 5: Settings.jsx Sync History Still Needs to Work

**What goes wrong:** Removing `triggerSync` and related state variables breaks the Sync History section if it depends on `syncing` state to show an in-progress indicator.

**Why it happens:** The Sync Status section renders `settings.last_sync.status === 'in_progress'` based on backend data, not the local `syncing` state. The in-progress spinner in the Sync Status section uses `syncing` state which comes from the removed button.

**How to avoid:** The Sync Status section reads from `settings.last_sync` (server data), not from the `syncing` local state. The local `syncing` state was only used by the button. After removing the button and `syncing` state, the in-progress status detection in Sync Status (`settings.last_sync.status === 'in_progress'`) still works correctly — it reads from the backend.

---

## Code Examples

### Exact Lines to Remove — EnhancedTADashboard.jsx

```jsx
// REMOVE: lines 209-231 — entire refreshData function
const refreshData = async () => {
  setLoading(true);
  setError('');
  try {
    const syncResult = await apiFetch('/api/canvas/sync', { method: 'POST' });
    console.log('Sync completed:', syncResult);
    if (selectedCourse) {
      await loadCourseData(selectedCourse.id);
    } else if (onLoadCourses) {
      onLoadCourses();
    }
  } catch (err) {
    console.error('Refresh error:', err);
    setError(`Failed to refresh: ${err.message}`);
  } finally {
    setLoading(false);
  }
};

// REMOVE: lines ~241-253 — lastUpdated display and Refresh button in JSX
{lastUpdated && (
  <div className="text-sm text-gray-500">
    Last Updated: {lastUpdated ? formatDate(lastUpdated) : 'Never'}
  </div>
)}
<button
  onClick={refreshData}
  disabled={loading}
  className="inline-flex items-center space-x-2 ..."
>
  <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
  <span>Refresh</span>
</button>

// REMOVE: lastUpdated state declaration (line 15)
const [lastUpdated, setLastUpdated] = useState(null);

// REMOVE: setLastUpdated(...) calls in loadCourseData (lines 54-58)
```

### Exact Lines to Remove — EnrollmentTracking.jsx

```jsx
// REMOVE: lines 97-105 — Refresh button in JSX
<button
  onClick={loadCourseData}
  disabled={loading}
  className="flex items-center gap-2 px-4 py-2 bg-blue-600 ..."
>
  <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
  Refresh
</button>

// REMOVE: lines 108-113 — lastUpdated and loadTime display
{lastUpdated && (
  <span>Last updated: {formatDateUtil(lastUpdated)}</span>
)}
{loadTime && (
  <span className="text-gray-500">Load time: {loadTime.toFixed(2)}s</span>
)}

// REMOVE: lastUpdated and loadTime state declarations and all setLoadTime/setLastUpdated calls
```

### Exact Lines to Remove — LateDaysTracking.jsx

```jsx
// REMOVE: lines 396-405 — loadTime and lastUpdated display in JSX
{loadTime && (
  <div className="flex items-center mt-1 text-xs text-green-600">
    ⚡ Loaded in {loadTime.toFixed(1)}s
  </div>
)}
{lastUpdated && (
  <div className="flex items-center mt-1 text-xs text-gray-500">
    🕒 Cached: {formatTime(lastUpdated)}
  </div>
)}

// REMOVE: loadTime and lastUpdated state declarations (lines 12, 16)
// REMOVE: setLoadTime and setLastUpdated calls in loadCourseData
```

### Exact Buttons to Remove — Settings.jsx

```jsx
// REMOVE: "Save & Sync Now" button (Course Configuration section, lines ~324-336)
<button
  onClick={saveAndSync}
  disabled={syncing || saving || !manualCourseId.trim()}
  className="px-4 py-2 bg-green-600 ..."
>
  ...
  Save & Sync Now
</button>

// REMOVE: "Sync Now" button (Sync Status section, lines ~343-354)
<button
  onClick={triggerSync}
  disabled={syncing || !settings.course_id}
  className="px-3 py-1.5 bg-blue-600 ..."
>
  ...
  Sync Now
</button>

// ALSO REMOVE in Settings.jsx:
// - syncing state variable (line 17)
// - triggerSync function (lines 90-110)
// - saveAndSync function (lines 113-116)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-page sync trigger + refresh button | Global header refresh with refreshTrigger prop | This phase | Single UX point for all syncs |
| Per-page "Last Updated" timestamp | Global header lastSyncedAt timestamp | This phase | Consistent timestamp always visible |
| Multiple sync entry points (header + Settings "Sync Now" + Settings "Save & Sync Now" + per-page Refresh) | Single entry point (header "Refresh Data") | This phase | Eliminates confusion about which sync button to use |

**Deprecated/removed:**
- `refreshData` function in EnhancedTADashboard: called `POST /api/canvas/sync` independently; replaced by refreshTrigger from header
- Settings "Sync Now" button: redundant with header; removed per CLEAN-01
- Settings "Save & Sync Now" button: replaced with "Save Settings" only per CLEAN-02
- Per-page load time / cached timestamp indicators: visual noise; removed per CLEAN-03/04/05

---

## Open Questions

1. **TAGradingDashboard reference in success criteria**
   - What we know: The file `canvas-react/src/TAGradingDashboard.jsx` does not exist. The ROADMAP success criterion lists it as one of the pages that should reload. Searching the directory confirms it is absent.
   - What's unclear: Was TAGradingDashboard removed in a previous phase, or is it a planned-but-not-yet-built page?
   - Recommendation: Planner should scope Phase 4 to the three existing dashboard pages (EnhancedTADashboard, LateDaysTracking, EnrollmentTracking). PeerReviewTracking is out of scope per REQUIREMENTS.md. If TAGradingDashboard is later added, the refreshTrigger prop pattern applies immediately.

2. **refreshTrigger initialization value when app loads**
   - What we know: React's useEffect fires on mount regardless of the refreshTrigger value. Pages already load data on mount from their `currentCourse` effect.
   - What's unclear: Should lastSyncedAt be initialized from the backend sync status on app load?
   - Recommendation: On app load, `lastSyncedAt` should be fetched from `/api/canvas/sync/status` in the same `loadSettings()` call, so the header shows the last sync time even before the user clicks Refresh. Add to `loadSettings`: fetch `syncData.last_sync.completed_at` and set `lastSyncedAt` if available.

---

## Validation Architecture

The config.json does not contain `workflow.nyquist_validation`, which means Nyquist validation is not enabled for this project. Skipping this section.

However, the project has Vitest configured and existing test files co-located with source files. Phase 4 changes should not break existing tests. The existing `EnhancedTADashboard.test.jsx` tests the component with `backendUrl` prop (note: this prop no longer exists in the component — test mocks `fetch` directly via `globalThis.fetch`). After removing `refreshData` and `lastUpdated`, the test at line 58 (`expect(screen.getByText(/TA Grading Dashboard/i))`) still passes. The Refresh button test does not exist, so no test deletion needed.

**Quick validation after each change:**
```bash
cd /Users/mapajr/git/cda-ta-dashboard/canvas-react && npm run test -- --run
```

---

## Sources

### Primary (HIGH confidence)

- Codebase read — `canvas-react/src/App.jsx`: confirmed current handleRefreshData structure, syncing state, existing props passed to pages
- Codebase read — `canvas-react/src/EnhancedTADashboard.jsx`: confirmed refreshData function, lastUpdated state, Refresh button, useEffect guard pattern
- Codebase read — `canvas-react/src/Settings.jsx`: confirmed triggerSync, saveAndSync, Sync Now button, Save & Sync Now button locations
- Codebase read — `canvas-react/src/LateDaysTracking.jsx`: confirmed loadTime/lastUpdated display (lines 396-405), ⚡/🕒 emoji indicators
- Codebase read — `canvas-react/src/EnrollmentTracking.jsx`: confirmed Refresh button, lastUpdated/loadTime display (lines 97-113)
- Codebase read — `.planning/STATE.md`: confirmed activeCourseId prop-drilling pattern as established convention for this codebase
- Codebase read — `.planning/REQUIREMENTS.md`: confirmed PeerReviewTracking is out of scope, TAGradingDashboard not mentioned as existing file
- Codebase read — `.planning/codebase/CONVENTIONS.md`: confirmed no barrel files, direct relative imports, camelCase handlers
- Codebase read — `.planning/codebase/TESTING.md`: confirmed Vitest setup, co-located test files, `npm run test` command

### Secondary (MEDIUM confidence)

- React 19 docs pattern: useEffect dependency array re-fires when any dependency changes — confirmed by project's existing useEffect patterns in codebase

### Tertiary (LOW confidence)

- None.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; existing stack confirmed from package.json
- Architecture: HIGH — refreshTrigger pattern confirmed as project convention from STATE.md; all file locations verified by direct code read
- Pitfalls: HIGH — all pitfalls identified by direct inspection of existing useEffect guards and ESLint configuration

**Research date:** 2026-02-28
**Valid until:** 2026-03-28 (stable — no external dependencies changing)
