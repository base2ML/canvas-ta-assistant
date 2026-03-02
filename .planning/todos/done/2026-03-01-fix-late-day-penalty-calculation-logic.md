---
created: 2026-03-01T16:00:54.320Z
title: Fix late day penalty calculation logic
area: api
files:
  - main.py:362-432
  - main.py:1545-1634
  - canvas-react/src/LateDaysTracking.jsx
  - database.py:330-380
---

## Problem

The `calculate_late_days_for_user` function (main.py:362-432) and the late days tracking endpoint (main.py:1545-1634) have fundamentally incorrect penalty logic. Four specific issues:

### 1. No semester-wide late day bank
The system has no concept of a cumulative 10-day semester bank. It only tracks a per-assignment cap (`max_late_days`, default 7). `days_remaining` is calculated per-assignment, not as remaining from the semester total across all assignments.

### 2. Penalty calculation is wrong
Current logic (main.py:415-416):
```python
penalty_days = min(days_late, max_late_days)  # caps at 7
penalty_percent = penalty_days * 10           # 10% per day
```
This applies penalty to ALL late days up to the cap. The correct behavior is: late days within the bank should NOT incur a penalty. Only days BEYOND what the bank covers should be penalized.

### 3. No project deliverable exclusion
All assignments with due dates are treated the same. Project deliverables should not accept late submissions at all — any late project submission should show as not accepted / full penalty.

### 4. Penalty rate is wrong
Current: 10% per day. Correct: 25% of earned grade per penalty day.

## Solution

### Correct late day policy

- **Semester bank**: 10 late days total across all assignments
- **Per-assignment cap**: 7 late days maximum on any single assignment
- **Project deliverables**: not accepted late — show as "Not Accepted" with zero grade
- **Penalty**: only applies to days BEYOND what the bank covers, at 25% of earned grade per penalty day, capped at 100% (zero grade)
- **Bank deduction**: penalty days do NOT deduct from the bank (no double penalty)
- **Project identification**: via Canvas assignment groups — head TA selects which assignment groups allow late days in Settings

### Example calculations

**Example 1**: Student submits 9 days late, has full 10-day bank:
- 7 days deducted from bank (per-assignment cap)
- 2 remaining late days become penalty days
- Bank balance: 10 - 7 = 3 days remaining
- Penalty: 2 × 25% = 50% deduction from earned grade

**Example 2**: Student submits 3 days late, has 1 bank day left:
- 1 day deducted from bank
- 2 penalty days
- Bank balance: 0
- Penalty: 2 × 25% = 50%

**Example 3**: Student submits project deliverable 2 days late:
- "Not Accepted" — zero grade, no bank days consumed

### Implementation approach: Two-Pass Calculation

**Pass 1 — Bank allocation (per student, all assignments):**
1. Sort all assignments by due date (chronological) — due date determines processing order, not submission date
2. Start with `bank_remaining = total_late_day_bank` (default 10)
3. For each assignment:
   - If assignment group is NOT in the "allows late days" list → skip (project deliverable — "Not Accepted" if late)
   - Calculate raw `days_late` (existing grace period logic)
   - `applicable_late_days = min(days_late, per_assignment_cap)` (cap at 7)
   - `bank_days_used = min(applicable_late_days, bank_remaining)`
   - `penalty_days = days_late - bank_days_used`
   - `penalty_percent = min(penalty_days × 25, 100)` (cap at 100%)
   - `bank_remaining -= bank_days_used`
   - Store per-assignment results

**Pass 2 — Comment rendering (per student, single assignment):**
- Look up pre-computed values from Pass 1
- Template variables: `days_late`, `bank_days_used`, `bank_remaining`, `penalty_days`, `penalty_percent`, `total_bank`, `max_late_days`

### Required changes

**Canvas sync** (canvas_sync.py):
- Sync assignment groups from Canvas (`course.get_assignment_groups()`)
- Store `assignment_group_id` on assignments table
- New `assignment_groups` table: id, course_id, name

**Settings** (database.py / main.py):
- Add `total_late_day_bank` setting (default: 10)
- Add `penalty_rate_per_day` setting (default: 25, as percentage)
- Add `late_day_eligible_groups` setting (JSON array of assignment group IDs that allow late days)
- Settings UI: multi-select for which Canvas assignment groups allow late submissions

**Backend** (main.py):
- Rewrite `calculate_late_days_for_user` → new `calculate_student_late_day_summary` that processes ALL assignments for a student semester-wide
- Update `get_late_days_data` endpoint to include bank balance per student and per-assignment breakdown (bank_days_used vs penalty_days)
- Update comment preview/post flow to use corrected calculations
- Project deliverables submitted late: return "not_accepted" status

**Frontend** (LateDaysTracking.jsx):
- Display semester bank balance per student (new column)
- Distinguish between "bank days used" (no penalty) and "penalty days" in the UI with different colors
- Mark project deliverables as "Not Accepted" if late (distinct visual treatment)
- Update comment templates to reflect correct penalty variables

**Frontend** (Settings.jsx):
- New section: "Late Day Policy" with bank size, penalty rate, per-assignment cap inputs
- Multi-select for Canvas assignment groups that allow late submissions

**Comment templates** (database.py default templates):
- Update template variables: add `bank_days_used`, `bank_remaining`, `total_bank`
- Update `penalty_percent` to use 25% rate
- Update default template text to reflect correct policy
