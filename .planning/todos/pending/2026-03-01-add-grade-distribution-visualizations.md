---
created: 2026-03-01T16:00:54.320Z
title: Add grade distribution visualizations
area: ui
files:
  - main.py
  - database.py
  - canvas-react/src/
---

## Problem

There's no way to visualize grade distributions across assignments or compare grading patterns between TAs. The head TA can't quickly spot if a TA is grading unusually harshly or leniently compared to others.

## Solution

**Depends on: Grader Identity Tracking (for per-TA box plots)**

### Backend
- New endpoint: `GET /api/dashboard/grade-distribution/{course_id}` returning per-assignment stats (score array, mean, median, std dev, min, max, quartiles) and per-TA per-assignment stats
- Optional `assignment_id` filter

### Frontend
- New page or section: "Grade Analysis"
- **Histograms**: per-assignment bar chart showing score distribution (percentage bins)
- **Box plots**: side-by-side per TA for a selected assignment showing median, quartiles, whiskers
- Assignment selector dropdown
- Summary stats (mean, median, std dev) alongside charts
- Warning when sample size per TA is too small for meaningful comparison

### Charting
- Consider inline SVG (like existing enrollment chart) or lightweight library like Chart.js — decide at implementation time based on complexity
