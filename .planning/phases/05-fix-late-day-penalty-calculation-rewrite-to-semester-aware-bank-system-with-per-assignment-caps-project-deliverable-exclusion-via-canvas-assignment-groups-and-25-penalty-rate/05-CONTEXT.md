# Phase 5: Fix Late Day Penalty Calculation - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning
**Source:** GSD todo `2026-03-01-fix-late-day-penalty-calculation-logic.md`

<domain>
## Phase Boundary

Rewrite the late day penalty calculation from a per-assignment cap model to a semester-aware bank system. Covers backend logic (canvas_sync.py, database.py, main.py), Settings UI (new Late Day Policy section), and LateDaysTracking.jsx display changes. Comment template variables also updated. Does NOT change how comments are posted — only what data is calculated and displayed.

</domain>

<decisions>
## Implementation Decisions

### Semester bank
- Each student gets **10 late days total** across all assignments in the semester (configurable via `total_late_day_bank` setting, default 10)
- Bank is **per-course**, not cross-course
- Processing order: assignments sorted **chronologically by due date** — due date determines which assignment consumes bank days first (not submission date)

### Per-assignment cap
- Max **7 late days** on any single assignment (configurable via `per_assignment_cap` setting, default 7)
- Caps the bank days that can be applied to a single assignment — prevents a student from spending all bank days on one assignment

### Penalty calculation (two-pass per student)
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

### Penalty rate
- **25% of earned grade per penalty day** (not 10% as currently implemented)
- Capped at 100% (zero grade)
- Only applies to days BEYOND what the bank covers (days within bank = no penalty)

### Project deliverable exclusion
- Project deliverables identified by **Canvas assignment group** — head TA selects in Settings which groups allow late submissions (`late_day_eligible_groups` = JSON array of assignment group IDs)
- Assignments in groups NOT in `late_day_eligible_groups` are treated as project deliverables
- Project deliverable submitted late: status = **"Not Accepted"**, zero grade, NO bank days consumed

### Example calculations (from todo — planner must match these)
- Student 9 days late, full 10-day bank: 7 bank days used (capped), 2 penalty days → 50% penalty, bank now 3
- Student 3 days late, 1 bank day left: 1 bank day used, 2 penalty days → 50% penalty, bank now 0
- Project deliverable 2 days late: "Not Accepted", zero grade, bank unchanged

### New settings
- `total_late_day_bank` — integer, default 10
- `penalty_rate_per_day` — integer (%), default 25
- `per_assignment_cap` — integer, default 7 (replaces `max_late_days_per_assignment`)
- `late_day_eligible_groups` — JSON array of Canvas assignment group IDs that allow late submissions

### Database changes
- New `assignment_groups` table: id, course_id, name
- Add `assignment_group_id` column to `assignments` table

### Canvas sync changes
- Sync assignment groups via `course.get_assignment_groups()` in canvas_sync.py
- Store `assignment_group_id` on each assignment during sync

### Template variable changes
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

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `calculate_late_days_for_user()` (main.py:362-432): Replace with `calculate_student_late_day_summary()` that processes all assignments for a student in one pass
- `get_late_days_data()` endpoint (main.py:1544-1644): Update to return bank balance per student and per-assignment `bank_days_used` vs `penalty_days`
- `LATE_SUBMISSION_GRACE_PERIOD_MINUTES` constant: keep for grace period logic
- `_build_submission_lookup()` helper: reusable in new calculation
- `upsert_assignments()` pattern (database.py): extend to include `assignment_group_id`
- `apiFetch` in frontend: unchanged, used by LateDaysTracking.jsx already
- Settings page (Settings.jsx): add "Late Day Policy" section alongside existing settings

### Established Patterns
- Upsert pattern (`INSERT ... ON CONFLICT DO UPDATE`): use for new `assignment_groups` table
- `get_setting()` / `set_setting()` for new settings keys
- Pydantic models for settings request/response — extend `SettingsUpdateRequest` and `SettingsResponse`
- Loguru logging for all backend operations
- Tailwind CSS status colors: green for bank days (no penalty), amber/red for penalty days, gray/red for "Not Accepted"

### Integration Points
- `canvas_sync.py → sync_course_data()`: add `get_assignment_groups()` fetch + `assignment_group_id` upsert on assignments
- `main.py → get_late_days_data()`: consumes new two-pass calculation result
- `main.py → comment posting flow` (around line 1032): uses `calculate_late_days_for_user()` — must migrate to new calculation function
- `Settings.jsx`: add group multi-select after existing settings fields; groups fetched from new endpoint or from `/api/canvas/data/{course_id}`
- `LateDaysTracking.jsx`: new columns/cells for bank balance, bank vs penalty distinction

</code_context>

<specifics>
## Specific Ideas

- The two-pass algorithm is fully specified in the todo — planner should implement exactly this approach
- Comment posting flow currently calls `calculate_late_days_for_user()` per-assignment (main.py ~1032-1037) — must be updated to use pre-computed bank summary instead
- "Not Accepted" for project deliverables should be a visually distinct state (not just a number) in LateDaysTracking.jsx

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-fix-late-day-penalty-calculation*
*Context gathered: 2026-03-01 via GSD todo*
