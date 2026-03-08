---
created: 2026-03-01T16:00:54.320Z
title: Add TA grading deadlines
area: general
files:
  - database.py
  - main.py
  - canvas-react/src/EnhancedTADashboard.jsx
  - canvas-react/src/Settings.jsx
---

## Problem

There's no way to set or track grading deadlines for TAs. The head TA can see what's ungraded but can't tell if a TA is behind schedule. Homework assignments have a fixed turnaround, but project assignments have per-assignment deadlines, so the system needs both a global default and per-assignment overrides.

## Solution

**Depends on: Grader Identity Tracking (must be built first)**

### Configuration
- **Global default** in Settings: "Default Grading Turnaround" number input (days after due date)
- **Per-assignment override**: set inline on the main dashboard next to each assignment

### Backend
- New `grading_deadlines` table: `assignment_id` (PK), `course_id`, `deadline` (TIMESTAMP), `days_after_due` (INTEGER), `is_override` (BOOLEAN)
- New setting: `default_grading_turnaround_days`
- Endpoints: `PUT/GET/DELETE /api/grading-deadlines/{assignment_id|course_id}`
- Update submission status endpoint to include "grading overdue" status per TA per assignment

### Frontend
- Settings: add default turnaround days input
- Dashboard: inline deadline display per assignment with edit capability
- Red highlight/badge on assignments where grading deadline has passed with ungraded submissions
- "Overdue" badge in TA breakdown for TAs who haven't finished grading past deadline
- Summary card: "X assignments with overdue grading"
- **Grading Schedule Summary**: a shareable view showing all assignments with their grading deadlines in chronological order, so the head TA can share with the TA team (e.g., copy link or export). Should include: assignment name, due date, grading deadline, status (upcoming/overdue/complete). This could be a dedicated page or a printable/exportable section.
