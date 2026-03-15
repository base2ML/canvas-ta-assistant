---
phase: 06-grader-identity-tracking
plan: "04"
subsystem: frontend
tags: [ta-dashboard, settings, grader-identity, ui]
dependency_graph:
  requires: [06-03]
  provides: [ta-breakdown-mode-ui, actual-grader-breakdown]
  affects: [EnhancedTADashboard, Settings, App]
tech_stack:
  added: [/api/canvas/ta-users/{course_id}]
  patterns: [grader_id-based-matching, group-name-to-ta-user-id-map]
key_files:
  created: []
  modified:
    - canvas-react/src/App.jsx
    - canvas-react/src/Settings.jsx
    - canvas-react/src/EnhancedTADashboard.jsx
    - canvas-react/src/EnhancedTADashboard.test.jsx
    - canvas-react/src/Settings.test.jsx
    - database.py
    - main.py
decisions:
  - "match grader_id (not grader_name) against ta_users.id for actual-mode count accuracy — grader_name matches group name only when Canvas group is named after the TA, which is not reliable; grader_id matching is reliable whenever ta_users is populated"
  - "fallback to grader_name string match when no ta_user id mapping found for a group name"
  - "fetch ta_users in EnhancedTADashboard via new /api/canvas/ta-users/{course_id} endpoint (graceful catch so missing endpoint doesn't break dashboard)"
  - "groupNameToTaUserId map computed in separate useMemo from assignmentStats for clarity and dependency tracking"
metrics:
  duration: "~15 min"
  completed_date: "2026-03-15"
  tasks_completed: 5
  files_changed: 7
---

# Phase 06 Plan 04: TA Breakdown Mode UI + Actual-Grader Fix Summary

**One-liner:** Settings toggle for ta_breakdown_mode ('group'/'actual') with grader_id-based TA matching in EnhancedTADashboard, fixing actual-mode showing 0 graded via new /api/canvas/ta-users endpoint.

## What Was Built

- **App.jsx**: loads `ta_breakdown_mode` from `/api/settings` and threads it as prop to `EnhancedTADashboard`
- **Settings.jsx**: "TA Dashboard" card between Course Configuration and Late Day Policy, with toggle labeled "Use actual grader from Canvas (grader_id)" and dedicated "Save TA Settings" button
- **EnhancedTADashboard.jsx**: accepts `taBreakdownMode` prop (default 'group'), branches graded count in `actual` mode using `grader_id` matching via a new `groupNameToTaUserId` useMemo
- **database.py**: new `get_ta_users()` function querying `ta_users` table by course
- **main.py**: new `/api/canvas/ta-users/{course_id}` endpoint

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] actual mode showed 0 graded for all TAs**
- **Found during:** Checkpoint human-verify (user reported bug)
- **Issue:** The plan's `actual` mode branch compared `s.grader_name === taName` where `grader_name` is the TA's personal Canvas name (e.g. "Jane Smith") but `taName` is the Canvas group name (e.g. "TA Group A"). These never match.
- **Fix:** Added `get_ta_users()` in `database.py` and `/api/canvas/ta-users/{course_id}` endpoint in `main.py`. `EnhancedTADashboard` now fetches ta_users, builds a `groupNameToTaUserId` map (group name → ta_users.id via name matching), and in `actual` mode compares `s.grader_id === taUserId`. Falls back to `grader_name` string match when no id mapping found.
- **Files modified:** database.py, main.py, canvas-react/src/EnhancedTADashboard.jsx
- **Commit:** 0d23cc4

## Commits

| Hash | Message |
|------|---------|
| 7606a21 | test(06-04): add failing stubs for taBreakdownMode and Settings TA Dashboard |
| f919350 | feat(06-04): App.jsx loads and threads ta_breakdown_mode from settings |
| bd43b41 | feat(06-04): Settings TA Dashboard card with mode toggle |
| 28d0f46 | feat(06-04): EnhancedTADashboard accepts taBreakdownMode prop and branches graded count |
| 0d23cc4 | fix(06-04): resolve actual-mode graded count showing 0 for all TAs |

## Verification

- Frontend build: clean (no errors)
- Frontend tests: all new taBreakdownMode tests pass; Settings.test.jsx passes; pre-existing failures unchanged
- Backend tests: 97 passed, 0 failed

## Self-Check: PASSED

- `database.py` `get_ta_users()` added: confirmed
- `main.py` `/api/canvas/ta-users/{course_id}` endpoint added: confirmed
- `canvas-react/src/EnhancedTADashboard.jsx` taUsers state + fetch + groupNameToTaUserId useMemo: confirmed
- Commits 7606a21, f919350, bd43b41, 28d0f46, 0d23cc4: confirmed in git log
