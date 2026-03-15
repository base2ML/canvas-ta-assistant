# Phase 7: Add TA Grading Deadlines - Research

**Researched:** 2026-03-15
**Domain:** SQLite schema extension, FastAPI CRUD endpoints, React inline editing, deadline computation
**Confidence:** HIGH

## Summary

Phase 7 adds a grading deadline system layered on top of the Phase 6 grader identity infrastructure. Each assignment gets a grading deadline date computed from its `due_at` plus a configurable `default_grading_turnaround_days` offset. Per-assignment overrides can be stored in a `grading_deadlines` table. The backend computes overdue status per TA by joining grading deadline data against the existing submission grading state. The frontend adds inline deadline editing directly in the `AssignmentStatusBreakdown` component, overdue badges on each TA row, a Settings UI field for the default turnaround, and a read-only shareable Grading Schedule Summary view.

No new external libraries are required. All patterns follow the established project conventions: SQLite with `try/except sqlite3.OperationalError` migrations, `ON CONFLICT DO UPDATE` upserts, FastAPI Pydantic request/response models, and React functional components with Tailwind CSS v4 and Lucide React icons.

The most important design decision is the data model for `grading_deadlines`: it should key on `(course_id, assignment_id)` — one deadline row per assignment — and store the computed deadline as an explicit `TIMESTAMP` rather than deriving it at query time. This makes deadline editing, display, and overdue computation straightforward and avoids re-deriving values every request.

**Primary recommendation:** Implement in four plans: (1) DB schema + CRUD functions, (2) Backend endpoints + overdue computation logic, (3) Settings UI turnaround field + default propagation, (4) Dashboard inline editing + overdue badges + Grading Schedule Summary view.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sqlite3 (stdlib) | Python stdlib | grading_deadlines table, settings key | Already used throughout database.py |
| FastAPI | current (project) | CRUD endpoints for deadlines | Established project pattern |
| Pydantic | current (project) | Request/response validation for deadline models | Established project pattern |
| React 19.1.1 | 19.1.1 | Inline editing UI, summary view | Project frontend stack |
| Tailwind CSS v4 | v4 | Styling badges, editor UI | Project CSS framework |
| Lucide React | current | AlertTriangle / Clock / Edit icons for badges | Project icon library |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dateutil | current | Parse ISO timestamps for overdue computation | Already imported in main.py as `dateutil_parser` |
| datetime (stdlib) | Python stdlib | UTC-aware now() for overdue check | Already used project-wide |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Explicit deadline TIMESTAMP in DB | Compute due_at + offset at query time | Stored value survives due_at changes and makes override editing simple |
| Per-assignment-per-TA deadline rows | Single per-assignment deadline | Per-TA would add complexity; grading deadlines are per-assignment, not per-TA |
| Dedicated shareable URL with token | Read-only route in same React app | Token auth adds scope; read-only React route at `/grading-schedule` is enough for the use case |

**Installation:** No new packages needed.

## Architecture Patterns

### Recommended Project Structure Impact

```
database.py                    # Add grading_deadlines table + CRUD functions
main.py                        # Add Pydantic models + 4 new endpoints
canvas-react/src/
  Settings.jsx                 # Add default_grading_turnaround_days field
  EnhancedTADashboard.jsx      # Thread deadlines state down to breakdown
  components/
    AssignmentStatusBreakdown.jsx   # Inline deadline editor + overdue badges
    GradingScheduleSummary.jsx      # New read-only shareable view (new file)
App.jsx                        # Add /grading-schedule route
```

### Pattern 1: grading_deadlines Table Schema

**What:** One row per (course_id, assignment_id). Stores the effective deadline timestamp and whether it was manually overridden. `turnaround_days` stored for display.

**When to use:** Table keyed on `(course_id, assignment_id)` — same pattern as other per-course tables.

```python
# In database.py init_db(), after assignments table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS grading_deadlines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id TEXT NOT NULL,
        assignment_id INTEGER NOT NULL,
        deadline_at TIMESTAMP NOT NULL,
        turnaround_days INTEGER NOT NULL,
        is_override INTEGER DEFAULT 0,
        note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(course_id, assignment_id)
    )
""")
cursor.execute(
    "CREATE INDEX IF NOT EXISTS idx_grading_deadlines_course "
    "ON grading_deadlines(course_id)"
)
```

### Pattern 2: default_grading_turnaround_days Setting

**What:** Integer stored in the existing `settings` table under key `"default_grading_turnaround_days"`. Default: 7. Follows the same pattern as `total_late_day_bank`, `penalty_rate_per_day`, etc.

**When to use:** Scalar settings follow the `get_setting` / `set_setting` key-value pattern. No new table needed.

```python
# In get_settings() in main.py
turnaround_str = db.get_setting("default_grading_turnaround_days")
default_grading_turnaround_days = int(turnaround_str) if turnaround_str else 7

# In update_settings() in main.py
if settings.default_grading_turnaround_days is not None:
    db.set_setting(
        "default_grading_turnaround_days",
        str(settings.default_grading_turnaround_days),
    )
```

### Pattern 3: Upsert Grading Deadlines

**What:** Insert or update a grading deadline. Uses `ON CONFLICT(course_id, assignment_id) DO UPDATE` — identical to other upsert functions.

```python
# Source: database.py upsert patterns (e.g., upsert_users, record_comment_posting)
def upsert_grading_deadline(
    course_id: str,
    assignment_id: int,
    deadline_at: datetime,
    turnaround_days: int,
    is_override: bool = False,
    note: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Upsert a grading deadline for one assignment."""
    def _upsert(c: sqlite3.Connection) -> None:
        now = datetime.now(UTC)
        c.execute(
            """
            INSERT INTO grading_deadlines
                (course_id, assignment_id, deadline_at, turnaround_days,
                 is_override, note, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(course_id, assignment_id) DO UPDATE SET
                deadline_at   = excluded.deadline_at,
                turnaround_days = excluded.turnaround_days,
                is_override   = excluded.is_override,
                note          = excluded.note,
                updated_at    = excluded.updated_at
            """,
            (
                course_id, assignment_id,
                deadline_at.isoformat(), turnaround_days,
                1 if is_override else 0, note, now, now,
            ),
        )

    if conn is not None:
        _upsert(conn)
    else:
        with get_db_connection() as c:
            _upsert(c)
            c.commit()
```

### Pattern 4: Overdue Computation

**What:** Compute per-TA overdue status by joining deadlines with submission grading state. A TA's grading is "overdue" if `now > deadline_at` AND at least one submission for their assigned students is ungraded (submitted but not yet graded). Computed server-side so the frontend only needs to display badges.

**When to use:** In a new endpoint `/api/dashboard/grading-deadlines/{course_id}` that returns assignments with deadline info and per-TA overdue flags.

```python
# Source: Pattern mirrors get_ta_grading_data() in main.py
from datetime import UTC, datetime

def _is_overdue(deadline_at_str: str | None) -> bool:
    """Return True if deadline has passed."""
    if not deadline_at_str:
        return False
    try:
        deadline = dateutil_parser.parse(deadline_at_str)
        return datetime.now(UTC) > deadline
    except Exception:
        return False
```

### Pattern 5: Inline Deadline Editing in React

**What:** Per-assignment row in `AssignmentStatusBreakdown.jsx` gains an inline edit button. On click, shows a date input pre-populated with the current deadline. On save, calls `PUT /api/dashboard/grading-deadlines/{course_id}/{assignment_id}`. On cancel, restores previous value. Uses local React state — no new state management library.

**When to use:** Inline editing is appropriate here because it is a single field per row. The edit/view toggle follows the same pattern already used in other parts of the project (e.g., template editing in Settings.jsx).

```jsx
// Source: Project React pattern — useState for edit toggle
const [editingDeadlineId, setEditingDeadlineId] = useState(null);
const [editingDeadlineValue, setEditingDeadlineValue] = useState('');

// Inline editor in TA breakdown row:
{editingDeadlineId === assignment.assignment_id ? (
  <div className="flex items-center gap-1">
    <input
      type="date"
      className="text-xs border border-gray-300 rounded px-1"
      value={editingDeadlineValue}
      onChange={e => setEditingDeadlineValue(e.target.value)}
    />
    <button onClick={() => saveDeadline(assignment.assignment_id)}>Save</button>
    <button onClick={() => setEditingDeadlineId(null)}>Cancel</button>
  </div>
) : (
  <div className="flex items-center gap-1">
    <span className="text-xs">{formatDateUtil(assignment.grading_deadline)}</span>
    <button onClick={() => startEditDeadline(assignment)}>
      <Edit className="h-3 w-3" />
    </button>
  </div>
)}
```

### Pattern 6: Overdue Badge

**What:** Red badge shown on TA rows or assignment rows where grading is overdue. Follows the existing badge pattern in `AssignmentStatusBreakdown.jsx`.

```jsx
// Source: Project badge pattern — inline-flex px-2 py-1 rounded-full
{assignment.is_overdue && (
  <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
    <AlertTriangle className="h-3 w-3" />
    Overdue
  </span>
)}
```

### Pattern 7: Grading Schedule Summary View

**What:** A read-only React component accessible at `/grading-schedule`. Lists all assignments with their grading deadlines, TA assignments, completion status, and overdue flags. Shareable by copying the URL. Uses the same data from `/api/dashboard/grading-deadlines/{course_id}`.

**When to use:** New route added to `App.jsx` with `<Route path="/grading-schedule" element={<GradingScheduleSummary ... />} />`. Receives same `courses`, `activeCourseId`, `refreshTrigger` props as other dashboard pages.

### Anti-Patterns to Avoid

- **Computing deadline from due_at at query time:** This makes overrides impossible and forces re-computation every request. Always store the computed deadline in the DB.
- **Storing deadline as day offset only:** Storing only the offset instead of the resolved timestamp creates ambiguity when `due_at` is NULL or changes. Store both: the resolved timestamp AND the `turnaround_days` for display.
- **Adding a dedicated deadline fetch in each component:** Fetch deadlines once in `EnhancedTADashboard.jsx` and thread them down via props, the same way `taBreakdownMode` is threaded from `App.jsx`.
- **Inline editing without optimistic UI:** Show a loading state on save; revert on error. Don't leave the input open after a network failure.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UTC-aware datetime comparison | Custom timezone math | `datetime.now(UTC)` + `dateutil_parser.parse()` | Already used in main.py; handles timezone-aware ISO strings correctly |
| Upsert logic | Manual SELECT then INSERT/UPDATE | SQLite `ON CONFLICT DO UPDATE` | Already established pattern; atomic and correct |
| Date formatting in React | Custom formatter | `formatDateUtil` from `./utils/dates` | Already imported and used in AssignmentStatusBreakdown.jsx |
| Icon set | Custom SVG icons | Lucide React (`AlertTriangle`, `Edit`, `Clock`) | Project standard; already imported in AssignmentStatusBreakdown.jsx |

**Key insight:** The project's existing patterns (upsert, key-value settings, component prop-threading, UTC comparison) are sufficient for all deadline features. Nothing new needs to be invented.

## Common Pitfalls

### Pitfall 1: NULL due_at Assignments

**What goes wrong:** Assignments without a `due_at` cannot have a deadline computed from `due_at + turnaround_days`. If not handled, the deadline computation throws an exception or silently produces NULL.

**Why it happens:** Canvas allows assignments without due dates (e.g., extra-credit, unscheduled work). The project already accounts for this: `calculate_student_late_day_summary()` skips assignments with no `due_at`.

**How to avoid:** In the "propagate default deadlines" logic, skip assignments where `due_at IS NULL`. In the frontend, show "No deadline" for those rows instead of a date.

**Warning signs:** Deadline timestamps showing as epoch 0 or 1970 dates in the UI.

### Pitfall 2: Timezone-Naive Deadline Comparisons

**What goes wrong:** Comparing a timezone-aware `datetime.now(UTC)` against a stored timestamp that was serialized without timezone info causes a TypeError in Python.

**Why it happens:** SQLite stores timestamps as strings. If stored as `datetime.now(UTC).isoformat()` (which includes `+00:00`), `dateutil_parser.parse()` returns a timezone-aware object. If stored without timezone, the comparison fails.

**How to avoid:** Always store timestamps with UTC offset using `datetime.now(UTC).isoformat()`. Parse stored values with `dateutil_parser.parse()` which handles both aware and naive strings.

**Warning signs:** `TypeError: can't compare offset-naive and offset-aware datetimes` in backend logs.

### Pitfall 3: Inline Edit State Leaking Between Assignments

**What goes wrong:** If `editingDeadlineId` is stored at the parent component level (`EnhancedTADashboard`) but the edit input is rendered inside `AssignmentStatusBreakdown`, the state location matters. Moving between assignments without canceling leaves stale edit state open.

**Why it happens:** State mismatch between parent and child components for edit-in-place UX.

**How to avoid:** Store `editingDeadlineId` and `editingDeadlineValue` inside `AssignmentStatusBreakdown.jsx` (or inside the per-assignment `map()` callback using a sub-component). The edit is scoped to one assignment row.

**Warning signs:** Two assignment rows showing edit inputs simultaneously.

### Pitfall 4: Overdue Badge on Fully-Graded Assignments

**What goes wrong:** Showing an overdue badge on assignments where ALL submissions are already graded, even though the deadline has passed.

**Why it happens:** The overdue check is `now > deadline_at` without checking grading completion.

**How to avoid:** An assignment is overdue only if `now > deadline_at AND pending_submissions > 0`. A fully-graded assignment that is past its deadline is just "complete (late)" — show a neutral historical indicator if any, not a warning badge.

**Warning signs:** Overdue badges on green/100% complete assignment rows.

### Pitfall 5: Shareable View Requires Auth/Course Selection

**What goes wrong:** The Grading Schedule Summary at `/grading-schedule` tries to load data but has no course selected because it was opened via a shared URL in a fresh browser session.

**Why it happens:** `activeCourseId` comes from App.jsx state, which starts empty until settings are loaded.

**How to avoid:** The Summary view should load `activeCourseId` from the same `loadSettings()` call used by App.jsx, or accept a `?course_id=...` query param as a fallback. This is a single-user local app, so no auth is needed, but course selection must still happen. The simplest solution: fall back to the first available course if `activeCourseId` is not yet set.

**Warning signs:** Blank/loading state when opening `/grading-schedule` directly.

## Code Examples

Verified patterns from project source:

### Settings Key-Value Pattern (for default_grading_turnaround_days)

```python
# Source: main.py get_settings() lines 663-683
turnaround_str = db.get_setting("default_grading_turnaround_days")
default_grading_turnaround_days = int(turnaround_str) if turnaround_str else 7

# In SettingsResponse Pydantic model:
default_grading_turnaround_days: int = 7

# In SettingsUpdateRequest Pydantic model:
default_grading_turnaround_days: int | None = None

# In update_settings():
if settings.default_grading_turnaround_days is not None:
    db.set_setting(
        "default_grading_turnaround_days",
        str(settings.default_grading_turnaround_days),
    )
    updated_fields.append("default_grading_turnaround_days")
```

### Migration Pattern (try/except OperationalError)

```python
# Source: database.py lines 94-102, 175-188 — established project migration pattern
try:
    cursor.execute(
        "ALTER TABLE submissions ADD COLUMN grader_id INTEGER"
    )
    logger.info("Added grader_id column to submissions table")
except sqlite3.OperationalError:
    # Column already exists
    pass
```

### Overdue Status in API Response

```python
# Source: Pattern derived from get_ta_grading_data() in main.py lines 1799-1847
def _is_overdue(deadline_at_str: str | None, pending_count: int) -> bool:
    """True if deadline passed and submissions are still pending."""
    if not deadline_at_str or pending_count == 0:
        return False
    try:
        deadline = dateutil_parser.parse(deadline_at_str)
        return datetime.now(UTC) > deadline
    except Exception:
        return False
```

### React Inline Edit Toggle Pattern

```jsx
// Source: Project pattern from Settings.jsx saveTaSettings / edit flow
const [editingDeadlineId, setEditingDeadlineId] = useState(null);
const [editingValue, setEditingValue] = useState('');
const [saving, setSaving] = useState(false);

const handleSaveDeadline = async (courseId, assignmentId) => {
    setSaving(true);
    try {
        await apiFetch(`/api/dashboard/grading-deadlines/${courseId}/${assignmentId}`, {
            method: 'PUT',
            body: JSON.stringify({ deadline_date: editingValue, is_override: true }),
        });
        setEditingDeadlineId(null);
        onDeadlineSaved(); // callback to refresh parent data
    } catch (err) {
        console.error('Error saving deadline:', err);
    } finally {
        setSaving(false);
    }
};
```

### Auto-Populate Default Deadlines Endpoint

```python
# Source: Pattern derived from sync endpoint (main.py lines 813-851)
@app.post("/api/dashboard/grading-deadlines/{course_id}/propagate-defaults")
async def propagate_default_deadlines(course_id: str) -> dict[str, Any]:
    """Populate grading_deadlines for all assignments missing a deadline,
    using due_at + default_grading_turnaround_days. Skips assignments with no due_at.
    Does NOT overwrite is_override=1 rows."""
    turnaround_str = db.get_setting("default_grading_turnaround_days")
    turnaround_days = int(turnaround_str) if turnaround_str else 7
    assignments = db.get_assignments(course_id)
    created = 0
    for a in assignments:
        if not a.get("due_at"):
            continue
        try:
            due = dateutil_parser.parse(a["due_at"])
            deadline = due + timedelta(days=turnaround_days)
            db.upsert_grading_deadline_if_not_override(
                course_id, a["id"], deadline, turnaround_days
            )
            created += 1
        except Exception as e:
            logger.warning(f"Could not compute deadline for assignment {a['id']}: {e}")
    return {"propagated": created, "turnaround_days": turnaround_days}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Compute deadlines on the fly | Store explicit deadline timestamp | Phase 7 | Enables overrides without re-computation |
| No grading accountability | Overdue badges + schedule view | Phase 7 | TAs and instructors see grading urgency at a glance |

**Not applicable / no deprecated patterns** for this phase — it is net-new functionality.

## Open Questions

1. **Should propagate-defaults run automatically on sync, or manually via a button?**
   - What we know: Other auto-computations (late day summaries) happen on demand via API endpoints, not on sync.
   - What's unclear: Whether the user wants deadlines to auto-update when due dates change.
   - Recommendation: Add a "Propagate Default Deadlines" button in Settings. Do not auto-run on sync — explicit is safer. Manual overrides would be at risk if sync auto-propagated.

2. **Date only vs. datetime for grading deadlines?**
   - What we know: Assignment `due_at` is a full ISO datetime. Turnaround "days" suggests end-of-day (11:59 PM) semantics in practice.
   - What's unclear: Whether TAs care about time-of-day on the grading deadline.
   - Recommendation: Store as full TIMESTAMP derived from `due_at` + timedelta(days=N). The frontend date picker can use date-only input (`<input type="date">`), and the stored value will be interpreted as midnight UTC of that date when the user overrides it manually.

3. **Grading Schedule Summary: static HTML export vs. React route?**
   - What we know: The description says "shareable" — in a local single-user app, shareable means a URL anyone on the same machine (or LAN) can open.
   - What's unclear: Whether TAs need to share with people who don't have the app running.
   - Recommendation: React route at `/grading-schedule` is sufficient for the local deployment model. A "Copy Link" button satisfies the sharing requirement. Static HTML export is out of scope.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest (frontend) + pytest (backend) |
| Config file | `canvas-react/vitest.config.js` (frontend), `tests/conftest.py` (backend) |
| Quick run command (backend) | `uv run pytest tests/test_07_*.py -x` |
| Quick run command (frontend) | `cd canvas-react && npm run test -- --run` |
| Full suite command | `uv run pytest && cd canvas-react && npm run test -- --run` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEADLINE-DB-01 | `grading_deadlines` table created by `init_db()` with correct columns and UNIQUE constraint | unit | `uv run pytest tests/test_07_01_schema.py -x` | Wave 0 |
| DEADLINE-DB-02 | `upsert_grading_deadline()` inserts and updates on conflict; `is_override` flag preserved | unit | `uv run pytest tests/test_07_01_schema.py::TestUpsertGradingDeadline -x` | Wave 0 |
| DEADLINE-SETTINGS-01 | `default_grading_turnaround_days` persisted via `get_setting`/`set_setting`; defaults to 7 | unit | `uv run pytest tests/test_07_02_settings.py -x` | Wave 0 |
| DEADLINE-API-01 | `GET /api/dashboard/grading-deadlines/{course_id}` returns assignments with deadline and overdue flag | integration | `uv run pytest tests/test_07_02_api.py::TestGetDeadlines -x` | Wave 0 |
| DEADLINE-API-02 | `PUT /api/dashboard/grading-deadlines/{course_id}/{assignment_id}` updates deadline; sets `is_override=1` | integration | `uv run pytest tests/test_07_02_api.py::TestPutDeadline -x` | Wave 0 |
| DEADLINE-API-03 | `POST propagate-defaults` creates deadline rows for assignments with `due_at`; skips NULL `due_at`; skips `is_override=1` rows | integration | `uv run pytest tests/test_07_02_api.py::TestPropagateDefaults -x` | Wave 0 |
| DEADLINE-OVERDUE-01 | Overdue flag is `True` only when `now > deadline_at AND pending_submissions > 0` | unit | `uv run pytest tests/test_07_03_overdue.py -x` | Wave 0 |
| DEADLINE-UI-01 | Inline deadline editor renders date input on edit click; saves to API on save | component | `cd canvas-react && npm run test -- --run AssignmentStatusBreakdown` | Wave 0 |
| DEADLINE-UI-02 | Overdue badge renders when assignment has `is_overdue: true` and `pending_submissions > 0` | component | `cd canvas-react && npm run test -- --run AssignmentStatusBreakdown` | Wave 0 |
| DEADLINE-SUMMARY-01 | GradingScheduleSummary renders assignment list with deadline and overdue state | component | `cd canvas-react && npm run test -- --run GradingScheduleSummary` | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_07_*.py -x` (backend) or `cd canvas-react && npm run test -- --run` (frontend, relevant test file)
- **Per wave merge:** `uv run pytest && cd canvas-react && npm run test -- --run`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_07_01_schema.py` — covers DEADLINE-DB-01, DEADLINE-DB-02
- [ ] `tests/test_07_02_settings.py` — covers DEADLINE-SETTINGS-01
- [ ] `tests/test_07_02_api.py` — covers DEADLINE-API-01, DEADLINE-API-02, DEADLINE-API-03
- [ ] `tests/test_07_03_overdue.py` — covers DEADLINE-OVERDUE-01
- [ ] `canvas-react/src/components/GradingScheduleSummary.jsx` — new component (DEADLINE-SUMMARY-01)
- [ ] `canvas-react/src/components/GradingScheduleSummary.test.jsx` — covers DEADLINE-SUMMARY-01
- [ ] Updated `canvas-react/src/components/AssignmentStatusBreakdown.test.jsx` — covers DEADLINE-UI-01, DEADLINE-UI-02

## Sources

### Primary (HIGH confidence)

- Project source: `database.py` — all schema patterns, migration pattern, upsert patterns, `get_setting`/`set_setting` design
- Project source: `main.py` — all FastAPI endpoint patterns, Pydantic model patterns, settings update pattern, `get_ta_grading_data()` for overdue derivation
- Project source: `canvas-react/src/EnhancedTADashboard.jsx` — prop threading pattern, `loadCourseData()`, state management approach
- Project source: `canvas-react/src/components/AssignmentStatusBreakdown.jsx` — badge pattern, expand/collapse pattern, Lucide icon usage
- Project source: `canvas-react/src/Settings.jsx` — independent save button pattern, `apiFetch` usage, state management for settings sections
- Project source: `tests/test_06_01_schema.py` — established pytest test structure using `fresh_db` fixture with `monkeypatch`/`tmp_path`
- Project source: `.claude/skills/canvas-api-expert/SKILL.md` — canonical ETL and database patterns for this project

### Secondary (MEDIUM confidence)

- SQLite docs: `ON CONFLICT` clause behavior for UNIQUE constraints (https://sqlite.org/lang_conflict.html)
- FastAPI docs: `status.HTTP_*` constants and response model patterns

### Tertiary (LOW confidence)

- None — all findings are grounded in direct project source inspection.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use; no new dependencies
- Architecture: HIGH — all patterns directly derived from project source files read in this session
- Pitfalls: HIGH — derived from reading existing code and known SQLite/React gotchas already present in the codebase
- Test map: HIGH — follows exact test file naming and fixture pattern from Phase 06 tests

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable — no external library changes expected; project dependencies pinned)
