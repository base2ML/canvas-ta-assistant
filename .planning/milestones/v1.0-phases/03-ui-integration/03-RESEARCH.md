# Phase 3: UI Integration - Research

**Researched:** 2026-02-17
**Domain:** React component authoring — SSE streaming, modal dialogs, form management, API integration
**Confidence:** HIGH

---

## Summary

Phase 3 integrates the backend posting and template infrastructure (Phases 1–2) into the React frontend. The work splits across two existing pages: **Settings.jsx** (add template management UI) and **LateDaysTracking.jsx** (add comment posting panel with selection, preview, confirmation, progress, history). No new routes or pages are required.

The technology stack is already fully present: React 19.1.1, Tailwind CSS v4, Lucide React icons, and a centralized `apiFetch` wrapper in `api.js`. The backend exposes all required endpoints: `GET/POST/PUT /api/templates`, `POST /api/comments/preview/:id`, `POST /api/comments/post/:id` (SSE stream), and `GET /api/comments/history`. No new npm packages are needed.

The most technically involved element is consuming the SSE bulk-posting stream (`/api/comments/post/:assignment_id`). The browser-native `EventSource` API cannot send POST bodies, so the correct approach is `fetch` with `ReadableStream` processing. A custom hook (`useSSEPost`) encapsulates the stream lifecycle and exposes progress state to the component. The pattern must handle cleanup on component unmount via `AbortController`. Everything else (modals, confirmation dialogs, history tables) is standard React state management with Tailwind.

**Primary recommendation:** Build five focused UI sections in sequence — template editor in Settings, posting panel in LateDaysTracking, preview modal, confirmation dialog, progress+history display — reusing existing component patterns from Settings.jsx and the Sync Status section as style guides.

---

## Standard Stack

### Core (already installed — zero new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19.1.1 | Component model, hooks | Already in project |
| Tailwind CSS | v4 | Utility-first styling | Already configured via `@tailwindcss/vite` |
| Lucide React | ^0.539.0 | Icons | Already used throughout (RefreshCw, CheckCircle, etc.) |
| React Router DOM | v7 | Routing | Already used; no new routes needed for this phase |
| Browser `fetch` + `ReadableStream` | Web standard | SSE POST streaming | No package needed; native API |
| Browser `EventSource` | Web standard | SSE GET streaming | Not usable here — POST body required |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `apiFetch` (internal) | — | JSON API calls | All non-SSE requests; already handles errors |
| `AbortController` | Web standard | Cancel in-flight fetch | Must use for SSE cleanup on unmount |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Native `fetch` + ReadableStream | `eventsource-parser` npm package | npm package adds parsing convenience but zero-dependency approach is simpler given the small event vocabulary (started, progress, posted, skipped, error, dry_run, complete, cancelled) |
| Modal via React state | React Portal or headless-ui | Portals solve z-index layering issues in complex apps; Tailwind fixed-position overlay with z-50 is sufficient here given the app has only one modal at a time |
| Inline form state | React Hook Form | Overkill for two textarea fields; plain useState is correct |

**Installation:** No new packages required.

---

## Architecture Patterns

### Recommended File Organization

The phase touches only these files:

```
canvas-react/src/
├── Settings.jsx                    # Add template management section
├── LateDaysTracking.jsx            # Add posting panel, preview, confirm, progress, history
├── hooks/
│   └── useSSEPost.js               # NEW: custom hook for SSE bulk posting stream
└── components/
    └── (existing components unchanged)
```

All UI additions are self-contained sections within the existing page components. No new top-level pages or routes.

### Pattern 1: Template Editor in Settings.jsx

**What:** Add a new card section below Sync History in Settings.jsx containing two labeled textarea fields — one for the penalty template, one for the non-penalty template — with a Save Templates button.

**When to use:** TMPL-06, CONF-03

**Data flow:**
1. On mount, `GET /api/templates` returns `{ templates: [...] }`. Filter for `template_type === 'penalty'` and `template_type === 'non_penalty'`. Pre-populate textarea values with `template_text`.
2. Save: `PUT /api/templates/:id` with `{ template_text: value }`. The backend validates syntax and returns 400 with error detail on invalid templates.
3. Display allowed variable names as a reference list below each textarea: `{days_late}`, `{days_remaining}`, `{penalty_days}`, `{penalty_percent}`, `{max_late_days}`.

**State:**
```javascript
const [penaltyTemplate, setPenaltyTemplate] = useState({ id: null, text: '' });
const [nonPenaltyTemplate, setNonPenaltyTemplate] = useState({ id: null, text: '' });
const [templateSaving, setTemplateSaving] = useState(false);
const [templateMessage, setTemplateMessage] = useState(null); // { type: 'success'|'error', text }
```

**Style guide:** Match existing card pattern from Settings.jsx lines 159–263:
```jsx
<div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
  <h2 className="text-lg font-semibold text-gray-900 mb-4">Comment Templates</h2>
  ...
</div>
```

**Pitfall — template_variables field:** The PUT endpoint accepts `template_variables` as an optional list. For this UI, omit it — the backend infers variables by test-rendering. Sending an explicit `template_variables: []` would clear the stored variables list. Send only `template_text` in the PUT body.

### Pattern 2: Posting Panel in LateDaysTracking.jsx

**What:** A collapsible panel added after the summary stats and before the table. The panel lets the TA:
- Select an assignment (dropdown from the existing `assignments` state)
- Select which students to post to (all with late days, filtered by TA group, or manually selected)
- Choose template type (penalty or non_penalty, or use the per-student logic)
- Launch preview workflow

**When to use:** POST-03, POST-04, POST-07, POST-08, POST-10, SAFE-04

**State additions to LateDaysTracking:**
```javascript
// Posting panel state
const [showPostingPanel, setShowPostingPanel] = useState(false);
const [postAssignmentId, setPostAssignmentId] = useState('');
const [selectedStudentIds, setSelectedStudentIds] = useState([]);
const [postTemplateType, setPostTemplateType] = useState('penalty');

// Preview modal state
const [showPreviewModal, setShowPreviewModal] = useState(false);
const [previewData, setPreviewData] = useState(null); // PreviewResponse shape
const [previewLoading, setPreviewLoading] = useState(false);
const [editedComments, setEditedComments] = useState({}); // { user_id: edited_text }

// Confirmation state
const [showConfirmDialog, setShowConfirmDialog] = useState(false);

// Progress state (SSE)
const [posting, setPosting] = useState(false);
const [postProgress, setPostProgress] = useState({ current: 0, total: 0 });
const [postResult, setPostResult] = useState(null); // complete event data

// History state
const [postingHistory, setPostingHistory] = useState([]);
const [historyLoading, setHistoryLoading] = useState(false);
```

**Student selection logic:** Pre-select all students with `total_late_days > 0` for the chosen assignment. Let the TA deselect individuals. The existing checkbox pattern from the Assignment Filter section (lines 313–347 of LateDaysTracking.jsx) is the direct style reference.

**Already-posted indicator (POST-10):** After loading history, build a Set of posted `user_id`s for the selected assignment. Render a small badge on the student row: `Already posted` in gray if in the set.

### Pattern 3: Preview Modal

**What:** A fixed full-screen overlay (z-50) showing a table of rendered comments per student before posting. Penalty cases show comment text. Non-penalty cases show a simpler message. Each row has an editable textarea for comment override (POST-08).

**Trigger:** After "Preview" button click → `POST /api/comments/preview/:assignment_id` with `{ course_id, template_type, user_ids }`.

**PreviewResponse shape** (from main.py `PreviewResponse` model):
```javascript
{
  assignment_id: number,
  assignment_name: string,
  template_id: number | null,
  previews: [{
    user_id: number,
    user_name: string,
    comment_text: string,
    already_posted: boolean,
    template_type: string | null,
    variables_used: { days_late, days_remaining, penalty_days, penalty_percent, max_late_days }
  }],
  total: number,
  already_posted_count: number
}
```

**Edit behavior (POST-08):** Each preview row includes a `<textarea>` initialized with `comment_text`. Changes are tracked in `editedComments` state keyed by `user_id`. When the user proceeds to Post, the edited text is sent as `override_comment` for that user. Since the backend bulk post endpoint takes one `override_comment` for all users, individual overrides require separate single-user calls OR the TA accepts that edits apply to all. **Resolution:** simplest approach for this phase — allow a single global `override_comment` textarea in the preview modal that replaces the template for ALL selected students. Individual per-row editing can be added in a future iteration. This matches the backend's existing `override_comment` field in `PostCommentsRequest`.

**SAFE-04 warning:** If `courseInfo` does not match `SANDBOX_COURSE_ID`, render a yellow warning banner in the preview modal:
```jsx
<div className="bg-yellow-50 border border-yellow-300 rounded p-3 mb-4 text-yellow-800">
  Warning: You are posting to a live production course. This will comment on real student submissions.
</div>
```

The Settings.jsx already returns `settings.sandbox_course_id` from `GET /api/settings`. The LateDaysTracking component receives `courses` prop which contains course id; compare to sandbox_course_id fetched from settings.

### Pattern 4: Confirmation Dialog

**What:** A small modal (or inline dialog) shown after the TA reviews the preview and clicks "Post Comments". Displays: course name, assignment name, student count, dry run status. Two buttons: Cancel and Confirm.

**POST-04 fields to display:**
- Course: `courseInfo.name`
- Assignment: `assignment.name` (from local `assignments` state)
- Students: `selectedStudentIds.length` (minus already_posted_count)
- Mode: dry run checkbox or indicator

**Implementation:** Render as a fixed overlay with a small centered card (z-60 to layer above preview modal if both are present, but simpler to close preview first). Pattern:
```jsx
<div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-60">
  <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
    ...
  </div>
</div>
```

### Pattern 5: SSE Progress Streaming

**What:** During bulk posting, show a progress bar/indicator "Posting X/Y comments..." and update it in real time via SSE events from `POST /api/comments/post/:assignment_id`.

**Critical:** The backend uses `POST` with a JSON body. The browser's native `EventSource` API only supports `GET` requests. Therefore, use `fetch` with `ReadableStream` for SSE consumption.

**Custom hook: `useSSEPost`**

Location: `canvas-react/src/hooks/useSSEPost.js`

```javascript
// Source: React docs pattern for external system synchronization + AbortController
import { useCallback, useRef } from 'react';
import { BACKEND_URL } from '../api';

export function useSSEPost() {
  const abortRef = useRef(null);

  const startPosting = useCallback(async (assignmentId, requestBody, handlers) => {
    // handlers: { onStarted, onProgress, onPosted, onSkipped, onError, onDryRun, onComplete, onCancelled }
    abortRef.current = new AbortController();
    const { signal } = abortRef.current;

    const response = await fetch(
      `${BACKEND_URL}/api/comments/post/${assignmentId}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
        signal,
      }
    );

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // Parse SSE lines: "event: name\ndata: json\n\n"
      const messages = buffer.split('\n\n');
      buffer = messages.pop(); // last partial chunk kept

      for (const message of messages) {
        const lines = message.split('\n');
        let eventType = 'message';
        let data = '';
        for (const line of lines) {
          if (line.startsWith('event: ')) eventType = line.slice(7).trim();
          if (line.startsWith('data: ')) data = line.slice(6).trim();
        }
        if (!data) continue;
        const parsed = JSON.parse(data);
        const handler = handlers[`on${eventType.charAt(0).toUpperCase() + eventType.slice(1)}`];
        if (handler) handler(parsed);
      }
    }
  }, []);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return { startPosting, cancel };
}
```

**Usage in LateDaysTracking:**
```javascript
const { startPosting, cancel } = useSSEPost();

const handlePost = async () => {
  setPosting(true);
  try {
    await startPosting(postAssignmentId, {
      course_id: currentCourse.id,
      template_type: postTemplateType,
      user_ids: selectedStudentIds,
      override_comment: globalOverride || null,
      dry_run: isDryRun,
    }, {
      onStarted: ({ total }) => setPostProgress({ current: 0, total }),
      onProgress: ({ current, total }) => setPostProgress({ current, total }),
      onPosted: () => {},
      onSkipped: () => {},
      onError: () => {},
      onComplete: (data) => { setPostResult(data); loadPostingHistory(); },
    });
  } catch (err) {
    setPostError(err.message);
  } finally {
    setPosting(false);
  }
};
```

**Cleanup on unmount:**
```javascript
useEffect(() => {
  return () => cancel();
}, [cancel]);
```

**Progress indicator JSX:**
```jsx
{posting && (
  <div className="flex items-center gap-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
    <RefreshCw className="w-4 h-4 animate-spin text-blue-600" />
    <span className="text-blue-800 font-medium">
      Posting {postProgress.current}/{postProgress.total} comments...
    </span>
    <button onClick={cancel} className="ml-auto text-sm text-red-600 hover:text-red-800">
      Cancel
    </button>
  </div>
)}
```

### Pattern 6: Posting History Table

**What:** After a successful post or on page load, fetch `GET /api/comments/history?course_id=:id&assignment_id=:id` and display results in a table below the posting panel.

**POST-09 fields:** user_id (or user_name if mapped from local users data), comment_text, posted_at (formatted), status badge (posted/failed/skipped).

**Load trigger:** On component mount and after each successful bulk post. Use `useCallback` + `useEffect` pattern matching existing `loadCourseData`.

**Status badges:**
```jsx
const statusBadge = (status) => ({
  posted: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  skipped: 'bg-gray-100 text-gray-700',
}[status] || 'bg-gray-100 text-gray-700');
```

**History response shape** (from `GET /api/comments/history`):
```javascript
{
  history: [{
    id, course_id, assignment_id, user_id, template_id,
    comment_text, canvas_comment_id, status, error_message,
    posted_at
  }],
  total: number
}
```

Map `user_id` to name using the existing `lateDaysData` array which already contains `student_id` and `student_name`.

### Anti-Patterns to Avoid

- **Using `EventSource` for SSE POST:** `EventSource` only supports GET. The backend requires POST with JSON body. Always use `fetch` + `ReadableStream`.
- **Fetching templates inside LateDaysTracking:** Templates are only needed in Settings. LateDaysTracking sends `template_type: 'penalty'|'non_penalty'` and the backend resolves the template. Do not fetch or store template text in LateDaysTracking.
- **Blocking UI during SSE stream:** The `startPosting` call is `async`/`await`. Keep `setPosting(true)` so the UI reflects streaming state. Do not use `syncing` state (that's for Canvas sync, not posting).
- **Calling `PUT /api/templates` with empty template_variables:** Send only `{ template_text: value }`. Sending `template_variables: []` clears the stored variable list unnecessarily — the backend already handles inferring variables from the text.
- **Not clearing `postResult` on new post attempt:** Reset `setPostResult(null)` at the start of each `handlePost` call to avoid showing stale results from the previous batch.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE event parsing | Custom regex parser | Simple `\n\n` split with `event:`/`data:` prefix stripping | The backend sends standard SSE format with a small fixed vocabulary of 8 event types. A 15-line parser is sufficient and correct. |
| Modal overlay | Third-party modal library | Tailwind `fixed inset-0 bg-black bg-opacity-50` + `z-50` | The app has zero third-party UI component dependencies; adding one for a single modal is not worth the dependency cost. |
| Template validation UI | Custom syntax highlighter | Single error message below textarea from API 400 response | The backend already validates templates with test-rendering. Surface the `detail` field from the 400 response. |
| Progress bar | `react-circular-progressbar` or similar | Inline "Posting X/Y" text with `animate-spin` icon | Matches the existing spinner pattern (RefreshCw with animate-spin is used in 4 places already). |
| Date formatting | date-fns or moment.js | `new Date(ts).toLocaleString()` | Already used in Settings.jsx line 298 for sync timestamps. |

**Key insight:** This phase is entirely additive UI composition over existing patterns. The existing codebase provides clear style precedent for every component type needed.

---

## Common Pitfalls

### Pitfall 1: SSE Stream Not Closed on Component Unmount

**What goes wrong:** The `fetch` + `ReadableStream` reader keeps consuming server data after the component unmounts, causing state updates on unmounted components and React warnings.

**Why it happens:** `ReadableStream.read()` is `await`-able in a loop; there is no automatic lifecycle connection to React's component tree.

**How to avoid:** Use `AbortController`. Pass `signal` to `fetch`. Call `abort()` in a `useEffect` cleanup function or on cancel button click. When aborted, `reader.read()` throws a `DOMException` with `name === 'AbortError'` — catch this specifically and treat it as a normal cancellation, not an error.

**Warning signs:** React DevTools console warning "Warning: Can't perform a React state update on an unmounted component."

### Pitfall 2: 403 from Preview/Post Because Test Mode Blocks Non-Sandbox Course

**What goes wrong:** The backend's `validate_posting_safety()` returns 403 when test mode is enabled and the configured course is not the sandbox course. The frontend shows no useful error.

**Why it happens:** The preview endpoint also enforces `validate_posting_safety()` (Phase 2 decision). The user may have test mode on without realizing.

**How to avoid:** Fetch current settings on mount in LateDaysTracking (or receive as a prop). If `settings.test_mode === true` and `currentCourse.id !== settings.sandbox_course_id`, show an inline warning banner before the preview button: "Test mode is active. Posting is only allowed to sandbox course." The API will reject the request anyway, but proactive UI guidance prevents confusion.

**Warning signs:** Preview button returns HTTP 403 with `detail` containing "Test mode is enabled."

### Pitfall 3: `already_posted` Users Counted in Progress Total

**What goes wrong:** The TA selects 30 students, 10 were already posted. The SSE stream shows "Posting 1/30" but only 20 actually get posted (10 are skipped as `already_posted`). The progress total is confusing.

**Why it happens:** `total` in the SSE `started` event equals `request_body.user_ids.length`, not the count of new posts.

**How to avoid:** Set `postProgress.total` from the `started` event data (which is the true total), and also track skipped count from `skipped` events. Update progress display to show "Posting 20 of 30 (10 skipped)." The `complete` event provides final `{ attempted, successful, failed, skipped }` for the summary.

### Pitfall 4: Template Textarea Loses Focus on Save

**What goes wrong:** Saving a template triggers a re-fetch that resets textarea value from state, which can cause the textarea to jump to a different scroll position or lose focus.

**Why it happens:** If `loadTemplates()` is called after save and sets state unconditionally, React re-renders the textarea.

**How to avoid:** After a successful PUT, update only the local state (`setPenaltyTemplate(prev => ({ ...prev, text: newText }))`), not via re-fetch. Only re-fetch on initial mount. The backend returns `{ status: 'success' }` on PUT — no re-fetch is needed.

### Pitfall 5: Settings Sandbox Course ID Not Available in LateDaysTracking

**What goes wrong:** SAFE-04 warning requires knowing the sandbox_course_id to compare against the current course. LateDaysTracking only receives `courses` and `onLoadCourses` as props.

**Why it happens:** `GET /api/settings` is only called in Settings.jsx today. LateDaysTracking is unaware of test mode or sandbox ID.

**How to avoid:** Add a small `GET /api/settings` fetch in LateDaysTracking's `useEffect` on mount, storing only `{ test_mode, sandbox_course_id }` in local state. Alternatively, elevate these two fields to App.jsx state and pass as props — but that changes more code. The local fetch approach is self-contained and matches how other pages handle their own data needs.

---

## Code Examples

Verified patterns from the existing codebase (HIGH confidence — read from actual source):

### Existing API Fetch Pattern (from api.js)

```javascript
// Source: /canvas-react/src/api.js
import { apiFetch } from './api';

// JSON POST request
const data = await apiFetch('/api/templates', {
  method: 'POST',
  body: JSON.stringify({ template_type: 'penalty', template_text: '...' }),
});

// GET with query params — apiFetch takes full path including params
const hist = await apiFetch(`/api/comments/history?course_id=${courseId}&assignment_id=${assignmentId}`);
```

### Existing Message Banner Pattern (from Settings.jsx lines 143–157)

```jsx
// Source: /canvas-react/src/Settings.jsx
{message && (
  <div className={`mb-6 p-4 rounded-lg flex items-center gap-2 ${
    message.type === 'success'
      ? 'bg-green-50 text-green-800 border border-green-200'
      : 'bg-red-50 text-red-800 border border-red-200'
  }`}>
    {message.type === 'success'
      ? <CheckCircle className="w-5 h-5" />
      : <XCircle className="w-5 h-5" />}
    {message.text}
  </div>
)}
```

### Existing Spinner Pattern (from Settings.jsx)

```jsx
// Source: /canvas-react/src/Settings.jsx line 272
<RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
```

### Existing Card Pattern (from Settings.jsx lines 159–160)

```jsx
// Source: /canvas-react/src/Settings.jsx
<div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
  <h2 className="text-lg font-semibold text-gray-900 mb-4">Section Title</h2>
  ...
</div>
```

### Existing Select/Checkbox Pattern (from LateDaysTracking.jsx lines 260–278)

```jsx
// Source: /canvas-react/src/LateDaysTracking.jsx
<select
  value={selectedTAGroup}
  onChange={(e) => handleTAGroupChange(e.target.value)}
  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
>
  <option value="">All TA Groups ({lateDaysData.length} students)</option>
  ...
</select>
```

### SSE Stream Parsing (Minimal, Correct)

```javascript
// Source: Pattern derived from MDN ReadableStream + SSE spec
const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = '';

try {
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split('\n\n');
    buffer = chunks.pop();
    for (const chunk of chunks) {
      let eventType = 'message', data = '';
      for (const line of chunk.split('\n')) {
        if (line.startsWith('event: ')) eventType = line.slice(7);
        if (line.startsWith('data: ')) data = line.slice(6);
      }
      if (data) handlers[eventType]?.(JSON.parse(data));
    }
  }
} catch (err) {
  if (err.name !== 'AbortError') throw err;
}
```

### Template API Calls

```javascript
// Load templates by type
const { templates } = await apiFetch('/api/templates?template_type=penalty');
const penaltyTpl = templates[0]; // { id, template_type, template_text, ... }

// Update template text only (do not send template_variables)
await apiFetch(`/api/templates/${penaltyTpl.id}`, {
  method: 'PUT',
  body: JSON.stringify({ template_text: newText }),
});

// Preview before posting
const preview = await apiFetch(`/api/comments/preview/${assignmentId}`, {
  method: 'POST',
  body: JSON.stringify({
    course_id: courseId,
    template_type: 'penalty',
    user_ids: [12345, 67890],
  }),
});
// preview.previews[].comment_text is the rendered template for each user

// Posting history
const { history } = await apiFetch(
  `/api/comments/history?course_id=${courseId}&assignment_id=${assignmentId}`
);
```

---

## Codebase Integration Notes

These are facts verified by reading the source files, not assumptions.

### Settings.jsx integration points

- The component manages its own state independently; no props are passed to it from App.jsx (`<Route path="/settings" element={<Settings />} />`).
- `loadSettings()` fetches from `GET /api/settings` which returns `{ test_mode, sandbox_course_id, max_late_days_per_assignment, ... }` (verified in main.py `SettingsResponse` model lines 105–113).
- The `SettingsUpdateRequest` model (main.py lines 115–128) accepts partial updates: only fields provided are updated. Frontend can send `{ template_text }` to PUT without affecting other fields.
- Add the template management card as the final section, after the Sync History card (line 324 of Settings.jsx).

### LateDaysTracking.jsx integration points

- Component receives `courses` (array) and `onLoadCourses` (function) as props. `currentCourse = courses[0]`.
- `lateDaysData` is already loaded and contains `{ student_id, student_name, student_email, ta_group_name, total_late_days, assignments: { [assignment_id]: days_late } }`.
- `assignments` state contains `{ id, name, due_at }` for all assignments.
- The posting panel should appear between the Assignment Filter section (line 350) and the Error Display (line 352). This keeps the data table below and ensures the posting panel is visible with the filter context.
- `sortedData` (the current filtered+sorted student list) is the correct source for student selection — it already respects the TA group filter and assignment filters.

### Backend API contract (verified from main.py)

| Endpoint | Method | Key Behavior |
|----------|--------|-------------|
| `GET /api/templates?template_type=penalty` | GET | Returns `{ templates: [{ id, template_type, template_text, template_variables, created_at, updated_at }] }` |
| `PUT /api/templates/:id` | PUT | Partial update; validates syntax; returns `{ status, message }` or 400 with `{ detail }` |
| `POST /api/comments/preview/:assignment_id` | POST | Body: `PostCommentsRequest`; enforces `validate_posting_safety()`; returns `PreviewResponse` |
| `GET /api/comments/history` | GET | Query params: `course_id`, optional `assignment_id`, `status`, `limit` (default 100) |
| `POST /api/comments/post/:assignment_id` | POST | Body: `PostCommentsRequest`; returns SSE stream; pre-flight 403/400/404 before stream starts |

SSE event types from the bulk post endpoint: `started`, `progress`, `posted`, `skipped`, `error`, `dry_run`, `complete`, `cancelled`. All `data` fields are JSON strings.

`PostCommentsRequest` shape (verified from main.py lines 235–248):
```javascript
{
  course_id: string,         // required
  template_id: number | null,
  template_type: string | null, // "penalty" or "non_penalty"
  user_ids: number[],        // required, non-empty
  override_comment: string | null,
  dry_run: boolean           // default false
}
```

Either `template_id` or `template_type` must be provided (or `override_comment`).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Class component lifecycle | Functional components + hooks | React 16.8 (2019) | Already using functional components throughout; no change needed |
| CSS modules / styled-components | Tailwind CSS v4 | This project from start | Already using; no conflict |
| `EventSource` for all SSE | `fetch` + `ReadableStream` for POST SSE | Web standards evolution | Required when SSE stream is triggered by POST; EventSource is GET-only |

**Deprecated/outdated in this context:**
- `EventSource`: Still valid for GET-triggered SSE, but inapplicable here since the post endpoint requires a POST body.
- Class-based modals (e.g., `ReactDOM.createPortal` required for old class pattern): With functional components and Tailwind's z-index utility classes, simple inline conditional rendering is sufficient for this single-modal use case.

---

## Open Questions

1. **Per-student comment editing scope**
   - What we know: POST-08 requires individual comment editing before posting. The backend `PostCommentsRequest` has one `override_comment` field for all users. Posting individual overrides requires either: (a) separate single-user POST calls, or (b) a `user_overrides: { [user_id]: text }` field not yet in the backend.
   - What's unclear: Whether POST-08 means one global override (simplest, already supported) or true per-student overrides.
   - Recommendation: Implement global `override_comment` in Phase 3 (one textarea in preview modal that replaces the template for all selected students). Document per-student editing as a future enhancement. The backend already supports `override_comment` so no backend changes are needed for the simple case.

2. **Test mode / sandbox_course_id availability in LateDaysTracking**
   - What we know: SAFE-04 requires a warning when posting to production. `sandbox_course_id` is only in `GET /api/settings`.
   - What's unclear: Whether to fetch settings in LateDaysTracking locally or lift the data to App.jsx.
   - Recommendation: Fetch settings locally in LateDaysTracking `useEffect`. This is self-contained, consistent with how other pages handle their own data, and avoids changing App.jsx props interface.

3. **Student `user_ids` are integers; `student_id` in `lateDaysData` is a string**
   - What we know: `lateDaysData[].student_id` is `str(user_id)` (main.py line 1532: `"student_id": str(user_id)`). The `PostCommentsRequest.user_ids` expects `list[int]`.
   - What's unclear: Will the frontend correctly convert.
   - Recommendation: Always `parseInt(student.student_id, 10)` when building the `user_ids` array for API calls.

---

## Sources

### Primary (HIGH confidence — read directly from source files)

- `/Users/mapajr/git/cda-ta-dashboard/main.py` — Verified all API endpoint signatures, Pydantic models, SSE event vocabulary, `PostCommentsRequest`, `PreviewResponse`, `SettingsResponse`
- `/Users/mapajr/git/cda-ta-dashboard/canvas-react/src/Settings.jsx` — Verified existing card/form/button/message patterns and state management approach
- `/Users/mapajr/git/cda-ta-dashboard/canvas-react/src/LateDaysTracking.jsx` — Verified existing data shape, component structure, insertion points for new UI
- `/Users/mapajr/git/cda-ta-dashboard/canvas-react/src/api.js` — Verified `apiFetch` interface and `BACKEND_URL` export
- `/Users/mapajr/git/cda-ta-dashboard/canvas-react/package.json` — Verified installed dependencies (no new packages needed)
- `/Users/mapajr/git/cda-ta-dashboard/canvas-react/src/App.jsx` — Verified routing structure, props passed to LateDaysTracking

### Secondary (HIGH confidence — official React docs via Context7)

- `/websites/react_dev` — `useEffect` cleanup pattern with `AbortController`, custom hook extraction pattern, dependency array rules

### Prior Research (HIGH confidence — from this project's research directory)

- `.planning/research/STACK.md` — Stack decisions verified; no new dependencies needed for UI phase
- `.planning/research/FEATURES.md` — Feature scope and MVP definition; confirms POST-08 individual editing is "high complexity" and acceptable as global override for v1

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — All libraries already installed; verified via package.json
- Architecture patterns: HIGH — Patterns derived directly from reading the actual source files
- SSE streaming: HIGH — Native Web API; React cleanup pattern verified via Context7
- Pitfalls: HIGH — Derived from API contract analysis and cross-component data flow inspection

**Research date:** 2026-02-17
**Valid until:** 2026-04-17 (stable stack; no fast-moving dependencies)
