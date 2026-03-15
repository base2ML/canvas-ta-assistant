---
phase: 7
slug: add-ta-grading-deadlines-grading-deadlines-table-default-grading-turnaround-days-setting-rest-endpoints-for-deadline-crud-overdue-status-per-ta-settings-ui-inline-deadline-editing-on-dashboard-overdue-badges-and-shareable-grading-schedule-summary-view
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + vitest (frontend) |
| **Config file** | `pyproject.toml` (pytest) / `canvas-react/vitest.config.js` |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -q && cd canvas-react && npm run test -- --run` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -q && cd canvas-react && npm run test -- --run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 7-01-01 | 01 | 0 | DB schema | unit | `uv run pytest tests/test_07_01_schema.py -x -q` | ❌ W0 | ⬜ pending |
| 7-01-02 | 01 | 0 | Settings key | unit | `uv run pytest tests/test_07_02_api.py -x -q -k TestSettings` | ❌ W0 | ⬜ pending |
| 7-02-01 | 02 | 1 | CRUD endpoints | unit | `uv run pytest tests/test_07_02_api.py -x -q -k TestGetDeadlines` | ❌ W0 | ⬜ pending |
| 7-02-02 | 02 | 1 | Overdue status | unit | `uv run pytest tests/test_07_03_overdue.py -x -q` | ❌ W0 | ⬜ pending |
| 7-03-01 | 03 | 2 | Settings UI | manual | — | N/A | ⬜ pending |
| 7-03-02 | 03 | 2 | Inline editing | manual | — | N/A | ⬜ pending |
| 7-03-03 | 03 | 2 | Overdue badges | manual | — | N/A | ⬜ pending |
| 7-04-01 | 04 | 3 | Schedule view | manual | — | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave Structure

| Wave | Plans | Description |
|------|-------|-------------|
| 0 | 07-01 | Test scaffolds (all RED — expected) |
| 1 | 07-02 | database.py — grading_deadlines table + CRUD functions |
| 2 | 07-03 | main.py — settings field + deadline endpoints (depends on 07-02) |
| 3 | 07-04, 07-05 | Frontend UI (parallel — no file conflicts) |

---

## Wave 0 Requirements

- [ ] `tests/test_07_01_schema.py` — stubs for `grading_deadlines` table and upsert function tests
- [ ] `tests/test_07_02_api.py` — stubs for deadline CRUD, propagate-defaults, AND `TestSettings` class covering `default_grading_turnaround_days` (GET returns 7 default, PUT persists value)
- [ ] `tests/test_07_03_overdue.py` — stubs for `_is_overdue()` logic tests
- [ ] `canvas-react/src/components/AssignmentStatusBreakdown.test.jsx` — inline editor and overdue badge tests
- [ ] `canvas-react/src/components/GradingScheduleSummary.test.jsx` — assignment name, deadline, and overdue badge tests (no ta_groups test — API model does not include ta_groups per assignment)

*Existing pytest infrastructure covers the framework; only new test stubs needed for phase 7.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Inline deadline editing on Dashboard | UI interaction | React DOM edit flow hard to unit test | Open Dashboard, click deadline cell, edit date, verify save |
| Overdue badges appear correctly | Visual indicator | CSS/render verification | Trigger overdue condition, confirm badge appears on TA row |
| Grading Schedule Summary view | Full page render | Route + data render | Navigate to `/grading-schedule`, verify all assignments and deadlines shown |
| Settings UI for turnaround days | Form interaction | Form state verification | Open Settings, change default turnaround days, save, reload |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
