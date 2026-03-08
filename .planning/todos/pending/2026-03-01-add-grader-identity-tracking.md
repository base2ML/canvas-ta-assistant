---
created: 2026-03-01T16:00:54.320Z
title: Add grader identity tracking
area: general
files:
  - canvas_sync.py
  - database.py
  - main.py
  - canvas-react/src/EnhancedTADashboard.jsx
---

## Problem

The dashboard tracks submission scores but not WHO graded each submission or WHEN it was graded. This means the head TA cannot measure TA grading turnaround times or identify which TA graded what. The `grader_id` and `graded_at` fields are available from the Canvas API but are not currently synced. Additionally, only student users are fetched — TA/instructor users are not synced, so grader IDs can't be resolved to names.

## Solution

**Build order: This should be built FIRST — it's a data foundation that unlocks TA Grading Deadlines and Grade Distribution features.**

### Backend
- Add `grader_id` (INTEGER, nullable) and `graded_at` (TIMESTAMP, nullable) columns to `submissions` table
- Sync TA/instructor users: `course.get_users(enrollment_type=['ta', 'teacher'])` — store with a `role` column or separate `ta_users` table
- Update `canvas_sync.py` to fetch `grader_id` and `graded_at` from submission data
- New endpoint: `GET /api/dashboard/grading-activity/{course_id}` returning per-TA stats (total graded, avg turnaround time, per-assignment counts)

### Settings
- New setting: `ta_breakdown_mode` with two options:
  - **"groups"** (default) — TA breakdown table is driven by TA grading groups (current behavior). Shows grading status per group regardless of who actually graded. Best for courses where groups define responsibility.
  - **"grader"** — TA breakdown table is driven by `grader_id`. Shows who actually graded each submission. Best for courses where any TA can grade any student.
- Configurable per course in Settings page

### Frontend
- Update TA breakdown table in EnhancedTADashboard to respect `ta_breakdown_mode` setting
- When mode is "grader": group submissions by `grader_id` instead of TA group membership
- When mode is "groups": keep current behavior but optionally show actual grader name as secondary info
- Add turnaround time column to TA breakdown
- Both "who graded what" and "turnaround time" views are equally important
