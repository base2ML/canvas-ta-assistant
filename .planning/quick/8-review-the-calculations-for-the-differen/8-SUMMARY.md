---
phase: quick-8
plan: "01"
subsystem: late-days
tags: [fix, templates, bank-system]
dependency_graph:
  requires: []
  provides: [canonical-template-variables, cumulative-bank-days-used]
  affects: [main.py, database.py, canvas-react/src/Settings.jsx]
tech_stack:
  added: []
  patterns: [cumulative-running-total, canonical-variable-naming]
key_files:
  modified:
    - main.py
    - database.py
    - canvas-react/src/Settings.jsx
    - tests/test_05_03_late_day_summary.py
    - tests/test_05_03_posting_flow.py
decisions:
  - "bank_days_used is now cumulative (total_bank - bank_remaining) not per-assignment draw; computed via rename of local var to 'draw' to avoid shadowing"
  - "Old calculate_late_days_for_user() kept intact (backward-compat, preserved per Phase 05-03 decision) — its internal days_remaining and max_late_days locals are separate from the template variable system"
  - "Tests updated to assert cumulative semantics and that alias variables are absent from ALLOWED_TEMPLATE_VARIABLES"
metrics:
  duration: "~5 min"
  completed: "2026-03-06"
  tasks_completed: 2
  files_modified: 5
---

# Quick-8 Summary: Fix bank_days_used cumulative semantics and remove alias template variables

**One-liner:** Corrected bank_days_used to store cumulative days drawn across all assignments and removed confusing alias variables (days_remaining, max_late_days) from the template variable system.

## What Was Changed

### Task 1: Fix bank_days_used and remove aliases from main.py (commit a18b065)

**ALLOWED_TEMPLATE_VARIABLES** — reduced from 8 to 6 canonical entries:
- Removed `"days_remaining"` (was alias for bank_remaining)
- Removed `"max_late_days"` (was alias for per_assignment_cap)
- Remaining: `days_late`, `penalty_days`, `penalty_percent`, `bank_days_used`, `bank_remaining`, `total_bank`

**calculate_student_late_day_summary()** — fixed bank_days_used semantics in all three loop branches:
- Zero-late branch: `"bank_days_used": total_bank - bank_remaining` (cumulative before this assignment, bank unchanged)
- Not-eligible branch: `"bank_days_used": total_bank - bank_remaining` (cumulative, no draw)
- Bank-eligible branch: renamed local `bank_days_used` to `draw` to avoid shadowing, then `"bank_days_used": total_bank - bank_remaining` after `bank_remaining -= draw`

**Both posting endpoint variable_data dicts** — removed `days_remaining` and `max_late_days` keys:
- Single-post endpoint (~line 1029): removed 2 keys + comment
- Bulk-post SSE endpoint (~line 1265): removed 2 keys + comment

**Tests updated** (deviation Rule 1 — tests encoded old per-assignment semantics):
- `tests/test_05_03_late_day_summary.py`: updated `test_assignments_sorted_by_due_at_for_bank_deduction` assertion from 1 to 6 (cumulative); renamed `test_backward_compat_variables_present` to `test_canonical_variables_present`, replaced affirmative assertions for aliases with negative assertions
- `tests/test_05_03_posting_flow.py`: removed two source-pattern tests that asserted alias presence; updated `test_allowed_template_variables_has_all_bank_vars` to assert aliases are absent

### Task 2: Update default templates in database.py and Settings.jsx (commit 1812a4f)

**database.py populate_default_templates():**
- Penalty template: replaced `{days_remaining}` → `{bank_remaining}`, `{max_late_days}` → removed, added `Bank days used (cumulative): {bank_days_used}` line; template_variables list now `["days_late", "bank_days_used", "bank_remaining", "penalty_days", "penalty_percent"]`
- Non-penalty template: replaced `{days_remaining}` → `{bank_remaining}`, removed `{max_late_days}` line, added `Bank days used (cumulative): {bank_days_used}` line; template_variables list now `["days_late", "bank_days_used", "bank_remaining"]`

**canvas-react/src/Settings.jsx:**
- Available Variables array trimmed from 8 to 6 tokens: removed `'{days_remaining}'` and `'{max_late_days}'`

## Verification

- 68 backend tests pass (0 failures)
- Frontend builds cleanly (vite 790ms, no errors)
- `ALLOWED_TEMPLATE_VARIABLES` has exactly 6 entries
- No `"days_remaining"` or `"max_late_days"` string-literal keys in variable_data/late_days_data dicts or in ALLOWED_TEMPLATE_VARIABLES

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated tests encoding old per-assignment bank_days_used semantics**
- Found during: Task 1 verification
- Issue: Two test files had assertions/source checks for alias variables and per-assignment (non-cumulative) bank_days_used values
- Fix: Updated assertions in `test_05_03_late_day_summary.py` and `test_05_03_posting_flow.py` to match new cumulative semantics and absence of alias variables
- Files modified: tests/test_05_03_late_day_summary.py, tests/test_05_03_posting_flow.py
- Commits: a18b065

## Self-Check

- [x] main.py exists and modified
- [x] database.py exists and modified
- [x] canvas-react/src/Settings.jsx exists and modified
- [x] Commit a18b065 exists
- [x] Commit 1812a4f exists
- [x] 68 tests pass
- [x] Frontend builds without errors

## Self-Check: PASSED
