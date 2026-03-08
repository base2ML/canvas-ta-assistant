---
phase: 05-fix-late-day-penalty-calculation
verified: 2026-03-01T18:30:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
human_verification:
  - test: "Late Day Policy UI — visual layout and save roundtrip"
    expected: "Settings page shows Late Day Policy card with 3 integer inputs, group checkboxes, and dedicated Save button; values persist after reload"
    why_human: "Checkpoint was completed and approved by user on 2026-03-01; visual layout cannot be re-verified programmatically"
  - test: "LateDaysTracking — NA badge, green/red circles, legend"
    expected: "Project deliverables show NA badge; bank-covered late days show green circles; penalty days show red circles; legend appears below table"
    why_human: "Checkpoint was completed and approved by user on 2026-03-01; rendering requires running frontend"
---

# Phase 05: Fix Late Day Penalty Calculation — Verification Report

**Phase Goal:** Fix late day penalty calculation — rewrite to semester-aware bank system with per-assignment caps, project deliverable exclusion via Canvas assignment groups, and 25% penalty rate

**Verified:** 2026-03-01T18:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Requirements Coverage

No `.planning/REQUIREMENTS.md` file exists in this repository. The requirement IDs declared in plan frontmatter (LATE-DB-01, LATE-SYNC-01, LATE-API-GROUPS-01, LATE-ALGO-01, LATE-SETTINGS-01, LATE-TEMPLATE-01, LATE-POSTING-01, LATE-UI-01, LATE-UI-02) cannot be cross-referenced against a requirements document. Requirements coverage is assessed below by matching each ID to its implementing plan and verifying implementation evidence in the codebase.

| Requirement ID    | Source Plan | Description (from plan)                              | Status      | Evidence                                                   |
|-------------------|-------------|------------------------------------------------------|-------------|------------------------------------------------------------|
| LATE-DB-01        | 05-01       | assignment_groups table + assignment_group_id column | SATISFIED   | `database.py` lines 81-99: CREATE TABLE, migration, index  |
| LATE-SYNC-01      | 05-02       | Canvas assignment groups fetched and synced          | SATISFIED   | `canvas_sync.py` line 361: `db.upsert_assignment_groups()` |
| LATE-API-GROUPS-01| 05-02       | GET /api/canvas/assignment-groups/{course_id}        | SATISFIED   | `main.py` line 1477: endpoint defined                      |
| LATE-ALGO-01      | 05-03       | Semester bank algorithm with caps/exclusions         | SATISFIED   | `main.py` lines 479-566: `calculate_student_late_day_summary()` |
| LATE-SETTINGS-01  | 05-03       | Settings model + DB read/write for 4 policy fields   | SATISFIED   | `main.py` lines 120-134: models with bank fields           |
| LATE-TEMPLATE-01  | 05-03       | render_template() supports bank variables            | SATISFIED   | `main.py` lines 293-296: bank_days_used, bank_remaining etc in VALID_VARIABLES |
| LATE-POSTING-01   | 05-03       | preview/post use bank summary, not old algorithm     | SATISFIED   | `main.py` lines 1048, 1288: `render_template()` in both   |
| LATE-UI-01        | 05-04       | Settings Late Day Policy section                     | SATISFIED   | `Settings.jsx` lines 29-634: policySettings state, load, save, UI section |
| LATE-UI-02        | 05-04       | LateDaysTracking bank/penalty/NA cell rendering      | SATISFIED   | `LateDaysTracking.jsx` lines 861-911: entry object handling, NA badge, bank_remaining display |

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | assignment_groups table exists with course_id, name, position columns | VERIFIED | `database.py` lines 81-91: CREATE TABLE IF NOT EXISTS assignment_groups with all required columns and index |
| 2 | assignments table has assignment_group_id column (migration applied) | VERIFIED | `database.py` lines 94-99: ALTER TABLE migration; get_assignments() SELECT includes assignment_group_id (line 979) |
| 3 | Canvas assignment groups are fetched and stored on sync | VERIFIED | `canvas_sync.py` line 361: `db.upsert_assignment_groups(course_id, assignment_groups_data, conn)` called inside sync transaction |
| 4 | GET /api/canvas/assignment-groups/{course_id} endpoint exists | VERIFIED | `main.py` line 1477: `@app.get("/api/canvas/assignment-groups/{course_id}")` |
| 5 | Semester bank algorithm calculates bank_days_used, penalty_days, not_accepted per assignment | VERIFIED | `main.py` lines 479-566: `calculate_student_late_day_summary()` with per_assignment_cap, bank deduction, not_accepted flag for ineligible groups |
| 6 | Settings models accept/persist total_late_day_bank, penalty_rate_per_day, per_assignment_cap, late_day_eligible_groups | VERIFIED | `main.py` lines 120-134: Pydantic models with all four fields; `main.py` lines 665-669: DB read on late-days endpoint |
| 7 | Comment templates support {bank_days_used}, {bank_remaining}, {total_bank} variables | VERIFIED | `main.py` lines 293-296: VALID_VARIABLES list includes bank_days_used, bank_remaining; render_template() at lines 362, 1048, 1288 |
| 8 | Settings.jsx has Late Day Policy section with 4 policy fields and group checkbox list | VERIFIED | `Settings.jsx` lines 29-563: policySettings state, loadAssignmentGroups callback with apiFetch to /api/canvas/assignment-groups/{course_id}, three integer inputs, checkbox list; save via PUT /api/settings includes all four fields (lines 92-95, 118-121) |
| 9 | LateDaysTracking.jsx shows bank/penalty distinction per cell and NA badge for project deliverables | VERIFIED | `LateDaysTracking.jsx` lines 861-911: entry.not_accepted -> NA badge; entry.bank_days_used -> green circle; entry.penalty_days -> red circle; bank_remaining/total_bank below student total; color legend at line 791 |

**Score:** 9/9 truths verified

---

### Required Artifacts

| Artifact | Provides | Status | Details |
|----------|----------|--------|---------|
| `database.py` | assignment_groups table, migration, clear/upsert functions | VERIFIED | CREATE TABLE (line 81), migration (line 94-99), upsert_assignment_groups (line 769), clear in both clear functions (lines 667, 701), assignment_group_id in upsert_assignments (line 733) and get_assignments SELECT (line 979) |
| `canvas_sync.py` | Fetch and store Canvas assignment groups | VERIFIED | upsert_assignment_groups called at line 361 inside sync transaction |
| `main.py` | Semester bank algorithm, settings models, API endpoint, template variables | VERIFIED | calculate_student_late_day_summary (line 479), Pydantic models (lines 120-134), GET assignment-groups endpoint (line 1477), VALID_VARIABLES with bank fields (lines 293-296) |
| `canvas-react/src/Settings.jsx` | Late Day Policy section with 4 fields and group multiselect | VERIFIED | policySettings state (line 31-35), loadAssignmentGroups (line 173-177), Late Day Policy UI (line 485+), save (lines 92-95, 118-121), variable list (line 634) |
| `canvas-react/src/LateDaysTracking.jsx` | Bank/penalty cells, NA badge, bank_remaining display, legend | VERIFIED | not_accepted -> NA badge (lines 861, 874-876), bank_days_used (line 862), penalty_days (line 863), bank_remaining (line 909-911), legend (lines 791-792) |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| canvas_sync.py sync_course_data() | database.upsert_assignment_groups() | called inside db transaction | WIRED | `canvas_sync.py` line 361 confirmed |
| database.clear_refreshable_data() | assignment_groups table | DELETE FROM assignment_groups WHERE course_id = ? | WIRED | `database.py` line 667 confirmed |
| Settings.jsx Late Day Policy save | PUT /api/settings | apiFetch with total_late_day_bank, penalty_rate_per_day, per_assignment_cap, late_day_eligible_groups | WIRED | `Settings.jsx` lines 92-95 (main save) and lines 118-121 (dedicated policy save) confirmed |
| Settings.jsx group selector | GET /api/canvas/assignment-groups/{course_id} | apiFetch in useCallback when course_id available | WIRED | `Settings.jsx` line 177: `apiFetch(\`/api/canvas/assignment-groups/${settings.course_id}\`)` confirmed |
| LateDaysTracking.jsx assignment cell | student.assignments[assignment.id] | entry.bank_days_used, entry.penalty_days, entry.not_accepted | WIRED | `LateDaysTracking.jsx` lines 861-863: entry object fields consumed for rendering |
| main.py get_late_days_data() | calculate_student_late_day_summary() | reads settings then calls algorithm | WIRED | `main.py` lines 665-669: reads total_late_day_bank and penalty_rate_per_day from DB, passes to algorithm |

---

### Commit Verification

All commits declared in SUMMARY.md are confirmed present in git history:

| Commit | Description |
|--------|-------------|
| f20236e | feat(05-04): add Late Day Policy section to Settings.jsx |
| d48ee83 | feat(05-04): update LateDaysTracking for bank/penalty distinction and Not Accepted badge |
| 6d8ecec | fix(05-04): add Save Policy Settings button and fix settings persistence UX |
| 80dc14a | fix(05-04): include assignment_group_id in get_assignments() SELECT |
| 47e6579 | docs(05-03): complete — semester bank algorithm, settings, and posting flow |
| c54b7d0 | feat(05-03): update preview/post to use bank summary |
| 7be6693 | feat(05-03): update settings models and get_late_days_data() |
| 8ab4203 | feat(05-03): implement _compute_days_late() and calculate_student_late_day_summary() |
| 223de42 | feat(05-02): add GET /api/canvas/assignment-groups/{course_id} endpoint |
| ea4b10f | feat(05-02): fetch Canvas assignment groups and annotate assignments |
| 1275656 | feat(05-01): add assignment_groups table and assignment_group_id migration |
| a98377e | feat(05-01): add upsert_assignment_groups() and extend clear/upsert functions |

---

### Anti-Patterns Found

No blocker anti-patterns found. The post-checkpoint fixes in SUMMARY.md (80dc14a: assignment_group_id missing from SELECT) were correctly identified and resolved before phase completion. The dedicated Save Policy Settings button addition (6d8ecec) addressed a UX gap.

---

### Human Verification Required

#### 1. Late Day Policy UI — visual layout and save roundtrip

**Test:** Navigate to Settings, scroll to Late Day Policy section. Verify three labeled integer inputs (Total Late Day Bank, Penalty Rate, Per-Assignment Cap) and a group checkbox area. Change Total Late Day Bank to 8, click Save Policy Settings, reload Settings page.
**Expected:** Value reads back as 8. If a course is synced, assignment groups appear as checkboxes.
**Why human:** Checkpoint approved by user on 2026-03-01. Visual layout and save persistence cannot be re-verified programmatically.

#### 2. LateDaysTracking — cell rendering for each state

**Test:** Navigate to Late Days Tracking with a synced course. Verify: on-time submissions show "—", bank-covered late shows green circle with count, penalty-day late shows red circle, project deliverables show "NA" badge, student total column shows "X/Y bank left", color legend appears below table.
**Expected:** All four cell states render correctly per the plan specification.
**Why human:** Checkpoint approved by user on 2026-03-01. Cell rendering requires running frontend with real Canvas data.

---

## Gaps Summary

No gaps. All 9 observable truths verified against the codebase. All 5 required artifacts confirmed substantive and wired. All 6 key links confirmed. All 9 requirement IDs from plan frontmatter have implementation evidence. Human checkpoint was approved by the user during execution.

Note: `.planning/REQUIREMENTS.md` does not exist in this project. Requirement IDs (LATE-DB-01 through LATE-UI-02) were mapped to plan frontmatter only, not cross-referenced against a requirements document. No orphaned requirements were found because no REQUIREMENTS.md exists.

---

_Verified: 2026-03-01T18:30:00Z_
_Verifier: Claude (gsd-verifier)_
