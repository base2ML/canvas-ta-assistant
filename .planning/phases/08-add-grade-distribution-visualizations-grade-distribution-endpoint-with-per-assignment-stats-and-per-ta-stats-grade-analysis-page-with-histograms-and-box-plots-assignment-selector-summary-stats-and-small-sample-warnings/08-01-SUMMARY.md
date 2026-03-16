---
phase: 08-add-grade-distribution-visualizations
plan: "01"
subsystem: testing
tags: [tdd, red-state, grade-distribution, vitest, pytest]
dependency_graph:
  requires: []
  provides:
    - tests/test_08_01_grade_distribution.py
    - canvas-react/src/GradeAnalysis.test.jsx
    - canvas-react/src/components/GradeHistogram.test.jsx
    - canvas-react/src/components/GradeBoxPlot.test.jsx
  affects:
    - main.py (endpoint must be implemented for tests to pass)
    - canvas-react/src/GradeAnalysis.jsx (component must be implemented)
    - canvas-react/src/components/GradeHistogram.jsx (component must be implemented)
    - canvas-react/src/components/GradeBoxPlot.jsx (component must be implemented)
tech_stack:
  added: []
  patterns:
    - DB_PATH monkeypatch + asyncio.run(_get(...)) for FastAPI endpoint tests
    - Vitest import-error RED state for React component tests
key_files:
  created:
    - tests/test_08_01_grade_distribution.py
    - canvas-react/src/GradeAnalysis.test.jsx
    - canvas-react/src/components/GradeHistogram.test.jsx
    - canvas-react/src/components/GradeBoxPlot.test.jsx
  modified: []
decisions:
  - "pytest file uses DB_PATH monkeypatch (not DATA_DIR) consistent with test_07_02_api.py — tests the API layer"
  - "upsert_ta_users requires enrollment_type field — included in all seed data dicts"
  - "GradeAnalysis.test.jsx uses _testData prop pattern for small-sample test — avoids fetch mock complexity"
  - "GradeBoxPlot.test.jsx asserts rect and line elements, not SVG children count — component structure-agnostic"
metrics:
  duration: "4 min"
  completed_date: "2026-03-15"
  tasks_completed: 2
  files_changed: 4
---

# Phase 08 Plan 01: Grade Distribution Test Scaffolds (Wave 0) Summary

**One-liner:** RED-state test scaffolds for all Phase 8 grade distribution requirements using pytest + Vitest with import-error and 404-error failure modes.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Write pytest stubs for grade distribution endpoint and stats | e5886b3 | tests/test_08_01_grade_distribution.py |
| 2 | Write Vitest stubs for GradeAnalysis, GradeHistogram, GradeBoxPlot | 41e201e | 3 test files |

## What Was Built

**Task 1 — pytest stubs (tests/test_08_01_grade_distribution.py):**

6 test classes covering all backend requirements:

- `TestGradeDistributionIndex` — index endpoint returns assignments list with graded_count
- `TestGradeDistributionDetail` — detail endpoint returns stats, histogram, per_ta keys
- `TestGradeStats` — mean/median/min/max correctness for known scores [70, 80, 90]
- `TestSmallSample` — small_sample flag logic; stdev/q1/q3 None when n=1
- `TestHistogramBins` — 10 bins for points_possible=100; total count == n; last bin catches max
- `TestPerTaStats` — known grader grouped by name; NULL grader_id grouped as "Unknown / Pre-Phase 6"

All tests use `DB_PATH` monkeypatch + `asyncio.run(_get(app, path))` pattern identical to `test_07_02_api.py`. Seed data uses `upsert_assignments`, `upsert_users`, `upsert_ta_users`, `upsert_submissions`.

**Task 2 — Vitest stubs (3 files):**

- `GradeAnalysis.test.jsx` — renders assignment selector (combobox), loading state, small-sample warning badge (using `_testData` prop), route render
- `GradeHistogram.test.jsx` — rect count matches bins.length; empty bins renders no rects
- `GradeBoxPlot.test.jsx` — SVG + rect + line elements for n>=2; null render for n<2

All 3 files import non-existent components, producing import errors (valid RED state).

## Verification

**RED state confirmed:**

```
uv run pytest tests/test_08_01_grade_distribution.py -q
→ 21 FAILED (404 Not Found — endpoint does not exist)

cd canvas-react && npm test -- --run GradeAnalysis GradeHistogram GradeBoxPlot
→ 3 test files FAILED (import errors — components do not exist)
```

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- tests/test_08_01_grade_distribution.py: FOUND
- canvas-react/src/GradeAnalysis.test.jsx: FOUND
- canvas-react/src/components/GradeHistogram.test.jsx: FOUND
- canvas-react/src/components/GradeBoxPlot.test.jsx: FOUND
- Commit e5886b3: FOUND
- Commit 41e201e: FOUND
