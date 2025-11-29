# Canvas Data Structures Documentation

## Overview

This document describes the data structures extracted from the Canvas LMS API and stored in AWS S3 buckets for the Canvas TA Dashboard application. The data is refreshed every 15 minutes by the `canvas_data_fetcher` Lambda function and consumed by the FastAPI backend and React frontend.

## Table of Contents

- [S3 Bucket Structure](#s3-bucket-structure)
- [Data Refresh Process](#data-refresh-process)
- [Core Data Entities](#core-data-entities)
  - [Assignments](#1-assignments)
  - [Submissions](#2-submissions)
  - [Users](#3-users)
  - [Groups](#4-groups)
  - [Enrollments](#5-enrollments)
- [Authentication Data](#authentication-data)
- [Data Relationships](#data-relationships)
- [API Endpoints](#api-endpoints)
- [Data Processing](#data-processing)

---

## S3 Bucket Structure

Data is stored in the S3 bucket specified by the `S3_BUCKET_NAME` environment variable with the following structure:

```
s3://YOUR_BUCKET_NAME/
├── canvas_data/
│   └── course_{COURSE_ID}/
│       ├── latest.json                      # Complete course data (all entities combined)
│       ├── latest_assignments.json          # Assignment data only
│       ├── latest_submissions.json          # Submission data only
│       ├── latest_users.json                # User data only
│       ├── latest_groups.json               # Group data only
│       └── latest_enrollments.json          # Enrollment data (currently unused)
└── auth/
    └── users.json                            # Application user authentication data
```

### File Formats

All files are stored as:
- **Format**: JSON with indentation (pretty-printed)
- **Content-Type**: `application/json`
- **Encryption**: AES256 Server-Side Encryption (SSE-S3)

### Course ID Variants

The system supports both short and long form Canvas course IDs:
- **Short form**: `516212` (last 6 digits)
- **Long form**: `20960000000516212` (full Canvas course ID)

The application automatically tries both formats when accessing data.

---

## Data Refresh Process

### Automated Updates

- **Frequency**: Every 15 minutes (via CloudWatch EventBridge rule)
- **Lambda Function**: `canvas_data_fetcher.py`
- **Process**:
  1. Retrieves Canvas API token from AWS Secrets Manager or environment variable
  2. Connects to Canvas API using `canvasapi` library
  3. Fetches all data entities for the configured course
  4. Transforms data to simplified JSON format
  5. Stores complete data in `latest.json`
  6. Stores individual entity files for backwards compatibility
  7. Adds timestamp metadata

### Manual Refresh

Users can trigger manual data refresh via:
- **Endpoint**: `POST /api/canvas/sync`
- **Authentication**: Requires valid JWT token
- **Process**: Asynchronously invokes the Canvas data fetcher Lambda function

---

## Core Data Entities

### 1. Assignments

**Description**: Course assignments fetched from Canvas API

**Source**: `course.get_assignments(per_page=100)`

**S3 Storage**:
- `canvas_data/course_{COURSE_ID}/latest_assignments.json`
- Included in `latest.json` under `assignments` key

**Data Structure**:

```json
{
  "assignments": [
    {
      "id": 123456,
      "name": "Homework 1",
      "due_at": "2025-02-15T23:59:00Z",
      "points_possible": 100.0,
      "html_url": "https://canvas.instructure.com/courses/516212/assignments/123456"
    }
  ]
}
```

**Field Definitions**:

| Field | Type | Description | Required | Source |
|-------|------|-------------|----------|--------|
| `id` | integer | Unique Canvas assignment ID | Yes | `assignment.id` |
| `name` | string | Assignment title/name | Yes | `assignment.name` |
| `due_at` | string (ISO 8601) | Due date/time in UTC | No | `assignment.due_at` |
| `points_possible` | float | Maximum points for assignment | No | `assignment.points_possible` |
| `html_url` | string (URL) | Direct link to assignment in Canvas | No | `assignment.html_url` |

**Notes**:
- `due_at` may be `null` for assignments without due dates
- `points_possible` may be `null` for ungraded assignments
- All assignments are fetched regardless of status (published/unpublished)

---

### 2. Submissions

**Description**: Student submission data for all assignments

**Source**: `assignment.get_submissions(include=['submission_history'])`

**S3 Storage**:
- `canvas_data/course_{COURSE_ID}/latest_submissions.json`
- Included in `latest.json` under `submissions` key

**Data Structure**:

```json
{
  "submissions": [
    {
      "id": 789012,
      "user_id": 345678,
      "assignment_id": 123456,
      "submitted_at": "2025-02-14T18:30:00Z",
      "workflow_state": "submitted",
      "late": false,
      "score": 95.0
    }
  ]
}
```

**Field Definitions**:

| Field | Type | Description | Required | Source |
|-------|------|-------------|----------|--------|
| `id` | integer | Unique submission ID | Yes | `submission.id` |
| `user_id` | integer | Canvas user ID of student | Yes | `submission.user_id` |
| `assignment_id` | integer | Associated assignment ID | Yes | `assignment.id` |
| `submitted_at` | string (ISO 8601) | Submission timestamp in UTC | No | `submission.submitted_at` |
| `workflow_state` | string | Submission status | Yes | `submission.workflow_state` |
| `late` | boolean | Whether submission was late | No | `submission.late` |
| `score` | float | Graded score (null if ungraded) | No | `submission.score` |

**Workflow States**:

| State | Description |
|-------|-------------|
| `unsubmitted` | No submission has been made |
| `submitted` | Submission made, awaiting grading |
| `pending_review` | Under review by instructor/TA |
| `graded` | Submission has been graded |

**Notes**:
- A submission record exists for every student-assignment pair, even if unsubmitted
- `submitted_at` is `null` for unsubmitted assignments
- `late` defaults to `false` if not provided by Canvas API
- `score` is `null` until grading is complete

---

### 3. Users

**Description**: Students enrolled in the course

**Source**: `course.get_users(enrollment_type=['student'])`

**S3 Storage**:
- `canvas_data/course_{COURSE_ID}/latest_users.json`
- Included in `latest.json` under `users` key

**Data Structure**:

```json
{
  "users": [
    {
      "id": 345678,
      "name": "Jane Doe",
      "email": "jdoe3@gatech.edu"
    }
  ]
}
```

**Field Definitions**:

| Field | Type | Description | Required | Source |
|-------|------|-------------|----------|--------|
| `id` | integer | Unique Canvas user ID | Yes | `user.id` |
| `name` | string | Student's full name | Yes | `user.name` |
| `email` | string (email) | Student's email address | No | `user.email` |

**Notes**:
- Only students are fetched (not instructors, TAs, or observers)
- `email` may be `null` if not provided by Canvas or privacy settings prevent access
- User data is sensitive and protected under FERPA

**Privacy Considerations**:
- Student names and emails are Personally Identifiable Information (PII)
- Never log or expose this data in client-side code
- Ensure proper authentication before serving user data

---

### 4. Groups

**Description**: TA grading groups for workload distribution

**Source**: `course.get_groups(per_page=100, include=['users'])`

**S3 Storage**:
- `canvas_data/course_{COURSE_ID}/latest_groups.json`
- Included in `latest.json` under `groups` key

**Data Structure**:

```json
{
  "groups": [
    {
      "id": 901234,
      "name": "TA Group - Alice",
      "members": [
        {
          "id": 345678,
          "user_id": 345678,
          "name": "Jane Doe"
        },
        {
          "id": 345679,
          "user_id": 345679,
          "name": "John Smith"
        }
      ]
    }
  ]
}
```

**Field Definitions**:

**Group Object**:

| Field | Type | Description | Required | Source |
|-------|------|-------------|----------|--------|
| `id` | integer | Unique Canvas group ID | Yes | `group.id` |
| `name` | string | Group name (typically TA name) | Yes | `group.name` |
| `members` | array | List of member objects | Yes | `group.users` |

**Member Object**:

| Field | Type | Description | Required | Source |
|-------|------|-------------|----------|--------|
| `id` | integer | Member ID (same as user_id) | Yes | `member.id` |
| `user_id` | integer | Canvas user ID | Yes | `member.id` |
| `name` | string | Member's full name | Yes | `member.name` |

**Notes**:
- Groups with "Term Project" in the name are filtered out by default
- Members include both `id` and `user_id` fields for compatibility
- Groups are used for TA workload distribution and submission filtering
- Empty groups are included if they exist in Canvas

---

### 5. Enrollments

**Description**: Course enrollment data (currently unused but reserved)

**Source**: Not currently fetched (placeholder in data structure)

**S3 Storage**:
- `canvas_data/course_{COURSE_ID}/latest_enrollments.json`
- Included in `latest.json` as empty array

**Data Structure**:

```json
{
  "enrollments": []
}
```

**Notes**:
- This field is reserved for future use
- Could be populated with enrollment type, status, and section information
- Currently returns empty array

---

## Complete Data Structure

The `latest.json` file contains all entities combined with metadata:

```json
{
  "course_id": "516212",
  "timestamp": "2025-11-28T15:30:00.123456Z",
  "assignments": [...],
  "submissions": [...],
  "users": [...],
  "groups": [...],
  "enrollments": []
}
```

**Metadata Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `course_id` | string | Course identifier (short or long form) |
| `timestamp` | string (ISO 8601) | Data refresh timestamp in UTC |

---

## Authentication Data

### User Authentication

**Description**: Application users (TAs, instructors, admins) with authentication credentials

**Source**: Managed via `scripts/manage_users.py` CLI tool

**S3 Storage**: `auth/users.json`

**Data Structure**:

```json
{
  "users": [
    {
      "email": "ta1@gatech.edu",
      "password_hash": "$2b$12$...",
      "name": "Alice Johnson",
      "role": "ta",
      "created_at": "2025-01-15T10:00:00.000000Z"
    }
  ]
}
```

**Field Definitions**:

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `email` | string (email) | User's login email | Yes |
| `password_hash` | string | Bcrypt password hash (cost factor 12) | Yes |
| `name` | string | User's full name | Yes |
| `role` | string | User role (ta, instructor, admin) | Yes |
| `created_at` | string (ISO 8601) | Account creation timestamp | Yes |

**Security Notes**:
- Passwords are hashed using bcrypt with cost factor 12
- Never expose `password_hash` in API responses
- File is encrypted at rest with SSE-S3
- Access restricted via IAM policies

---

## Data Relationships

### Entity Relationship Diagram

```
┌──────────────┐
│  Assignments │
│              │
│ id           │◄────────┐
│ name         │         │
│ due_at       │         │
│ points       │         │
└──────────────┘         │
                         │
                         │ assignment_id
                         │
┌──────────────┐         │
│    Users     │         │
│              │         │
│ id           │◄───┐    │
│ name         │    │    │
│ email        │    │    │
└──────────────┘    │    │
                    │    │
         ┌──────────┼────┼────────────┐
         │          │    │            │
         │ user_id  │    │            │
         │          │    │            │
┌────────▼──────────▼────▼─────┐      │
│      Submissions              │      │
│                               │      │
│ id                            │      │
│ user_id       ────────────────┘      │
│ assignment_id ───────────────────────┘
│ submitted_at                  │
│ workflow_state                │
│ late                          │
│ score                         │
└───────────────────────────────┘
         │
         │ user_id
         │
         ▼
┌──────────────────────────────┐
│         Groups                │
│                               │
│ id                            │
│ name                          │
│ members[]                     │
│   ├─ user_id (FK to Users)   │
│   └─ name                     │
└───────────────────────────────┘
```

### Key Relationships

1. **Submissions to Assignments**: Many-to-one
   - Foreign Key: `submission.assignment_id` → `assignment.id`
   - Each submission is for exactly one assignment
   - Each assignment can have multiple submissions (one per student)

2. **Submissions to Users**: Many-to-one
   - Foreign Key: `submission.user_id` → `user.id`
   - Each submission belongs to exactly one user
   - Each user can have multiple submissions (one per assignment)

3. **Groups to Users**: Many-to-many
   - Through: `group.members[]` containing user IDs
   - Each group can have multiple members
   - Each user can belong to multiple groups (though typically one TA group)

### Data Integrity

- **Referential Integrity**: Not enforced at database level (S3 is not a database)
- **Application Logic**: Backend validates relationships when processing data
- **Missing References**: Gracefully handled with null checks and optional fields

---

## API Endpoints

### Endpoints Using Canvas Data

| Endpoint | Method | Data Used | Description |
|----------|--------|-----------|-------------|
| `/api/canvas/courses` | GET | Course folders | List available courses |
| `/api/canvas/data/{course_id}` | GET | `latest.json` | Get complete course data |
| `/api/canvas/assignments/{course_id}` | GET | `latest_assignments.json` | Get assignment list |
| `/api/canvas/submissions/{course_id}` | GET | `latest_submissions.json` | Get submission data |
| `/api/canvas/users/{course_id}` | GET | `latest_users.json` | Get enrolled students |
| `/api/canvas/groups/{course_id}` | GET | `latest_groups.json` | Get TA groups |
| `/api/dashboard/submission-status/{course_id}` | GET | All entities | Calculate submission metrics |
| `/api/dashboard/ta-grading/{course_id}` | GET | Assignments, Submissions, Users | Get ungraded items |
| `/api/canvas/sync` | POST | Triggers Lambda | Manually refresh Canvas data |

### Data Access Patterns

**Pre-signed URLs**:
- Large datasets served via S3 pre-signed URLs (1 hour expiration)
- Reduces Lambda payload size and improves performance
- Endpoints: assignments, submissions, users, groups

**Direct JSON Response**:
- Small datasets returned directly in API response
- Endpoints: courses list, complete data

**Computed Metrics**:
- Backend processes raw data to calculate metrics
- Endpoints: submission-status, ta-grading

---

## Data Processing

### Submission Status Classification

The backend classifies submissions into three categories:

**Algorithm** (from `main.py:classify_submission_status`):

```python
def classify_submission_status(submission, assignment):
    workflow_state = submission.get('workflow_state')
    submitted_at = submission.get('submitted_at')
    due_at = assignment.get('due_at')
    late = submission.get('late', False)

    # Missing: not submitted or pending review
    if workflow_state in ['unsubmitted', 'pending_review'] or not submitted_at:
        return 'missing'

    # Late: explicit late flag or submitted after due date
    if late:
        return 'late'

    if submitted_at and due_at:
        if parse(submitted_at) > parse(due_at):
            return 'late'

    return 'on_time'
```

**Status Categories**:

| Status | Condition |
|--------|-----------|
| `missing` | `workflow_state` is 'unsubmitted' or 'pending_review', or no `submitted_at` |
| `late` | `late` flag is true, or submitted after due date |
| `on_time` | Submitted before due date and not marked late |

### Metrics Calculation

**Submission Status Metrics** (`/api/dashboard/submission-status/{course_id}`):

Returns comprehensive statistics with three levels:

1. **Overall Metrics**:
   - Total on-time, late, missing submissions across all assignments
   - Percentages calculated as: `(count / total_expected) * 100`
   - `total_expected = num_assignments * num_users`

2. **By Assignment**:
   - Metrics for each individual assignment
   - Shows which assignments have completion issues
   - Includes assignment metadata (name, due date)

3. **By TA Group**:
   - Metrics aggregated by TA group
   - Shows workload distribution across TAs
   - Student count per TA group
   - Percentages calculated per TA's assigned students

**Performance Optimization**:
- Time complexity: O(Assignments × Users)
- Uses pre-computed lookup dictionaries for O(1) access
- Avoids nested loops over groups and members

### TA Grading Dashboard

**Ungraded Submissions** (`/api/dashboard/ta-grading/{course_id}`):

Returns list of submissions needing grading:

```json
{
  "ungraded_submissions": [
    {
      "assignment_id": "123456",
      "assignment_name": "Homework 1",
      "student_id": "345678",
      "student_name": "Jane Doe",
      "submitted_at": "2025-02-14T18:30:00Z",
      "due_date": "2025-02-15T23:59:00Z",
      "submission_type": ["online_upload"],
      "points_possible": 100.0
    }
  ],
  "ta_workload": {
    "TA Group - Alice": 25,
    "TA Group - Bob": 22
  },
  "total_ungraded": 47,
  "last_updated": "2025-11-28T15:30:00Z"
}
```

---

## Performance Considerations

### Caching Strategy

- **S3-side caching**: Data refreshes every 15 minutes
- **Client-side caching**: Frontend can cache data with TTL
- **Pre-signed URLs**: 1-hour expiration reduces S3 requests

### Data Size Estimates

Typical course with 200 students and 10 assignments:

| Entity | Records | Estimated Size |
|--------|---------|----------------|
| Assignments | 10 | ~2 KB |
| Users | 200 | ~15 KB |
| Submissions | 2,000 | ~80 KB |
| Groups | 5 | ~3 KB |
| **Total** | - | **~100 KB** |

### Optimization Recommendations

1. **Use pre-signed URLs** for large datasets (submissions, users)
2. **Filter data** at API level (assignment_id, ta_group parameters)
3. **Cache API responses** in frontend with appropriate TTL (5-10 minutes)
4. **Paginate results** for very large courses (500+ students)

---

## Error Handling

### Missing Data Scenarios

| Scenario | Behavior |
|----------|----------|
| Course not found | Returns 404 with descriptive error message |
| Empty course | Returns empty arrays for all entities |
| Partial data | Returns available data, logs warning |
| S3 unavailable | Returns 500 with service status |

### Data Validation

**Pydantic Models** (defined in `main.py`):
- `CanvasData`: Validates complete data structure
- `AssignmentStatusBreakdown`: Validates metrics responses
- `TAStatusMetrics`: Validates TA workload data

**Validation Rules**:
- Required fields enforced by Pydantic
- Type checking (integers, strings, dates)
- Email format validation for users
- ISO 8601 date format for timestamps

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

### Access Control

- **S3 Bucket**: Private, IAM-restricted access
- **API Endpoints**: JWT authentication required
- **Pre-signed URLs**: Short expiration (1 hour)
- **Encryption**: At-rest (SSE-S3) and in-transit (HTTPS)

### Compliance Notes

- **FERPA**: Student data must be protected under FERPA regulations
- **Audit Logging**: All API requests logged to CloudWatch
- **Data Retention**: Configure S3 lifecycle policies for compliance
- **Access Logs**: Monitor via CloudWatch for unauthorized access attempts

---

## Troubleshooting

### Common Issues

**1. No data for course ID**:
- Verify course ID format (short vs long form)
- Check S3 bucket for `canvas_data/course_{ID}/` folder
- Confirm data fetcher Lambda has run successfully
- Check Lambda CloudWatch logs for errors

**2. Stale data**:
- Verify EventBridge rule is enabled
- Check data fetcher Lambda execution history
- Manually trigger sync via `/api/canvas/sync`
- Confirm `timestamp` field in data

**3. Missing users or submissions**:
- Verify Canvas API token permissions
- Check if users are enrolled as students (not TAs/instructors)
- Confirm assignments are published in Canvas
- Review Canvas API rate limits

### Debugging Tools

**AWS CLI - Check S3 data**:
```bash
aws s3 ls s3://YOUR_BUCKET/canvas_data/course_516212/
aws s3 cp s3://YOUR_BUCKET/canvas_data/course_516212/latest.json - | jq .
```

**Backend logs**:
```bash
# Local development
tail -f logs/app.log

# Lambda CloudWatch
aws logs tail /aws/lambda/canvas-data-fetcher --follow
```

**Test API endpoints**:
```bash
# Get courses
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://your-api.com/api/canvas/courses

# Get course data
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://your-api.com/api/canvas/data/516212
```

---

## Future Enhancements

### Planned Improvements

1. **Enrollments Data**: Populate enrollment information (section, role, status)
2. **Historical Data**: Store timestamped versions for trend analysis
3. **Assignment Rubrics**: Include rubric data for grading assistance
4. **Submission Comments**: Fetch grading comments and feedback
5. **Grade Statistics**: Calculate grade distributions and statistics
6. **Data Compression**: Use gzip compression for large datasets
7. **Delta Updates**: Only fetch changed data since last sync
8. **Multi-Course Support**: Extend to multiple courses per deployment

### Schema Versioning

Consider adding schema version to data files:

```json
{
  "schema_version": "1.0.0",
  "course_id": "516212",
  "timestamp": "2025-11-28T15:30:00Z",
  ...
}
```

This allows for backward-compatible schema evolution.

---

## References

- **Canvas API Documentation**: https://canvas.instructure.com/doc/api/
- **CanvasAPI Python Library**: https://canvasapi.readthedocs.io/en/stable/
- **AWS S3 Documentation**: https://docs.aws.amazon.com/s3/
- **FERPA Guidelines**: https://www2.ed.gov/policy/gen/guid/fpco/ferpa/index.html
- **Project Architecture**: See `ARCHITECTURE.md`
- **Authentication Details**: See `AUTHENTICATION.md`
- **Agent Instructions**: See `AGENTS.md`

---

## Document Metadata

- **Version**: 1.0.0
- **Last Updated**: 2025-11-28
- **Author**: Canvas TA Dashboard Development Team
- **Status**: Active
