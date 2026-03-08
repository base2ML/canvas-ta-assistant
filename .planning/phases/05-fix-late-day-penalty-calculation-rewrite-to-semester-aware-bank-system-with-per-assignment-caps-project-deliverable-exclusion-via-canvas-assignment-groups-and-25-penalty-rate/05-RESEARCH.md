# Phase 5: Fix Late Day Penalty Calculation - Research

**Researched:** 2026-03-01
**Domain:** Python/FastAPI backend penalty algorithm + SQLite schema migration + React settings UI
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Semester bank
- Each student gets **10 late days total** across all assignments in the semester (configurable via `total_late_day_bank` setting, default 10)
- Bank is **per-course**, not cross-course
- Processing order: assignments sorted **chronologically by due date** — due date determines which assignment consumes bank days first (not submission date)

#### Per-assignment cap
- Max **7 late days** on any single assignment (configurable via `per_assignment_cap` setting, default 7)
- Caps the bank days that can be applied to a single assignment — prevents a student from spending all bank days on one assignment

#### Penalty calculation (two-pass per student)
**Pass 1 — Bank allocation (process all assignments for one student):**
1. Sort assignments by due date (ascending)
2. `bank_remaining = total_late_day_bank` (starts at 10)
3. For each assignment:
   - If not in `late_day_eligible_groups` → skip (project deliverable rules apply)
   - `applicable_late_days = min(days_late, per_assignment_cap)`
   - `bank_days_used = min(applicable_late_days, bank_remaining)`
   - `penalty_days = days_late - bank_days_used`  ← days beyond what bank covers
   - `penalty_percent = min(penalty_days × 25, 100)`  ← 25% per penalty day, capped at 100%
   - `bank_remaining -= bank_days_used`  ← bank days deduct; penalty days do NOT deduct again

**Pass 2 — Comment rendering (single assignment lookup):**
- Pre-computed values from Pass 1 used for template rendering

#### Penalty rate
- **25% of earned grade per penalty day** (not 10% as currently implemented)
- Capped at 100% (zero grade)
- Only applies to days BEYOND what the bank covers (days within bank = no penalty)

#### Project deliverable exclusion
- Project deliverables identified by **Canvas assignment group** — head TA selects in Settings which groups allow late submissions (`late_day_eligible_groups` = JSON array of assignment group IDs)
- Assignments in groups NOT in `late_day_eligible_groups` are treated as project deliverables
- Project deliverable submitted late: status = **"Not Accepted"**, zero grade, NO bank days consumed

#### Example calculations (from todo — planner must match these)
- Student 9 days late, full 10-day bank: 7 bank days used (capped), 2 penalty days → 50% penalty, bank now 3
- Student 3 days late, 1 bank day left: 1 bank day used, 2 penalty days → 50% penalty, bank now 0
- Project deliverable 2 days late: "Not Accepted", zero grade, bank unchanged

#### New settings
- `total_late_day_bank` — integer, default 10
- `penalty_rate_per_day` — integer (%), default 25
- `per_assignment_cap` — integer, default 7 (replaces `max_late_days_per_assignment`)
- `late_day_eligible_groups` — JSON array of Canvas assignment group IDs that allow late submissions

#### Database changes
- New `assignment_groups` table: id, course_id, name
- Add `assignment_group_id` column to `assignments` table

#### Canvas sync changes
- Sync assignment groups via `course.get_assignment_groups()` in canvas_sync.py
- Store `assignment_group_id` on each assignment during sync

#### Template variable changes
New/changed template variables available for comment templates:
- `bank_days_used` (new) — days covered by bank, no penalty
- `bank_remaining` (new) — student's remaining bank days after this assignment
- `total_bank` (new) — total semester bank size
- `penalty_days` — days beyond bank (these incur penalty)
- `penalty_percent` — now calculated at 25%/day
- Existing `days_late`, `max_late_days` still present

Default comment templates should be updated to reflect the corrected policy language.

### Claude's Discretion
- Exact UI layout of "Late Day Policy" section in Settings.jsx
- Visual design for bank vs penalty day differentiation in LateDaysTracking.jsx (colors, labels)
- How "Not Accepted" is visually rendered in the table
- Migration/transition behavior for existing `max_late_days_per_assignment` setting

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

This phase rewrites the core late day penalty algorithm from a per-assignment cap model (10% per day, no semester tracking) to a semester-aware bank system. The existing `calculate_late_days_for_user()` function in main.py handles only a single assignment in isolation; the new `calculate_student_late_day_summary()` must process all assignments for a student in one pass, maintaining a running bank balance sorted by assignment due date.

The data model requires two additions: a new `assignment_groups` table (synced from Canvas) and an `assignment_group_id` column on `assignments`. These enable the eligibility check that distinguishes bank-eligible assignments from project deliverables. The settings layer gains four new keys (`total_late_day_bank`, `penalty_rate_per_day`, `per_assignment_cap`, `late_day_eligible_groups`), replacing the existing `max_late_days_per_assignment`. The comment posting flow must be updated to source pre-computed bank values rather than calling the per-assignment function inline.

The Canvas `canvasapi` library exposes `course.get_assignment_groups()` returning a `PaginatedList` of `AssignmentGroup` objects; each group has `id`, `name`, and `position` fields. The project's existing skill patterns (upsert with `ON CONFLICT`, `get_db_transaction()` context manager, `getattr()` for safe attribute access, Loguru logging, Pydantic model extension) apply directly to all new code.

**Primary recommendation:** Implement in four sequential concerns — (1) DB schema migration, (2) canvas_sync addition, (3) backend algorithm + API rewrite, (4) frontend Settings + LateDaysTracking updates.

---

## Standard Stack

### Core (all already in use — no new dependencies needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | >=0.104.0 | REST API + Pydantic integration | Project standard |
| Pydantic v2 | >=2.0.0 | Settings request/response models | Project standard |
| SQLite (stdlib) | — | Schema migration via `ALTER TABLE`, new `CREATE TABLE` | Project standard |
| canvasapi | >=3.0.0 | `course.get_assignment_groups()` Canvas API call | Project standard; canvas-api-expert skill |
| python-dateutil | >=2.8.0 | Parse `due_at` ISO strings for chronological sort | Already used in `calculate_late_days_for_user()` |
| Loguru | >=0.7.3 | All logging (never `print`) | Project standard |
| React 19 + Tailwind CSS v4 | — | Settings.jsx new section + LateDaysTracking.jsx new columns | Project standard |
| Lucide React | — | Icons for new UI | Project standard |

### No New Packages Required

This phase is purely logic/data changes within the existing stack. No new `pip install` or `npm install` needed.

---

## Architecture Patterns

### Recommended File Change Map

```
main.py
├── ALLOWED_TEMPLATE_VARIABLES     # add: bank_days_used, bank_remaining, total_bank
├── SettingsResponse               # add: total_late_day_bank, penalty_rate_per_day,
│                                  #       per_assignment_cap, late_day_eligible_groups
├── SettingsUpdateRequest          # add same 4 fields; keep max_late_days_per_assignment
│                                  #   for backward compat (read-only migration)
├── calculate_late_days_for_user() # REPLACE with calculate_student_late_day_summary()
│                                  #   returns {user_id: {assignment_id: {bank_days_used,
│                                  #   bank_remaining, penalty_days, penalty_percent,
│                                  #   days_late, not_accepted}}}
├── get_late_days_data()           # UPDATE to call new function, return new fields
├── get_settings()                 # UPDATE to read 4 new setting keys
├── update_settings()              # UPDATE to write 4 new setting keys
└── post_comments streaming loop   # UPDATE: replace per-user calculate_late_days_for_user()
    (line ~1032)                   #   call with lookup into pre-computed bank summary

database.py
├── init_db()                      # ADD: assignment_groups table + migration for
│                                  #   assignment_group_id column on assignments
├── upsert_assignment_groups()     # NEW: mirrors upsert_assignments() pattern
└── upsert_assignments()           # EXTEND: include assignment_group_id in INSERT/UPDATE

canvas_sync.py
└── sync_course_data()             # ADD: fetch assignment groups + store group IDs
                                   #   on assignments before upsert

canvas-react/src/Settings.jsx
└── (new section)                  # "Late Day Policy" — 4 new configurable fields
                                   #   + assignment group multi-select

canvas-react/src/LateDaysTracking.jsx
└── (update table)                 # new columns: bank used, bank remaining, penalty;
                                   #   "Not Accepted" badge for project deliverables
```

### Pattern 1: Two-Pass Semester Bank Algorithm

**What:** Process all assignments for one student chronologically, maintaining `bank_remaining`. Return a per-assignment dict that callers can look up by `(user_id, assignment_id)`.

**When to use:** Called once per student per API request in `get_late_days_data()`, and once globally before the SSE comment posting loop.

**Implementation:**

```python
# Source: derived from existing calculate_late_days_for_user() in main.py
# and CONTEXT.md algorithm specification

def calculate_student_late_day_summary(
    user_id: int,
    assignments: list[dict[str, Any]],          # all assignments for course
    submissions: list[dict[str, Any]],           # all submissions for user
    total_late_day_bank: int,
    per_assignment_cap: int,
    penalty_rate_per_day: int,
    late_day_eligible_group_ids: set[int],       # set of eligible assignment_group_ids
) -> dict[int, dict[str, Any]]:
    """
    Returns: {assignment_id: {
        "days_late": int,
        "bank_days_used": int,
        "bank_remaining": int,     # after this assignment
        "penalty_days": int,
        "penalty_percent": int,
        "not_accepted": bool,      # True for project deliverables submitted late
        "total_bank": int,
    }}
    """
    # Build submission lookup for this user
    sub_lookup = {
        s["assignment_id"]: s for s in submissions
        if s.get("user_id") == user_id
    }

    # Sort assignments chronologically by due_at — assignments with no due_at skipped
    sorted_assignments = sorted(
        [a for a in assignments if a.get("due_at")],
        key=lambda a: dateutil_parser.parse(a["due_at"])
    )

    bank_remaining = total_late_day_bank
    result: dict[int, dict[str, Any]] = {}

    for assignment in sorted_assignments:
        assignment_id = assignment["id"]
        due_at = assignment["due_at"]
        group_id = assignment.get("assignment_group_id")
        is_eligible = group_id in late_day_eligible_group_ids

        sub = sub_lookup.get(assignment_id)
        days_late = _compute_days_late(sub, due_at)  # reuse grace period logic

        if days_late == 0:
            # On-time or no submission — no bank impact
            result[assignment_id] = {
                "days_late": 0, "bank_days_used": 0,
                "bank_remaining": bank_remaining,
                "penalty_days": 0, "penalty_percent": 0,
                "not_accepted": False, "total_bank": total_late_day_bank,
            }
            continue

        if not is_eligible:
            # Project deliverable submitted late — Not Accepted, no bank consumed
            result[assignment_id] = {
                "days_late": days_late, "bank_days_used": 0,
                "bank_remaining": bank_remaining,
                "penalty_days": days_late, "penalty_percent": 100,
                "not_accepted": True, "total_bank": total_late_day_bank,
            }
            continue

        # Bank-eligible late submission
        applicable_late_days = min(days_late, per_assignment_cap)
        bank_days_used = min(applicable_late_days, bank_remaining)
        penalty_days = days_late - bank_days_used
        penalty_percent = min(penalty_days * penalty_rate_per_day, 100)
        bank_remaining -= bank_days_used

        result[assignment_id] = {
            "days_late": days_late,
            "bank_days_used": bank_days_used,
            "bank_remaining": bank_remaining,
            "penalty_days": penalty_days,
            "penalty_percent": penalty_percent,
            "not_accepted": False,
            "total_bank": total_late_day_bank,
        }

    return result
```

### Pattern 2: SQLite Schema Migration (Add Column to Existing Table)

**What:** Use `ALTER TABLE ... ADD COLUMN` inside `init_db()` wrapped in `try/except sqlite3.OperationalError` — the established migration pattern in this codebase.

**When to use:** Adding `assignment_group_id` to the existing `assignments` table.

```python
# Source: database.py lines 91-98 — established pattern for migrations
try:
    cursor.execute(
        "ALTER TABLE assignments ADD COLUMN assignment_group_id INTEGER"
    )
    logger.info("Added assignment_group_id column to assignments table")
except sqlite3.OperationalError:
    # Column already exists
    pass
```

### Pattern 3: New Table + Upsert (assignment_groups)

**What:** Mirror the existing `upsert_assignments()` pattern exactly.

```python
# New table in init_db():
cursor.execute("""
    CREATE TABLE IF NOT EXISTS assignment_groups (
        id INTEGER PRIMARY KEY,
        course_id TEXT NOT NULL,
        name TEXT NOT NULL,
        position INTEGER,
        synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
cursor.execute(
    "CREATE INDEX IF NOT EXISTS idx_assignment_groups_course "
    "ON assignment_groups(course_id)"
)

# New upsert function in database.py:
def upsert_assignment_groups(
    course_id: str,
    groups: list[dict[str, Any]],
    conn: sqlite3.Connection | None = None,
) -> int:
    def _upsert(db_conn: sqlite3.Connection) -> int:
        cursor = db_conn.cursor()
        synced_at = datetime.now(UTC)
        data = [
            (g["id"], course_id, g["name"], g.get("position"), synced_at)
            for g in groups
        ]
        cursor.executemany(
            """
            INSERT INTO assignment_groups (id, course_id, name, position, synced_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                course_id = excluded.course_id,
                name = excluded.name,
                position = excluded.position,
                synced_at = excluded.synced_at
            """,
            data,
        )
        if conn is None:
            db_conn.commit()
        return len(groups)
    if conn is not None:
        return _upsert(conn)
    else:
        with get_db_connection() as db_conn:
            return _upsert(db_conn)
```

### Pattern 4: Canvas API — Fetch Assignment Groups

**What:** Use `course.get_assignment_groups()` via canvasapi. Returns `PaginatedList[AssignmentGroup]` where each object has `id`, `name`, `position`.

**Verified fields** (Canvas REST API docs — HIGH confidence):
- `assignment_group.id` — Canvas group ID
- `assignment_group.name` — group name (e.g., "Homework", "Projects")
- `assignment_group.position` — ordering position (integer)

**Important:** Assignment groups from Canvas are course-level categories (like "Homework", "Projects") — **not** the TA grading groups from `course.get_groups()`. These are structurally distinct.

```python
# Source: canvas_sync.py established patterns + canvasapi docs
# In sync_course_data(), after fetching assignments:

assignment_groups_data = []
for ag in course.get_assignment_groups():
    assignment_groups_data.append({
        "id": ag.id,
        "name": getattr(ag, "name", f"Group {ag.id}"),
        "position": getattr(ag, "position", None),
    })

# Annotate each assignment with its group_id
assignment_group_id_map = {ag["id"]: ag["id"] for ag in assignment_groups_data}
for assignment_obj, assignment_data in zip(assignment_objects, assignments, strict=True):
    assignment_data["assignment_group_id"] = getattr(
        assignment_obj, "assignment_group_id", None
    )
```

**Note:** The `assignment_group_id` field is already present on Canvas assignment objects (`assignment.assignment_group_id`). It does not require a separate API call to resolve.

### Pattern 5: Settings Keys via get_setting() / set_setting()

**What:** The four new settings follow the existing `get_setting` / `set_setting` key-value pattern.

```python
# Reading in get_settings():
total_bank_str = db.get_setting("total_late_day_bank")
total_bank = int(total_bank_str) if total_bank_str else 10

penalty_rate_str = db.get_setting("penalty_rate_per_day")
penalty_rate = int(penalty_rate_str) if penalty_rate_str else 25

per_cap_str = db.get_setting("per_assignment_cap")
per_cap = int(per_cap_str) if per_cap_str else 7

eligible_str = db.get_setting("late_day_eligible_groups")
eligible_groups = json.loads(eligible_str) if eligible_str else []

# Writing in update_settings():
if settings.total_late_day_bank is not None:
    db.set_setting("total_late_day_bank", str(settings.total_late_day_bank))
# ... pattern repeats for each key
# late_day_eligible_groups stored as JSON: json.dumps(settings.late_day_eligible_groups)
```

### Pattern 6: Comment Posting Flow — Pre-Compute and Lookup

**What:** The SSE streaming loop (main.py ~line 1032) currently calls `calculate_late_days_for_user()` per student. Replace with a pre-computed lookup built once before the loop.

```python
# Before the per-user SSE loop (outside the generator):
# 1. Fetch all settings once
total_bank = int(db.get_setting("total_late_day_bank") or 10)
per_cap = int(db.get_setting("per_assignment_cap") or 7)
penalty_rate = int(db.get_setting("penalty_rate_per_day") or 25)
eligible_str = db.get_setting("late_day_eligible_groups")
eligible_set = set(json.loads(eligible_str)) if eligible_str else set()

# 2. Pre-compute bank summary for all requested users
bank_summaries: dict[int, dict[int, dict]] = {}
for uid in request.user_ids:
    user_subs = [s for s in submissions if s.get("user_id") == uid]
    bank_summaries[uid] = calculate_student_late_day_summary(
        uid, assignments, user_subs,
        total_bank, per_cap, penalty_rate, eligible_set
    )

# 3. Inside the loop, look up pre-computed values:
late_days_data = bank_summaries[user_id].get(assignment_id, default_dict)
```

### Pattern 7: ALLOWED_TEMPLATE_VARIABLES Extension

**What:** The `ALLOWED_TEMPLATE_VARIABLES` set in main.py must be extended. Template validation in `validate_template_syntax()` and `render_template()` both check against this set.

```python
ALLOWED_TEMPLATE_VARIABLES = {
    # Existing (kept for backward compatibility)
    "days_late",
    "days_remaining",    # keep as alias for bank_remaining
    "penalty_days",
    "penalty_percent",
    "max_late_days",     # keep as alias for per_assignment_cap
    # New
    "bank_days_used",
    "bank_remaining",
    "total_bank",
}
```

**Note:** `days_remaining` and `max_late_days` must remain for backward compatibility with any saved templates. Map them to new values: `days_remaining = bank_remaining`, `max_late_days = per_assignment_cap`.

### Anti-Patterns to Avoid

- **Per-assignment calculation inside the posting loop:** The old `calculate_late_days_for_user()` call at line 1032 is a single-assignment function. Calling it per iteration is now semantically wrong because bank state depends on prior assignments. Pre-compute the full student summary before the loop.
- **Calling `calculate_student_late_day_summary()` with all submissions (not filtered by user):** The function accepts all submissions for efficiency, but the internal lookup must filter by `user_id`. Passing unsorted, unfiltered data is fine — the function handles it.
- **Not including `late_day_eligible_groups` in the clear_refreshable_data path:** Assignment groups are course data that changes with sync. They belong in `clear_refreshable_data()`, not just `clear_course_data()`.
- **Treating `assignment_group_id` (Canvas category) as TA group (course.get_groups()):** These are entirely different Canvas objects. Assignment groups are syllabus categories; TA groups are student groupings for grading. Never conflate them.
- **Forgetting to clear assignment_groups in clear_refreshable_data():** Since this is refreshable data, it must be cleared and re-fetched on each sync.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ISO 8601 datetime parsing | Custom regex or strptime | `dateutil_parser.parse()` | Already used in `calculate_late_days_for_user()`; handles timezone variations in Canvas dates |
| Assignment group fetch | Raw httpx REST call | `course.get_assignment_groups()` via canvasapi | Handles pagination, auth, retry via project's `get_canvas_client()` |
| JSON storage for eligible groups list | Custom serialization | `json.dumps()` / `json.loads()` | Already pattern for `template_variables` field in comment_templates table |
| SQLite migration safety | `IF NOT EXISTS` workaround | `try/except sqlite3.OperationalError` | Established pattern in database.py lines 91-98 |
| Chronological sort of assignments | Manual date comparison | `sorted(..., key=lambda a: dateutil_parser.parse(a["due_at"]))` | Built on existing `dateutil_parser` import |

**Key insight:** This phase is almost entirely algorithmic — the infrastructure (DB layer, Canvas sync pipeline, settings pattern, Pydantic models, template rendering) all exists. The work is wiring new logic into established slots.

---

## Common Pitfalls

### Pitfall 1: assignment_group_id Is Already on Assignment Objects

**What goes wrong:** Developer adds a separate `get_assignment_groups()` call to retrieve group IDs, then tries to join them to assignments by assignment listing. Wasted API calls.

**Why it happens:** The Canvas REST API AssignmentGroup endpoint lists groups; the Canvas Assignment object already carries `assignment_group_id` as a direct attribute.

**How to avoid:** Access `getattr(assignment_obj, "assignment_group_id", None)` directly on the assignment object during the existing assignment fetch loop. The separate `get_assignment_groups()` call is only needed to populate the `assignment_groups` table with names for the Settings UI dropdown.

**Warning signs:** Any code that iterates `assignment_groups` to look up IDs by joining against assignments.

### Pitfall 2: Bank Deduction Order Follows Due Date, Not Submission Date

**What goes wrong:** Sorting assignments by `submitted_at` instead of `due_at`. A student who submits Assignment B before Assignment A (both late) should still have Assignment A's bank deducted first if Assignment A was due first.

**Why it happens:** "Chronological" is ambiguous without the spec.

**How to avoid:** Sort by `due_at` ascending (CONTEXT.md is explicit). Assignments with no `due_at` are excluded from late day calculation entirely.

**Warning signs:** Sorting key references `submission.get("submitted_at")` instead of `assignment.get("due_at")`.

### Pitfall 3: `penalty_days` vs `bank_days_used` in Template Rendering

**What goes wrong:** Using `days_late` as `penalty_days` in the template (the old model). In the new model, `penalty_days = days_late - bank_days_used`. A student 5 days late with 5 bank days left has 0 penalty days.

**Why it happens:** The variable names look similar to the old model.

**How to avoid:** The render_template context dict must use values from the new `calculate_student_late_day_summary()` result, not recompute them.

**Warning signs:** Template preview shows `penalty_percent > 0` for a student fully covered by their bank.

### Pitfall 4: Migration of `max_late_days_per_assignment` Setting

**What goes wrong:** Removing `max_late_days_per_assignment` from the Pydantic models and database reads breaks existing deployments that have the setting stored in SQLite.

**Why it happens:** CONTEXT.md says `per_assignment_cap` replaces `max_late_days_per_assignment`.

**How to avoid (Claude's Discretion):** Keep `max_late_days_per_assignment` in `SettingsUpdateRequest` but mark it deprecated (or simply ignore new writes). On read, if `per_assignment_cap` is not set, fall back to `max_late_days_per_assignment` value. This is zero-downtime migration. Alternative: write `per_assignment_cap` from existing `max_late_days_per_assignment` value during first `init_db()` run after upgrade.

**Warning signs:** Existing users see `per_assignment_cap = 7` (default) instead of their custom value after upgrade.

### Pitfall 5: Project Deliverable "Not Accepted" in Comment Template Rendering

**What goes wrong:** Calling `render_template()` with the penalty template for a "Not Accepted" project deliverable — the template variables would show `penalty_days = days_late` and `penalty_percent = 100`, which is misleading. The correct behavior is to use a distinct comment path or skip template rendering.

**Why it happens:** The comment posting flow doesn't have a "Not Accepted" branch — it just uses penalty vs non-penalty template type.

**How to avoid:** In the SSE posting loop, check `late_days_data["not_accepted"]` before template selection. If `True`, either skip posting (Not Accepted students may not need a bank comment) or use special handling. This is partially Claude's Discretion — the CONTEXT.md doesn't specify whether comments are posted for project deliverables.

**Warning signs:** Students with "Not Accepted" project deliverables receive confusing "50% penalty" comments.

### Pitfall 6: clear_refreshable_data() Missing assignment_groups

**What goes wrong:** `assignment_groups` table accumulates stale entries across syncs because it is not cleared in `clear_refreshable_data()`.

**Why it happens:** `clear_refreshable_data()` currently clears peer reviews, groups, and assignments but `assignment_groups` is a new table not yet listed.

**How to avoid:** Add `DELETE FROM assignment_groups WHERE course_id = ?` to `clear_refreshable_data()`.

**Warning signs:** After renaming an assignment group in Canvas and re-syncing, the Settings UI still shows the old group name.

### Pitfall 7: Frontend Multi-Select for Eligible Groups

**What goes wrong:** Rendering a plain text input for `late_day_eligible_groups` (a JSON array of IDs). Users have no idea which IDs correspond to which group names.

**Why it happens:** The IDs are opaque integers.

**How to avoid (Claude's Discretion):** Fetch the list of assignment groups from a new endpoint (`GET /api/canvas/assignment-groups/{course_id}`) or from the existing `/api/canvas/data/{course_id}` response. Render as a labeled checkbox list or multi-select showing group names, storing only IDs in the setting. This is the pattern used for course selection in Settings.jsx.

---

## Code Examples

### Grace Period Days-Late Computation (Extract from Existing)

```python
# Source: main.py calculate_late_days_for_user() lines 400-414
# Extract this as a helper to avoid duplication:

def _compute_days_late(
    submission: dict[str, Any] | None,
    due_at: str,
) -> int:
    """Return days late (ceiling), accounting for grace period. 0 if not late."""
    if not submission:
        return 0
    submitted_at = submission.get("submitted_at")
    workflow_state = submission.get("workflow_state", "")
    if not submitted_at or workflow_state in ("unsubmitted", "pending_review"):
        return 0
    try:
        submitted_datetime = dateutil_parser.parse(submitted_at)
        due_datetime = dateutil_parser.parse(due_at)
        if submitted_datetime <= due_datetime:
            return 0
        time_diff = submitted_datetime - due_datetime
        grace_seconds = LATE_SUBMISSION_GRACE_PERIOD_MINUTES * 60
        total_seconds = time_diff.total_seconds() - grace_seconds
        if total_seconds <= 0:
            return 0
        return math.ceil(total_seconds / 86400)
    except Exception:
        return 0
```

### Settings API — Extended Pydantic Models

```python
# Source: main.py lines 109-135 (extend these models)
class SettingsResponse(BaseModel):
    course_id: str | None
    course_name: str | None
    canvas_api_url: str
    last_sync: dict[str, Any] | None
    test_mode: bool
    sandbox_course_id: str
    timezone: str | None
    data_path: str
    # Existing (kept for compat)
    max_late_days_per_assignment: int
    # New
    total_late_day_bank: int
    penalty_rate_per_day: int
    per_assignment_cap: int
    late_day_eligible_groups: list[int]


class SettingsUpdateRequest(BaseModel):
    course_id: str | None = None
    test_mode: bool | None = None
    timezone: str | None = None
    # New late day policy fields
    total_late_day_bank: int | None = None
    penalty_rate_per_day: int | None = None
    per_assignment_cap: int | None = None
    late_day_eligible_groups: list[int] | None = None
    # Deprecated but kept for backward compat
    max_late_days_per_assignment: int | None = None
```

### LateDaysTracking API Response Shape (New)

```json
{
  "students": [
    {
      "student_id": "123",
      "student_name": "...",
      "ta_group_name": "...",
      "bank_remaining": 7,
      "total_bank": 10,
      "assignments": {
        "456": {
          "days_late": 3,
          "bank_days_used": 3,
          "bank_remaining": 7,
          "penalty_days": 0,
          "penalty_percent": 0,
          "not_accepted": false
        },
        "789": {
          "days_late": 2,
          "bank_days_used": 0,
          "bank_remaining": 7,
          "penalty_days": 2,
          "penalty_percent": 100,
          "not_accepted": true
        }
      }
    }
  ],
  "assignments": [...],
  "assignment_groups": [{"id": 1, "name": "Homework"}, ...],
  "course_info": {...},
  "last_updated": "..."
}
```

### Frontend — New Endpoint for Assignment Groups

```javascript
// In Settings.jsx — fetch assignment groups when course is configured
const loadAssignmentGroups = useCallback(async () => {
    if (!settings.course_id) return;
    try {
        const data = await apiFetch(`/api/canvas/assignment-groups/${settings.course_id}`);
        setAssignmentGroups(data.groups || []);
    } catch (err) {
        console.error('Error loading assignment groups:', err);
    }
}, [settings.course_id]);

// Render as checkbox list (Claude's Discretion — layout):
// {assignmentGroups.map(group => (
//   <label key={group.id} className="flex items-center gap-2">
//     <input type="checkbox"
//       checked={eligibleGroupIds.includes(group.id)}
//       onChange={() => toggleGroup(group.id)} />
//     <span className="text-sm">{group.name}</span>
//   </label>
// ))}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 10% penalty per day, per-assignment | 25% penalty per day, bank-aware | This phase | Penalty doubles for uncovered days |
| `max_late_days_per_assignment` = per-assignment cap only | `per_assignment_cap` = sub-cap within semester bank | This phase | Students now have a shared bank across all assignments |
| All assignments treated equally | Assignment group determines eligibility | This phase | Project deliverables = "Not Accepted" vs bank draw-down |
| `calculate_late_days_for_user()` per assignment | `calculate_student_late_day_summary()` across all assignments | This phase | Bank state propagates chronologically |

**Deprecated/outdated:**
- `max_late_days_per_assignment` setting key: superseded by `per_assignment_cap`. Keep in DB reads for migration; deprecate new writes.
- `days_remaining` template variable: maps to `bank_remaining` in new model. Keep as alias.
- `penalty_days × 10%` calculation in `calculate_late_days_for_user()`: replaced by `penalty_days × penalty_rate_per_day` from settings.

---

## Open Questions

1. **Should comment posting skip "Not Accepted" project deliverables?**
   - What we know: CONTEXT.md specifies "Not Accepted, zero grade" for project deliverables submitted late, but does not specify whether a comment is posted.
   - What's unclear: Should the SSE posting flow skip these, or post a distinct "Not Accepted" comment?
   - Recommendation: Skip template rendering for `not_accepted = True` entries; add a log warning. If a comment is needed, it would require a third template type ("not_accepted"). Keep scope minimal — skip posting unless explicitly needed.

2. **Where does assignment_group_id come from on the Canvas Assignment object?**
   - What we know: Canvas REST API documents `assignment_group_id` as a field on Assignment objects. The `canvasapi` package wraps the API response directly.
   - What's unclear: Whether the field is always populated or may be `None` for ungrouped assignments.
   - Recommendation: Use `getattr(assignment_obj, "assignment_group_id", None)` with `None` as default. Assignments with `assignment_group_id = None` are not in any group — treat as NOT eligible (project deliverable behavior) unless `late_day_eligible_groups` is empty, in which case treat all as eligible (backward-compat default).

3. **Migration path for existing databases without assignment_group_id data**
   - What we know: Existing `assignments` table rows have no `assignment_group_id` column.
   - What's unclear: After migration adds the column (NULL for existing rows), assignments will show `assignment_group_id = None` until next sync.
   - Recommendation: On first load after upgrade (before sync), if `late_day_eligible_groups` is empty (unconfigured), treat all assignments as bank-eligible (safe fallback). The Settings UI should prompt the user to configure eligible groups and sync.

---

## Sources

### Primary (HIGH confidence)
- Canvas REST API docs (https://canvas.instructure.com/doc/api/assignment_groups.html) — AssignmentGroup object fields: `id`, `name`, `position`, `group_weight`
- canvasapi readthedocs (https://canvasapi.readthedocs.io/en/stable/course-ref.html) — `course.get_assignment_groups()` returns `PaginatedList[AssignmentGroup]`
- Project source: `main.py` lines 362-432 — existing `calculate_late_days_for_user()` implementation
- Project source: `database.py` lines 49-391 — `init_db()`, migration pattern, upsert patterns
- Project source: `canvas_sync.py` lines 218-500 — `sync_course_data()` structure
- Project source: `.claude/skills/canvas-api-expert/SKILL.md` — canonical project patterns for Canvas API, ETL, safe attribute access

### Secondary (MEDIUM confidence)
- CONTEXT.md algorithm specification — two-pass algorithm fully specified by the user, with example calculations
- Project source: `main.py` lines 276-317 — `ALLOWED_TEMPLATE_VARIABLES` set and template validation pattern

### Tertiary (LOW confidence)
- None — all claims verified against source code or official docs.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all existing packages
- Architecture: HIGH — directly derived from reading actual source files
- Algorithm correctness: HIGH — spec is fully defined in CONTEXT.md with concrete examples
- Canvas API (assignment_group_id on assignments): MEDIUM — verified against REST API docs; canvasapi wraps the same fields but `assignment_group_id` attribute name not explicitly in canvasapi readthedocs (it mirrors the REST API field)
- Pitfalls: HIGH — derived from reading actual code paths that will be modified

**Research date:** 2026-03-01
**Valid until:** 2026-04-01 (stable stack — all libraries are pinned, no fast-moving dependencies)
