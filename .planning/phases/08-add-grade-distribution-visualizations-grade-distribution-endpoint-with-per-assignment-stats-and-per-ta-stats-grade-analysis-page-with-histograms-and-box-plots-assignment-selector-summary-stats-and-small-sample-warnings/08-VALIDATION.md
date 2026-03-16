---
phase: 8
slug: add-grade-distribution-visualizations-grade-distribution-endpoint-with-per-assignment-stats-and-per-ta-stats-grade-analysis-page-with-histograms-and-box-plots-assignment-selector-summary-stats-and-small-sample-warnings
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + vitest with React Testing Library (frontend) |
| **Config file** | pyproject.toml (pytest) / canvas-react/vite.config.js (vitest) |
| **Quick run command** | `uv run pytest tests/test_08_*.py -x -q` |
| **Full suite command** | `uv run pytest -x -q && cd canvas-react && npm run test -- --run` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_08_*.py -x -q`
- **After every plan wave:** Run `uv run pytest -x -q && cd canvas-react && npm run test -- --run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-W0-01 | W0 | 0 | GRADE-DIST-DB | unit | `uv run pytest tests/test_08_01_api.py -x -q` | ❌ W0 | ⬜ pending |
| 08-W0-02 | W0 | 0 | GRADE-DIST-UI | unit | `cd canvas-react && npm run test -- --run GradeAnalysis` | ❌ W0 | ⬜ pending |
| 08-01-01 | 01 | 1 | GRADE-DIST-DB | unit | `uv run pytest tests/test_08_01_api.py -x -q` | ❌ W0 | ⬜ pending |
| 08-02-01 | 02 | 1 | GRADE-DIST-API | unit | `uv run pytest tests/test_08_01_api.py -x -q` | ❌ W0 | ⬜ pending |
| 08-03-01 | 03 | 2 | GRADE-DIST-UI | unit | `cd canvas-react && npm run test -- --run GradeAnalysis` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_08_01_api.py` — stubs for grade-distribution endpoint (index + detail)
- [ ] `canvas-react/src/components/GradeAnalysis.test.jsx` — stubs for GradeAnalysis page, histogram, and box plot components

*Existing test infrastructure (conftest.py, vitest config) covers phase requirements — no new framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Histogram bars visually accurate | GRADE-DIST-UI | SVG rendering can't be asserted by unit tests | Navigate to Grade Analysis, select assignment, verify histogram bins match score range and heights look proportional |
| Box plot whiskers correct | GRADE-DIST-UI | Visual rendering | Select assignment with known scores, verify median line, box edges, and whiskers position matches expected quartiles |
| Small-sample warning appears | GRADE-DIST-UI | Threshold trigger | Select an assignment where a TA has < 5 graded submissions, verify warning badge appears beside that TA's box plot |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
