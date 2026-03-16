---
phase: 08-add-grade-distribution-visualizations-grade-distribution-endpoint-with-per-assignment-stats-and-per-ta-stats-grade-analysis-page-with-histograms-and-box-plots-assignment-selector-summary-stats-and-small-sample-warnings
plan: 02
subsystem: api
tags: [fastapi, pydantic, statistics, histogram, sqlite]

# Dependency graph
requires:
  - phase: 08-01
    provides: RED-state test scaffolds for grade-distribution endpoints
  - phase: 06
    provides: grader_id/graded_at columns on submissions, ta_users table, grader_name via LEFT JOIN in get_submissions()

provides:
  - GET /api/dashboard/grade-distribution/{course_id} — assignment index with graded_count
  - GET /api/dashboard/grade-distribution/{course_id}/{assignment_id} — full stats + histogram + per-TA breakdown
  - HistogramBin, GradeStats, TaGradeStats, GradeDistributionResponse, AssignmentGradeSummary, GradeDistributionIndexResponse Pydantic models
  - compute_histogram_bins() helper with 10 bins and closed-right last bin

affects:
  - 08-03 (Grade Analysis frontend page consumes these endpoints)

# Tech tracking
tech-stack:
  added: [Python standard library `statistics` module (mean, median, stdev, quantiles — via local import)]
  patterns:
    - Local `import statistics as _stats` inside endpoint function to avoid F811 name clash with Pydantic field names (mean, median, stdev)
    - compute_histogram_bins() as module-level helper separate from endpoint logic
    - Closed-right last bin (lo <= s <= hi) to catch score == points_possible exactly

key-files:
  created: []
  modified:
    - main.py

key-decisions:
  - "Used local `import statistics as _stats` inside endpoint body to avoid ruff F811 clash between stdlib names and Pydantic field names (mean, median, stdev are both stdlib and Pydantic field names)"
  - "Index endpoint sorts by graded_count DESC to surface most-graded assignments first for UX"
  - "graded_count uses workflow_state='graded' AND score is not None AND math.isfinite(score) for data integrity"
  - "statistics.quantiles(scores, n=4) returns [Q1, Q2, Q3]; q1=qs[0], q3=qs[2]"
  - "per_ta groups by grader_name field from get_submissions() LEFT JOIN; NULL grader_name becomes 'Unknown / Pre-Phase 6'"

patterns-established:
  - "Pattern: local statistics import inside endpoint to prevent Pydantic field name shadowing"
  - "Pattern: guard stats functions with n>=2 check before calling stdev/quantiles to avoid StatisticsError"

requirements-completed:
  - GRADE-DB-01
  - GRADE-API-01
  - GRADE-API-02
  - GRADE-STATS-01
  - GRADE-STATS-02
  - GRADE-HIST-01
  - GRADE-TA-01

# Metrics
duration: 4min
completed: 2026-03-16
---

# Phase 08 Plan 02: Grade Distribution Backend Endpoints Summary

**Two FastAPI grade-distribution endpoints with histogram bins, GradeStats (small-sample aware), and per-TA breakdown using Python statistics module and existing SQLite submissions data**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-16T03:24:58Z
- **Completed:** 2026-03-16T03:28:38Z
- **Tasks:** 2
- **Files modified:** 1 (main.py)

## Accomplishments

- Added 6 Pydantic response models (HistogramBin, GradeStats, TaGradeStats, GradeDistributionResponse, AssignmentGradeSummary, GradeDistributionIndexResponse)
- Added `compute_histogram_bins()` helper with proper closed-right last bin to catch scores at exactly points_possible
- Added GET /api/dashboard/grade-distribution/{course_id} (index) returning assignments sorted by graded_count DESC
- Added GET /api/dashboard/grade-distribution/{course_id}/{assignment_id} (detail) with full stats, histogram, and per-TA breakdown
- All 21 pytest tests in test_08_01_grade_distribution.py GREEN

## Task Commits

Each task was committed atomically:

1. **Task 1: Pydantic models and compute_histogram_bins helper** - `c29daa5` (feat)
2. **Task 2: grade-distribution index and detail endpoints** - `86fd9f5` (feat)

_Note: Task 1 commit was cleaned by pre-commit hook (removed unused statistics import that was added prematurely before endpoints existed)_

## Files Created/Modified

- `main.py` - Added 6 Pydantic models, compute_histogram_bins() helper, two new GET endpoints

## Decisions Made

- Used `import statistics as _stats` inside endpoint function body (not at module level) to avoid ruff F811 name collision: stdlib `mean`, `median`, `stdev` clash with identically-named Pydantic field names on `GradeStats` and `TaGradeStats` models.
- Index endpoint returns assignments sorted by `graded_count DESC` for most-useful default UX (most-graded first).
- `statistics.quantiles(scores, n=4)` returns a 3-element list `[Q1, Q2, Q3]`; mapping is `q1=qs[0]`, `q3=qs[2]`.
- NULL `grader_name` (from LEFT JOIN on ta_users when grader_id is NULL) maps to string `"Unknown / Pre-Phase 6"`.

## Deviations from Plan

None — plan executed exactly as written. The only deviation was the import strategy: moved `import statistics` from file-level to function-level to resolve ruff F811 name shadowing with Pydantic field names.

## Issues Encountered

- `from statistics import mean, median, stdev, quantiles` at module level caused ruff F811 errors because `GradeStats` Pydantic model defines fields also named `mean`, `median`, `stdev`. Resolution: use `import statistics as _stats` inside each endpoint function body, which ruff allows.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Both endpoints registered and tested; ready for 08-03 frontend Grade Analysis page to consume
- Endpoint contracts: index returns `{assignments: [{assignment_id, assignment_name, points_possible, graded_count}]}`; detail returns `{assignment_id, assignment_name, points_possible, stats, histogram, per_ta}`
- No blockers

---
*Phase: 08-add-grade-distribution-visualizations*
*Completed: 2026-03-16*

## Self-Check: PASSED
