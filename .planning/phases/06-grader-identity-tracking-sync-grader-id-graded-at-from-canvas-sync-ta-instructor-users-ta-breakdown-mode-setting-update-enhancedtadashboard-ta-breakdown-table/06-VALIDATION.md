---
phase: 6
slug: 06-grader-identity-tracking
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-14
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + vitest (frontend) |
| **Config file** | `pyproject.toml` (pytest) / `canvas-react/vite.config.js` (vitest) |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ && cd canvas-react && npm run test -- --run` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ && cd canvas-react && npm run test -- --run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 6-01-01 | 01 | 1 | ta_users DB schema | unit | `uv run pytest tests/test_06_01_schema.py::TestTAUsersTable -x -q` | ❌ W0 | ⬜ pending |
| 6-01-02 | 01 | 1 | submissions grader_id migration | unit | `uv run pytest tests/test_06_01_schema.py::TestSubmissionsMigration -x -q` | ❌ W0 | ⬜ pending |
| 6-01-03 | 01 | 1 | upsert_ta_users | unit | `uv run pytest tests/test_06_01_schema.py::TestUpsertTAUsers -x -q` | ❌ W0 | ⬜ pending |
| 6-02-01 | 02 | 1 | canvas_sync ta_users fetch | unit | `uv run pytest tests/test_06_02_sync.py::TestSyncTAUsers -x -q` | ❌ W0 | ⬜ pending |
| 6-02-02 | 02 | 1 | grader_id captured in sync | unit | `uv run pytest tests/test_06_02_sync.py::TestSyncGraderFields -x -q` | ❌ W0 | ⬜ pending |
| 6-03-01 | 03 | 2 | get_submissions grader_name join | unit | `uv run pytest tests/test_06_03_api.py::TestSubmissionsGraderName -x -q` | ❌ W0 | ⬜ pending |
| 6-03-02 | 03 | 2 | submissions endpoint includes grader fields | unit | `uv run pytest tests/test_06_03_api.py::TestTABreakdownModeSetting -x -q` | ❌ W0 | ⬜ pending |
| 6-04-00 | 04 | 3 | EnhancedTADashboard breakdown mode stubs | unit | `cd canvas-react && npm run test -- --run EnhancedTADashboard 2>&1 \| tail -10` | ❌ W0 | ⬜ pending |
| 6-04-02 | 04 | 3 | Settings TA Dashboard toggle | unit | `cd canvas-react && npm run test -- --run Settings 2>&1 \| tail -10` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 test stubs are created as the **first task within each plan** (not a separate pre-phase):

- [x] `tests/test_06_01_schema.py` — Plan 01 Task 1 creates stubs for: `TestTAUsersTable`, `TestSubmissionsMigration`, `TestUpsertTAUsers`, `TestClearRefreshableData`
- [x] `tests/test_06_02_sync.py` — Plan 02 Task 1 creates stubs for: `TestSyncTAUsers`, `TestSyncGraderFields`, `TestUpsertSubmissionsGraderFields`
- [x] `tests/test_06_03_api.py` — Plan 03 Task 1 creates stubs for: `TestSubmissionsGraderName`, `TestTABreakdownModeSetting`
- [ ] `canvas-react/src/EnhancedTADashboard.test.jsx` — Plan 04 Task 0 adds `describe('taBreakdownMode prop')` block with stubs for mode defaults and branching
- [ ] `canvas-react/src/Settings.test.jsx` — Plan 04 Task 0 creates new file with stub for TA Dashboard card rendering

*Note: Backend Wave 0 stubs (test_06_01, test_06_02, test_06_03) are created inline in Plans 01-03. Frontend stubs are created in Plan 04 Task 0. `wave_0_complete` becomes true once Plan 04 Task 0 completes.*

*Existing infrastructure (pytest + vitest) covers phase requirements — no new framework needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| grader_id resolved to real TA name after sync | grader_name in API response | Requires live Canvas sync with sandbox course | Sync sandbox course, check submissions endpoint response for grader_name field |
| TA Dashboard toggle takes effect on page reload | ta_breakdown_mode UX | Requires browser interaction | Toggle setting in Settings, navigate to dashboard, verify breakdown source changes |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (backend inline in plans 01-03, frontend in plan 04 Task 0)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
