# Canvas Data Structures Documentation

## Overview

This document describes the data structures extracted from the Canvas LMS API and stored in SQLite for the Canvas TA Dashboard application. Data is synced on application startup and can be manually refreshed via the Settings page or Refresh button.

## Table of Contents

- [Database Structure](#database-structure)
- [Data Refresh Process](#data-refresh-process)
- [Core Data Entities](#core-data-entities)
  - [Assignments](#1-assignments)
  - [Submissions](#2-submissions)
  - [Users](#3-users)
  - [Groups](#4-groups)
- [Data Relationships](#data-relationships)
- [API Endpoints](#api-endpoints)
- [Data Processing](#data-processing)

---

## Database Structure

Data is stored in a SQLite database at `./data/canvas.db` with the following schema:

### Tables Overview

| Table | Purpose |
|-------|---------|
| `settings` | Application configuration (course ID, etc.) |
| `assignments` | Canvas assignments |
| `users` | Enrolled students |
| `submissions` | Assignment submissions |
| `groups` | TA grading groups |
| `group_members` | Group membership |
| `sync_history` | Data sync history |

### Schema Details

```sql
-- Application settings
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Canvas assignments
CREATE TABLE assignments (
    id INTEGER PRIMARY KEY,
    course_id TEXT NOT NULL,
    name TEXT NOT NULL,
    due_at TIMESTAMP,
    points_possible REAL,
    html_url TEXT,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Canvas users (students)
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    course_id TEXT NOT NULL,
    name TEXT NOT NULL,
    email TEXT,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Canvas submissions
CREATE TABLE submissions (
    id INTEGER PRIMARY KEY,
    course_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    assignment_id INTEGER NOT NULL,
    submitted_at TIMESTAMP,
    workflow_state TEXT,
    late BOOLEAN DEFAULT FALSE,
    score REAL,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (assignment_id) REFERENCES assignments(id)
);

-- Canvas groups (TA groups)
CREATE TABLE groups (
    id INTEGER PRIMARY KEY,
    course_id TEXT NOT NULL,
    name TEXT NOT NULL,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Group membership
CREATE TABLE group_members (
    group_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    name TEXT,
    PRIMARY KEY (group_id, user_id),
    FOREIGN KEY (group_id) REFERENCES groups(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Sync history
CREATE TABLE sync_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

---

## Data Refresh Process

### Startup Sync

When the application starts:

1. Database is initialized (tables created if not exist)
2. If `CANVAS_COURSE_ID` is configured:
   - Connects to Canvas API using `canvasapi` library
   - Fetches assignments, users, submissions, groups
   - Stores data in SQLite tables
   - Records sync in `sync_history` table

### Manual Refresh

Users can trigger manual data refresh via:

- **Settings Page**: Click "Sync Now" button
- **Dashboard**: Click "Refresh Data" button in header
- **API Endpoint**: `POST /api/canvas/sync`

**Sync Process**:

1. Clears existing course data from tables
2. Fetches fresh data from Canvas API
3. Inserts new data into SQLite
4. Updates `sync_history` table

---

## Core Data Entities

### 1. Assignments

**Description**: Course assignments fetched from Canvas API

**Source**: `course.get_assignments()`

**Table**: `assignments`

**Data Structure**:

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Canvas assignment ID (primary key) |
| `course_id` | TEXT | Course identifier |
| `name` | TEXT | Assignment title |
| `due_at` | TIMESTAMP | Due date/time (nullable) |
| `points_possible` | REAL | Maximum points (nullable) |
| `html_url` | TEXT | Link to assignment in Canvas |
| `synced_at` | TIMESTAMP | When data was synced |

**Notes**:

- `due_at` may be NULL for assignments without due dates
- `points_possible` may be NULL for ungraded assignments

---

### 2. Submissions

**Description**: Student submission data for all assignments

**Source**: `assignment.get_submissions()`

**Table**: `submissions`

**Data Structure**:

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Submission ID (primary key) |
| `course_id` | TEXT | Course identifier |
| `user_id` | INTEGER | Student's Canvas user ID |
| `assignment_id` | INTEGER | Associated assignment ID |
| `submitted_at` | TIMESTAMP | Submission timestamp (nullable) |
| `workflow_state` | TEXT | Submission status |
| `late` | BOOLEAN | Whether submission was late |
| `score` | REAL | Graded score (nullable) |
| `synced_at` | TIMESTAMP | When data was synced |

**Workflow States**:

| State | Description |
|-------|-------------|
| `unsubmitted` | No submission has been made |
| `submitted` | Submission made, awaiting grading |
| `pending_review` | Under review |
| `graded` | Submission has been graded |

---

### 3. Users

**Description**: Students enrolled in the course

**Source**: `course.get_users(enrollment_type=['student'])`

**Table**: `users`

**Data Structure**:

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Canvas user ID (primary key) |
| `course_id` | TEXT | Course identifier |
| `name` | TEXT | Student's full name |
| `email` | TEXT | Student's email (nullable) |
| `synced_at` | TIMESTAMP | When data was synced |

**Privacy Notes**:

- Student names and emails are PII protected under FERPA
- Data stored locally in SQLite database

---

### 4. Groups

**Description**: TA grading groups for workload distribution

**Source**: `course.get_groups(include=['users'])`

**Tables**: `groups` and `group_members`

**Groups Table**:

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Canvas group ID (primary key) |
| `course_id` | TEXT | Course identifier |
| `name` | TEXT | Group name (typically TA name) |
| `synced_at` | TIMESTAMP | When data was synced |

**Group Members Table**:

| Column | Type | Description |
|--------|------|-------------|
| `group_id` | INTEGER | Group ID (foreign key) |
| `user_id` | INTEGER | User ID (foreign key) |
| `name` | TEXT | Member's full name |

---

## Data Relationships

### Entity Relationship Diagram

```
┌──────────────┐
│  assignments │
│              │
│ id (PK)      │◄────────┐
│ course_id    │         │
│ name         │         │
│ due_at       │         │
└──────────────┘         │
                         │ assignment_id (FK)
                         │
┌──────────────┐         │
│    users     │         │
│              │         │
│ id (PK)      │◄───┐    │
│ course_id    │    │    │
│ name         │    │    │
│ email        │    │    │
└──────────────┘    │    │
                    │    │
         ┌──────────┼────┼────────────┐
         │          │    │            │
         │ user_id  │    │            │
         │ (FK)     │    │            │
┌────────▼──────────▼────▼─────┐      │
│      submissions              │      │
│                               │      │
│ id (PK)                       │      │
│ user_id (FK)     ─────────────┘      │
│ assignment_id (FK) ──────────────────┘
│ submitted_at                  │
│ workflow_state                │
│ late, score                   │
└───────────────────────────────┘

┌──────────────┐     ┌──────────────────┐
│    groups    │     │  group_members   │
│              │     │                  │
│ id (PK)      │◄────│ group_id (FK)    │
│ course_id    │     │ user_id (FK)     │────► users.id
│ name         │     │ name             │
└──────────────┘     └──────────────────┘
```

---

## API Endpoints

### Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings` | Get current settings |
| PUT | `/api/settings` | Update settings |
| GET | `/api/settings/courses` | List available Canvas courses |

### Canvas Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/canvas/courses` | List configured courses |
| GET | `/api/canvas/assignments/{course_id}` | Get assignments from SQLite |
| GET | `/api/canvas/submissions/{course_id}` | Get submissions from SQLite |
| GET | `/api/canvas/users/{course_id}` | Get users from SQLite |
| GET | `/api/canvas/groups/{course_id}` | Get groups from SQLite |

### Sync

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/canvas/sync` | Trigger Canvas data sync |
| GET | `/api/canvas/sync/status` | Get last sync status |

---

## Data Processing

### Submission Status Classification

The backend classifies submissions into categories:

| Status | Condition |
|--------|-----------|
| `missing` | `workflow_state` is 'unsubmitted' or no `submitted_at` |
| `late` | `late` flag is true or submitted after due date |
| `on_time` | Submitted before due date and not marked late |

### Database Operations

Key database operations in `database.py`:

- `init_db()` - Create tables if not exist
- `get_setting(key)` / `set_setting(key, value)` - Settings CRUD
- `upsert_assignments(course_id, assignments)` - Bulk insert/update
- `upsert_submissions(course_id, submissions)` - Bulk insert/update
- `upsert_users(course_id, users)` - Bulk insert/update
- `upsert_groups(course_id, groups)` - Bulk insert/update
- `get_assignments(course_id)` - Query assignments
- `get_submissions(course_id)` - Query submissions
- `clear_course_data(course_id)` - Delete before re-sync

---

## Security and Privacy

### Data Classification

| Data Type | Classification | FERPA Protected |
|-----------|----------------|-----------------|
| Assignments | Public | No |
| Users (names, emails) | PII | Yes |
| Submissions | Educational Records | Yes |
| Grades (scores) | Educational Records | Yes |
| Groups | Internal | No |

### Local Storage Security

- SQLite database stored at `./data/canvas.db`
- Database file persisted via Docker volume
- No encryption at rest (local deployment)
- Access controlled by file system permissions

### Best Practices

- Never commit `data/` directory to version control
- Handle student data according to FERPA guidelines
- Regenerate Canvas API tokens periodically

---

## Troubleshooting

### Common Issues

**No data for course ID**:

- Verify course ID is correct
- Check Canvas API token is valid
- Try manual sync via Settings page

**Stale data**:

- Click "Refresh Data" or "Sync Now"
- Check sync history in Settings page

**Database errors**:

- Check logs: `docker-compose logs backend`
- Reset database: `docker-compose down -v && docker-compose up`

### Debugging

```bash
# View SQLite database
sqlite3 ./data/canvas.db

# List tables
.tables

# View assignments
SELECT * FROM assignments LIMIT 10;

# View sync history
SELECT * FROM sync_history ORDER BY started_at DESC LIMIT 5;
```

---

## References

- **Canvas API Documentation**: https://canvas.instructure.com/doc/api/
- **CanvasAPI Python Library**: https://canvasapi.readthedocs.io/en/stable/
- **SQLite Documentation**: https://sqlite.org/docs.html
