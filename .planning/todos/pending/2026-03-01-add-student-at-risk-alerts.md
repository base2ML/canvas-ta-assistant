---
created: 2026-03-01T16:00:54.320Z
title: Add student at-risk alerts
area: general
files:
  - main.py
  - database.py
  - canvas-react/src/EnhancedTADashboard.jsx
  - canvas-react/src/
---

## Problem

The head TA has no proactive way to identify students who are struggling. Late days, missing submissions, and grade trends exist in separate views but are not combined into actionable alerts. Students can fall through the cracks until it's too late to intervene.

## Solution

### Risk signals (all combined)
1. Late days accumulation exceeding threshold
2. Missing submission count exceeding threshold
3. Declining or consistently below-average grades

### Configuration (in Settings)
- `at_risk_late_days_threshold` (default: 5)
- `at_risk_missing_threshold` (default: 2)
- `at_risk_grade_threshold` (default: 70% of points possible)
- Configurable per course via existing settings table

### Backend
- New endpoint: `GET /api/dashboard/at-risk/{course_id}` returning:
  - At-risk student list with name, email, TA group, triggered risk factors, severity (1-3 signals)
  - Per-student detail: late days total, missing count, avg grade, grade trend (improving/declining/stable)
  - Summary: total at-risk count, breakdown by severity

### Frontend
- **Dashboard summary card**: "X students at risk" with severity breakdown, linking to detail page
- **New "At Risk" nav tab**: dedicated page with:
  - Filter by risk severity and TA group
  - Student table with risk factor columns and color coding
  - Click-to-expand per-assignment detail per student
  - Quick link to student Canvas profile
- Risk levels: Low (1 signal), Medium (2), High (3)
- Grade trend needs 3-4+ graded assignments — show "insufficient data" otherwise
- Exclude dropped students
