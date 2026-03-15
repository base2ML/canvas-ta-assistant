# Phase 6: Grader Identity Tracking - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Sync `grader_id` and `graded_at` from Canvas submission data into the submissions table. Sync TA and instructor user enrollments into a new `ta_users` table for grader name resolution. Add `ta_breakdown_mode` setting to Settings page. Update EnhancedTADashboard TA breakdown table to use actual grader data (from `grader_id`) when that mode is active. Does NOT change comment posting, late days, or any other dashboard pages.

</domain>

<decisions>
## Implementation Decisions

### Breakdown mode behavior
- Default mode is **group assignment** (current behavior) — actual grader mode is opt-in
- The breakdown table keeps the same row structure in both modes: one row per TA, same columns (total assigned, graded, pending, % complete)
- In actual-grader mode: graded count comes from `grader_id` (who pressed grade in Canvas); ungraded submissions fall back to group assignment for the pending count
- `graded_at` is stored in the DB but NOT displayed in the breakdown table in Phase 6 — reserved for future analytics

### TA user sync scope
- Sync users with `enrollment_type='ta'` and `enrollment_type='teacher'` into new `ta_users` table
- Table schema: `id, course_id, name, email, enrollment_type, synced_at`
- Sync order in `sync_course_data()`: after students, before submissions
- This is a NEW `ta_users` table — does not replace `group_members`; group-based assignment still works

### grader_id name resolution
- Resolution happens at the **backend**: `GET /api/canvas/submissions/{course_id}` returns `grader_id` and `grader_name` on each submission object (join to `ta_users` at query time)
- When `grader_id` is null or doesn't resolve to a `ta_users` row: fall back to group assignment silently (no "Unknown" row)
- EnhancedTADashboard already calls the submissions endpoint — no new fetch needed

### Settings page integration
- New **"TA Dashboard" section** in Settings.jsx, placed between Course Configuration and Late Day Policy
- `ta_breakdown_mode` is a **toggle switch** — "Show actual grader (grader_id) instead of group assignment"
- Default: off (group assignment)
- Mode change takes effect on next page load/navigation — no instant live-update, consistent with how other settings behave

### Claude's Discretion
- Exact layout of the "TA Dashboard" settings card
- How `grader_id` / `grader_name` are used in the `buildTAAssignments` / breakdown computation logic in EnhancedTADashboard.jsx
- Migration strategy for adding `grader_id` and `graded_at` columns to `submissions` table (try/except sqlite3.OperationalError pattern, consistent with Phase 5)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `canvas_sync.py` already fetches `enrollment_type='ta'` and `enrollment_type='teacher'` for course discovery — extend the same fetch to populate `ta_users`
- `submissions` table upsert in `canvas_sync.py` + `database.py`: extend to capture `grader_id` and `graded_at` from Canvas submission object
- `buildTAAssignments()` in `EnhancedTADashboard.jsx`: extend or replace logic to use `grader_name` from submissions when in actual-grader mode
- `get_setting()` / `set_setting()` pattern for `ta_breakdown_mode` setting (default: `"group"`)
- Settings.jsx test mode toggle: existing toggle pattern to reuse for `ta_breakdown_mode`

### Established Patterns
- `INSERT ... ON CONFLICT DO UPDATE` upsert for new `ta_users` table — same as all other Canvas entity tables
- `try/except sqlite3.OperationalError` for adding `grader_id` and `graded_at` columns to `submissions` table — consistent with Phase 5 `assignment_group_id` migration
- Pydantic model extension: extend `SettingsResponse` and `SettingsUpdateRequest` to include `ta_breakdown_mode`
- Loguru for all backend logging; `apiFetch` for all frontend API calls

### Integration Points
- `canvas_sync.py → sync_course_data()`: add ta_users fetch + upsert after student users, before submissions; add `grader_id`/`graded_at` to submission upsert
- `database.py → get_submissions()`: JOIN `ta_users` on `grader_id` to include `grader_name` in response
- `main.py → GET /api/canvas/submissions/{course_id}`: returns enriched submission with `grader_id` + `grader_name`
- `main.py → GET /api/settings` + `PUT /api/settings`: include `ta_breakdown_mode`
- `Settings.jsx`: add "TA Dashboard" card with toggle
- `EnhancedTADashboard.jsx → assignmentStats useMemo`: branch on `ta_breakdown_mode` to use `grader_name` from submissions vs group lookup

</code_context>

<specifics>
## Specific Ideas

- The `ta_breakdown_mode` setting value in the DB should be `"group"` (default) or `"actual"` — string enum, not boolean, for extensibility
- The toggle label: "Use actual grader from Canvas (grader_id)" — makes clear this is Canvas data, not computed

</specifics>

<deferred>
## Deferred Ideas

- Displaying `graded_at` for grading speed/deadline analytics — noted in STATE.md todos (#3 TA grading deadlines)
- Grade distribution visualizations — todo #4, depends on Phase 6

</deferred>

---

*Phase: 06-grader-identity-tracking*
*Context gathered: 2026-03-14*
