---
phase: quick
plan: 2
type: execute
wave: 1
depends_on: []
files_modified:
  - canvas_sync.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "Browse Courses dropdown shows term name (e.g., 'Spring 2025') for each course"
    - "Course header displays term name after sync"
    - "course_term_{course_id} setting is written to SQLite after sync"
  artifacts:
    - path: "canvas_sync.py"
      provides: "Fixed sync_course_data with include=term, debug logging in fetch_available_courses"
      contains: "include=[\"term\"]"
  key_links:
    - from: "canvas_sync.sync_course_data"
      to: "canvas.get_course(course_id)"
      via: "include=[\"term\"] kwarg"
      pattern: "get_course.*include"
    - from: "canvas_sync.fetch_available_courses"
      to: "_get_term_name"
      via: "enrollment_term attribute on course object"
      pattern: "_get_term_name"
---

<objective>
Fix term information not appearing in the Browse Courses dropdown and course header.

Purpose: The Settings page Browse Courses dropdown shows courses without term names. The course header also lacks term info. Root cause: two separate bugs in canvas_sync.py prevent term data from being fetched or stored.

Output: canvas_sync.py with both bugs fixed so term names display correctly.
</objective>

<execution_context>
@/Users/mapajr/.claude/get-shit-done/workflows/execute-plan.md
@/Users/mapajr/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@canvas_sync.py
@canvas-react/src/Settings.jsx
</context>

## Research Findings

### Root Cause (Confirmed)

**Bug 1 — Missing `include=["term"]` in `sync_course_data` (PRIMARY)**

In `canvas_sync.py` line 207, `sync_course_data` calls:
```python
course = canvas.get_course(course_id)
```

This fetches the course object WITHOUT requesting term data. The Canvas API endpoint `GET /api/v1/courses/:id` does support `include[]=term` but it must be explicitly requested. Without it, the course object has no `enrollment_term` attribute.

As a result, `_get_term_name(course)` returns `None`, `course_term` is `None`, and the guard `if course_term:` on line 464 prevents `db.set_setting(f"course_term_{course_id}", ...)` from ever being written to SQLite.

The `/api/canvas/courses` endpoint reads `db.get_setting(f"course_term_{course_id}")` — which is always `None` — so the course header and any downstream display of term from the synced data shows nothing.

**Fix:** Change line 207 to:
```python
course = canvas.get_course(course_id, include=["term"])
```

**Bug 2 — No debug logging in `fetch_available_courses` (SECONDARY)**

`fetch_available_courses` does pass `include=["term"]` correctly (verified: `combine_kwargs` converts it to `include[]=term`). However, if term is still `None` from the Browse Courses path, there is no logging to diagnose whether the Canvas API returned `enrollment_term` or not.

**Fix:** Add a `logger.debug` line inside the course loop in `fetch_available_courses` to log the raw term value, making future diagnosis easier.

### Why `_get_term_name` Is Correct

The helper function handles both dict and CanvasObject forms of `enrollment_term`, and falls back to `term_name`. The logic is correct — the problem is purely that `get_course()` is never asked to include term data during sync.

### Canvas API Confirmation

The Canvas REST API docs confirm `include[]=term` is valid for both:
- `GET /api/v1/courses` (list) — returns `enrollment_term` nested object
- `GET /api/v1/courses/:id` (single) — same behavior

The `enrollment_term` object contains `{ id, name, start_at, end_at }`. The `name` field is what `_get_term_name` extracts.

<tasks>

<task type="auto">
  <name>Task 1: Fix sync_course_data to request term data and add diagnostic logging</name>
  <files>canvas_sync.py</files>
  <action>
Two changes to canvas_sync.py:

**Change 1 — Fix primary bug (line 207):**
Change:
```python
course = canvas.get_course(course_id)
```
To:
```python
course = canvas.get_course(course_id, include=["term"])
```
This ensures the Canvas API returns `enrollment_term` on the course object so `_get_term_name` can extract the term name and `sync_course_data` can store it in SQLite.

**Change 2 — Add diagnostic logging in `fetch_available_courses`:**
Inside the first `for course in canvas.get_courses(...)` loop, immediately after building the course dict and before `courses.append(...)`, add:
```python
logger.debug(
    f"Course {course_id}: name={getattr(course, 'name', None)!r}, "
    f"enrollment_term={getattr(course, 'enrollment_term', None)!r}, "
    f"term_name={getattr(course, 'term_name', None)!r}"
)
```
Add the same debug line inside the second `for course in canvas.get_courses(...)` loop (teacher enrollment). This helps diagnose if Canvas is not returning term data at all (e.g., course has no term set).

Do NOT change any other logic. Do NOT change `_get_term_name`. Do NOT change how `fetch_available_courses` calls `get_courses` (it already passes `include=["term"]` correctly).
  </action>
  <verify>
Run Ruff to confirm no lint errors:
```bash
uv run ruff check canvas_sync.py
uv run ruff format --check canvas_sync.py
```

Confirm the fix is present:
```bash
grep -n "get_course.*include" canvas_sync.py
```
Expected output: line showing `canvas.get_course(course_id, include=["term"])`.

Confirm debug logging added:
```bash
grep -n "enrollment_term" canvas_sync.py
```
Expected: _get_term_name body (existing) plus the new debug lines in fetch_available_courses.
  </verify>
  <done>
`canvas.get_course(course_id, include=["term"])` appears in sync_course_data. Debug logging for enrollment_term appears inside fetch_available_courses loops. Ruff passes with no errors.
  </done>
</task>

</tasks>

<verification>
After the fix, trigger a sync and verify term is stored:

1. Start the backend: `uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload`
2. Trigger sync: `curl -X POST http://localhost:8000/api/canvas/sync`
3. Check SQLite directly:
   ```bash
   sqlite3 ./data/canvas.db "SELECT key, value FROM settings WHERE key LIKE 'course_term_%';"
   ```
   Expected: row like `course_term_12345 | Spring 2025`
4. Fetch courses endpoint:
   ```bash
   curl http://localhost:8000/api/canvas/courses | python3 -m json.tool
   ```
   Expected: courses array with non-null `term` field.
5. In the UI, visit Settings and click Browse Courses — each course option should show term in the label if Canvas returns it.

If `course_term_*` is still null after sync, check the debug logs (`logs/app.log` or stdout) for the `enrollment_term` debug lines — if they show `enrollment_term=None`, the Canvas instance may not be associating courses with terms, which is a Canvas configuration issue (not a code bug).
</verification>

<success_criteria>
- `canvas.get_course(course_id, include=["term"])` is the call in sync_course_data
- After a sync, `sqlite3 data/canvas.db "SELECT * FROM settings WHERE key LIKE 'course_term_%'"` returns a non-empty row with an actual term name
- `/api/canvas/courses` returns courses with non-null `term` field
- Ruff lint passes on canvas_sync.py
</success_criteria>

<output>
After completion, create `.planning/quick/2-research-the-canvas-api-and-determine-wh/2-SUMMARY.md`
</output>
