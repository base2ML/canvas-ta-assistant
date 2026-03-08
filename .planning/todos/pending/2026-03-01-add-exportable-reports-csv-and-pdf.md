---
created: 2026-03-01T16:00:54.320Z
title: Add exportable reports CSV and PDF
area: general
files:
  - main.py
  - canvas-react/src/LateDaysTracking.jsx
  - canvas-react/src/EnhancedTADashboard.jsx
  - canvas-react/src/PeerReviewTracking.jsx
---

## Problem

The head TA cannot export dashboard data for offline analysis or to share with the instructor. All data is only viewable in the browser. CSV is needed for spreadsheet analysis, PDF for sharing formatted reports.

## Solution

**Should be built last — exports data from all other features.**

### What to export
- Late days matrix
- Grading progress
- Peer review penalties
- At-risk student list (once built)
- Grade distributions (once built)

### Backend
- New export endpoints with `format` query param:
  - `GET /api/export/late-days/{course_id}?format=csv|pdf`
  - `GET /api/export/grading-progress/{course_id}?format=csv|pdf`
  - `GET /api/export/peer-reviews/{course_id}?format=csv|pdf`
  - `GET /api/export/at-risk/{course_id}?format=csv|pdf`
  - `GET /api/export/grade-distribution/{course_id}?format=csv|pdf`
- CSV: Python `csv` module, `text/csv` content type
- PDF: lightweight library (reportlab or weasyprint) — evaluate at implementation time
- All exports include: course name, export date, applied filters

### Frontend
- "Export" dropdown button on each page (Download CSV, Download PDF)
- Loading indicator during generation
- Consider starting with CSV only, adding PDF later

### Considerations
- FERPA: add disclaimer/header on PDF reports
- Consider option to anonymize (student IDs instead of names)
- Large courses: consider streaming for CSV
