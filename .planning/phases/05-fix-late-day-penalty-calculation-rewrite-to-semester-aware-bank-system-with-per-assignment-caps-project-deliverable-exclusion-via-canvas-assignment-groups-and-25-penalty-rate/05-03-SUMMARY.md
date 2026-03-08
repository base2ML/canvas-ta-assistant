---
phase: 05-fix-late-day-penalty-calculation
plan: 03
subsystem: api
tags: [python, fastapi, pydantic, late-days, bank-system, sse, tdd]

# Dependency graph
requires:
  - phase: 05-01
    provides: assignment_group_id column in SQLite assignments table
  - phase: 05-02
    provides: assignment_groups table, get_assignment_groups() DB function, Canvas sync for groups

provides:
  - calculate_student_late_day_summary() — semester bank drawdown algorithm in main.py
  - _compute_days_late() — grace-period-aware helper function
  - Updated SettingsResponse/SettingsUpdateRequest with 4 new late day policy fields
  - Updated get_settings() and update_settings() for total_late_day_bank, penalty_rate_per_day, per_assignment_cap, late_day_eligible_groups
  - Rewritten get_late_days_data() using bank summary with bank_remaining, bank_days_used, penalty_percent, not_accepted per assignment
  - Updated preview_comments() and post_comments() SSE loop using bank summary
  - not_accepted guard in post_comments() skipping project deliverables
  - Backward-compat aliases (days_remaining, max_late_days) in template context

affects:
  - 05-04 (frontend late days UI — consumes new bank_remaining, bank_days_used, not_accepted fields)
  - templates system (ALLOWED_TEMPLATE_VARIABLES now includes bank variables)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Pre-compute bank_summaries dict outside SSE generator, captured via closure
    - Semester-bank drawdown: chronological sort, cap by per_assignment_cap, then bank_remaining
    - Backward-compat aliases (days_remaining, max_late_days) alongside new bank variables
    - Migration fallback: per_assignment_cap falls back to max_late_days_per_assignment if not set

key-files:
  created:
    - tests/test_05_03_late_day_summary.py
    - tests/test_05_03_settings_and_late_days.py
    - tests/test_05_03_posting_flow.py
  modified:
    - main.py

key-decisions:
  - "Placed _compute_days_late() and calculate_student_late_day_summary() after calculate_late_days_for_user() without deleting old function (still referenced for backward compat)"
  - "Pre-compute bank_summaries before async SSE generator in post_comments() — pattern matches existing resolved_template_text closure pattern"
  - "Empty eligible_group_ids set means all assignments eligible (backward compat when groups not configured)"
  - "per_assignment_cap migrates from max_late_days_per_assignment if per_assignment_cap key not yet in DB"
  - "Project deliverables (ineligible groups) get not_accepted=True, penalty_percent=100, bank unchanged"

patterns-established:
  - "Semester bank approach: sort assignments chronologically, draw bank days per assignment (capped), compute penalty on remainder"
  - "backward-compat aliases: always include days_remaining and max_late_days as aliases in template context"
  - "SSE pre-computation: compute expensive per-user data before generator to avoid async issues"

requirements-completed: [LATE-ALGO-01, LATE-SETTINGS-01, LATE-TEMPLATE-01, LATE-POSTING-01]

# Metrics
duration: 7min
completed: 2026-03-01
---

# Phase 05 Plan 03: Late Day Bank Algorithm Summary

**Semester-aware bank system replacing per-assignment penalty: calculate_student_late_day_summary() with chronological drawdown, 25%/day penalty rate, project deliverable exclusion via assignment groups, and backward-compat template aliases**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-01T17:35:09Z
- **Completed:** 2026-03-01T17:42:51Z
- **Tasks:** 3
- **Files modified:** 4 (main.py + 3 new test files)

## Accomplishments

- Implemented `calculate_student_late_day_summary()` — semester bank drawdown algorithm with chronological ordering, per-assignment caps, and project deliverable exclusion
- Added `_compute_days_late()` helper extracting grace-period logic for reuse across both bank summary and old function
- Updated `SettingsResponse`, `SettingsUpdateRequest`, `get_settings()`, `update_settings()` with four new late day policy fields (total_late_day_bank, penalty_rate_per_day, per_assignment_cap, late_day_eligible_groups)
- Rewrote `get_late_days_data()` using bank summary — response now includes bank_remaining, bank_days_used, penalty_days, penalty_percent, not_accepted per assignment
- Updated `preview_comments()` and `post_comments()` SSE loop to use bank summary instead of old per-assignment function
- Added not_accepted guard in `post_comments()` to skip project deliverables and yield "skipped" event
- Added ALLOWED_TEMPLATE_VARIABLES new bank variables (bank_days_used, bank_remaining, total_bank)
- 70 tests passing (35 new tests added across 3 test files)

## Task Commits

1. **Task 1: _compute_days_late() and calculate_student_late_day_summary()** - `8ab4203` (feat)
2. **Task 2: Settings models, get/update_settings(), get_late_days_data()** - `7be6693` (feat)
3. **Task 3: preview_comments() and post_comments() SSE loop** - `c54b7d0` (feat)

## Files Created/Modified

- `main.py` — New functions, updated settings models, rewritten get_late_days_data(), updated posting flow
- `tests/test_05_03_late_day_summary.py` — 17 tests for _compute_days_late() and calculate_student_late_day_summary()
- `tests/test_05_03_settings_and_late_days.py` — 8 tests for settings models and function presence
- `tests/test_05_03_posting_flow.py` — 11 tests verifying posting flow source patterns and imports

## Decisions Made

- Preserved old `calculate_late_days_for_user()` function (not deleted) to avoid any risk of breaking imports during the plan; it can be removed in a later cleanup plan
- Pre-computed `bank_summaries` dict outside the SSE generator (before `async def event_generator()`) so semester bank is computed once per request, not per-event
- Empty `late_day_eligible_group_ids` set means all assignments are eligible — backward-compatible behavior when no groups are configured in settings
- Migration fallback: `per_assignment_cap` setting falls back to `max_late_days_per_assignment` value if `per_assignment_cap` key not yet in DB, avoiding breaking changes for existing deployments
- Project deliverables with `not_accepted=True` get `penalty_percent=100` (immediate full penalty) with no bank days consumed — per algorithm spec

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed ruff E501 line-length violations in new code**
- **Found during:** All three tasks (pre-commit hooks caught them)
- **Issue:** New functions had docstrings and comments exceeding 88-char line limit
- **Fix:** Reformatted docstrings, split long comment lines, wrapped long function calls
- **Files modified:** main.py, test files
- **Verification:** ruff check passes with no errors
- **Committed in:** Each task commit (hooks auto-fixed most, manual edits for remainder)

---

**Total deviations:** 1 auto-fixed (Rule 3 - Blocking: line length violations from ruff)
**Impact on plan:** Minor formatting fix only. No scope creep, no logic changes.

## Issues Encountered

None beyond standard ruff formatting enforcement on new code additions.

## Next Phase Readiness

- Core algorithm implementation complete — `calculate_student_late_day_summary()` passes all three CONTEXT.md example calculations
- All API endpoints updated to return bank-aware fields (bank_remaining, bank_days_used, penalty_days, penalty_percent, not_accepted)
- Settings endpoints ready for frontend configuration of all four new policy fields
- Frontend (05-04) can now consume the enriched late days response with bank summary data

## Self-Check: PASSED

- main.py: FOUND
- tests/test_05_03_late_day_summary.py: FOUND
- tests/test_05_03_settings_and_late_days.py: FOUND
- tests/test_05_03_posting_flow.py: FOUND
- Commit 8ab4203: FOUND
- Commit 7be6693: FOUND
- Commit c54b7d0: FOUND
- All 70 tests pass

---
*Phase: 05-fix-late-day-penalty-calculation*
*Completed: 2026-03-01*
