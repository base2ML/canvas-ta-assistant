# Architecture Research: Comment Posting Integration

**Domain:** Canvas LMS TA Dashboard - Comment Posting Feature
**Researched:** 2026-02-15
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend Layer (React)                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────────────────────────────────┐   │
│  │  Settings   │  │       LateDaysTracking                  │   │
│  │  Page       │  │       Page                              │   │
│  │             │  │                                         │   │
│  │ - Template  │  │ - Student list                          │   │
│  │   editor    │  │ - Comment preview                       │   │
│  │ - Template  │  │ - Bulk posting UI                       │   │
│  │   list      │  │ - Post history                          │   │
│  └──────┬──────┘  └─────────┬───────────────────────────────┘   │
│         │                   │                                   │
│         │  apiFetch()       │  apiFetch()                       │
│         │                   │                                   │
├─────────┴───────────────────┴───────────────────────────────────┤
│                     API Layer (FastAPI)                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │ Template         │  │ Comment Posting  │  │ Post History │  │
│  │ Endpoints        │  │ Endpoints        │  │ Endpoints    │  │
│  │                  │  │                  │  │              │  │
│  │ GET    /templates│  │ POST   /comments │  │ GET /history │  │
│  │ POST   /templates│  │ POST   /preview  │  │              │  │
│  │ PUT    /templates│  │                  │  │              │  │
│  │ DELETE /templates│  │                  │  │              │  │
│  └────────┬─────────┘  └────────┬─────────┘  └──────┬───────┘  │
│           │                     │                    │          │
├───────────┴─────────────────────┴────────────────────┴──────────┤
│                   Canvas Integration Layer                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              canvas_sync.py (new function)               │    │
│  │                                                          │    │
│  │  post_submission_comment(course_id, assignment_id,       │    │
│  │                          user_id, comment_text)          │    │
│  │                                                          │    │
│  │  Uses: submission.edit(comment={'text_comment': text})   │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                   Data Layer (SQLite)                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌────────────────────┐  ┌──────────────────────────────────┐   │
│  │ comment_templates  │  │ comment_posting_history          │   │
│  │                    │  │                                  │   │
│  │ - id (PK)          │  │ - id (PK, AUTOINCREMENT)         │   │
│  │ - name             │  │ - course_id                      │   │
│  │ - template_text    │  │ - assignment_id                  │   │
│  │ - placeholders     │  │ - user_id                        │   │
│  │ - is_default       │  │ - comment_text                   │   │
│  │ - created_at       │  │ - posted_at                      │   │
│  │ - updated_at       │  │ - posted_by                      │   │
│  └────────────────────┘  │ - status (success/failed)        │   │
│                          │ - error_message                  │   │
│                          └──────────────────────────────────┘   │
│                                                                  │
│  Existing tables:                                                │
│  - assignments, users, submissions, groups, group_members        │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Settings Page** | Template CRUD UI | React component with form inputs, template list, Tailwind CSS styling |
| **LateDaysTracking Page** | Comment posting workflow | Enhanced existing component with comment UI, preview, bulk post |
| **Template Endpoints** | Template storage management | FastAPI routes with Pydantic models, SQLite CRUD via database.py |
| **Posting Endpoints** | Comment submission orchestration | FastAPI routes that call canvas_sync.py, record history |
| **Canvas Integration** | Canvas API comment posting | New function in canvas_sync.py using canvasapi library |
| **Database Layer** | Template and history persistence | SQLite tables with upsert patterns, context managers |

## Recommended Project Structure

```
canvas-react/src/
├── components/
│   ├── Navigation.jsx                      # Existing (no changes)
│   ├── AssignmentStatusBreakdown.jsx       # Existing (no changes)
│   ├── CommentTemplateEditor.jsx           # NEW - Template CRUD UI
│   ├── CommentPostingPanel.jsx             # NEW - Student selection + comment preview
│   └── PostingHistoryTable.jsx             # NEW - History display
├── Settings.jsx                            # MODIFIED - Add template tab
├── LateDaysTracking.jsx                    # MODIFIED - Add posting UI
├── App.jsx                                 # Existing (no changes to routing)
└── api.js                                  # Existing (no changes)

Backend:
├── main.py                                 # MODIFIED - Add 3 endpoint groups
│                                           # - /api/templates/* (CRUD)
│                                           # - /api/comments/* (post, preview)
│                                           # - /api/comments/history/* (query)
├── database.py                             # MODIFIED - Add template + history functions
│                                           # - upsert_template()
│                                           # - get_templates()
│                                           # - delete_template()
│                                           # - record_comment_post()
│                                           # - get_posting_history()
├── canvas_sync.py                          # MODIFIED - Add posting function
│                                           # - post_submission_comment()
└── data/canvas.db                          # MODIFIED - Add 2 tables
                                            # - comment_templates
                                            # - comment_posting_history
```

### Structure Rationale

- **Frontend components:** Follows existing pattern of page-level components (Settings, LateDaysTracking) with smaller reusable components in `components/` directory
- **Backend modules:** Maintains separation of concerns - `main.py` (routes), `database.py` (data access), `canvas_sync.py` (Canvas API)
- **Database tables:** Separate tables for templates (configuration) and history (audit trail), following existing naming conventions
- **No new dependencies:** Uses existing tech stack (React, FastAPI, canvasapi, SQLite)

## Architectural Patterns

### Pattern 1: Template Storage with Placeholder Substitution

**What:** Store comment templates with placeholder markers (e.g., `{student_name}`, `{late_days}`) that are replaced with actual values at posting time.

**When to use:** For bulk comment posting where the structure is the same but values differ per student.

**Trade-offs:**
- **Pros:** Reusable templates, consistent messaging, reduces typing, supports bulk operations
- **Cons:** Requires placeholder parsing logic, templates need to be flexible enough for different scenarios

**Example:**
```python
# Template storage in SQLite
template_text = "Hi {student_name}, you have {late_days} late days remaining."
placeholders = ["student_name", "late_days"]  # JSON array

# At posting time (backend)
comment = template_text.format(
    student_name=student.name,
    late_days=calculate_late_days(student.id)
)
```

### Pattern 2: Posting History as Audit Trail

**What:** Record every comment posting attempt (success or failure) in a dedicated `comment_posting_history` table.

**When to use:** For tracking what was posted to Canvas, troubleshooting failures, and providing user feedback.

**Trade-offs:**
- **Pros:** Full audit trail, error tracking, supports "what did I post?" queries, enables retry logic
- **Cons:** Additional database writes, table can grow large (mitigated by periodic cleanup)

**Example:**
```python
# Record successful post
db.record_comment_post(
    course_id=course_id,
    assignment_id=assignment_id,
    user_id=student_id,
    comment_text=rendered_comment,
    status="success",
    posted_by="TA Dashboard"
)

# Record failure
db.record_comment_post(
    course_id=course_id,
    assignment_id=assignment_id,
    user_id=student_id,
    comment_text=rendered_comment,
    status="failed",
    error_message=str(error)
)
```

### Pattern 3: Preview Before Post

**What:** Provide a `/api/comments/preview` endpoint that renders templates with actual data WITHOUT posting to Canvas.

**When to use:** To allow users to verify comment content before bulk posting.

**Trade-offs:**
- **Pros:** Prevents mistakes, builds confidence, shows exactly what will be posted
- **Cons:** Requires separate endpoint, adds UI complexity

**Example:**
```javascript
// Frontend: Preview before posting
const previews = await apiFetch('/api/comments/preview', {
  method: 'POST',
  body: JSON.stringify({
    template_id: selectedTemplate.id,
    student_ids: selectedStudents.map(s => s.id),
    assignment_id: currentAssignment.id
  })
});

// Display previews for user review
// User clicks "Confirm Post" to actually post
```

## Data Flow

### Request Flow: Template Creation

```
User creates template in Settings
    ↓
Settings.jsx → POST /api/templates
    ↓
main.py template_create() → database.upsert_template()
    ↓
SQLite INSERT INTO comment_templates
    ↓
Return template object → Settings.jsx updates UI
```

### Request Flow: Comment Posting

```
User selects students + template in LateDaysTracking
    ↓
LateDaysTracking.jsx → POST /api/comments
    ↓
main.py post_comments() validates request
    ↓
For each student:
    ├─→ Render template with student data
    ├─→ canvas_sync.post_submission_comment() → Canvas API
    ├─→ database.record_comment_post() → SQLite
    └─→ Collect results (success/failure)
    ↓
Return summary → LateDaysTracking.jsx shows results
```

### State Management

**Frontend:**
- Settings page: `useState` for template list, editing template, form state
- LateDaysTracking page: Existing `useState` for student data + new state for selected students, preview mode, posting status
- No global state needed (template data fetched per-page)

**Backend:**
- Stateless FastAPI endpoints (SQLite is source of truth)
- Canvas API client created per-request (existing pattern)

### Key Data Flows

1. **Template CRUD:** Settings UI ↔ `/api/templates/*` ↔ `comment_templates` table
2. **Comment Preview:** LateDaysTracking UI → `/api/comments/preview` → render templates (no DB write)
3. **Comment Posting:** LateDaysTracking UI → `/api/comments` → Canvas API + `comment_posting_history` table
4. **History Query:** LateDaysTracking UI → `/api/comments/history/{assignment_id}` → `comment_posting_history` table

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-100 students | Current architecture is perfect - SQLite, synchronous posting loop |
| 100-500 students | Add rate limiting on Canvas API calls (existing SlowAPI middleware), consider progress UI for bulk posts |
| 500+ students | Consider async posting with background tasks (FastAPI BackgroundTasks), batch Canvas API calls |

### Scaling Priorities

1. **First bottleneck:** Canvas API rate limits (bulk posting many comments)
   - **Fix:** Add rate limiting (1-2 req/sec), show progress bar in UI, use FastAPI BackgroundTasks for async posting
2. **Second bottleneck:** Database writes for history (one INSERT per comment)
   - **Fix:** Batch INSERT statements, add periodic history cleanup (delete records older than 1 year)

## Anti-Patterns

### Anti-Pattern 1: Storing Comments in SQLite Instead of Canvas

**What people do:** Store comments locally in SQLite, then sync to Canvas later
**Why it's wrong:** Creates synchronization complexity, risk of data loss, local DB becomes source of truth when Canvas should be
**Do this instead:** Post directly to Canvas, use SQLite only for audit trail (`comment_posting_history`)

### Anti-Pattern 2: Embedding Business Logic in Frontend

**What people do:** Render templates with placeholders in React component (frontend)
**Why it's wrong:** Exposes student data processing logic to client, harder to test, inconsistent rendering across UI
**Do this instead:** Backend renders templates (main.py), frontend only displays previews and results

### Anti-Pattern 3: No Error Handling for Failed Posts

**What people do:** Assume all Canvas API calls succeed, no retry or error reporting
**Why it's wrong:** Silent failures, no audit trail of what failed, user doesn't know if post succeeded
**Do this instead:** Wrap Canvas API calls in try/except, record failures in `comment_posting_history`, return detailed results to frontend

### Anti-Pattern 4: Tight Coupling Between Posting and Settings

**What people do:** Put template editor in the same UI as posting workflow
**Why it's wrong:** Clutters posting UI, forces context switching during bulk operations
**Do this instead:** Separate concerns - template management in Settings, template usage in LateDaysTracking (current design)

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Canvas API (submission comments) | `canvasapi` library → `submission.edit(comment={'text_comment': ...})` | Requires TA/Teacher permissions, rate limited, may fail silently if permissions insufficient |
| Canvas API (submission fetch) | Existing `canvas_sync.py` pattern | Reuse existing `get_canvas_client()` function |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Settings ↔ Backend | REST API (`/api/templates/*`) | Standard CRUD operations, Pydantic models for validation |
| LateDaysTracking ↔ Backend | REST API (`/api/comments/*`) | Posting and preview endpoints, JSON request/response |
| Backend ↔ Canvas API | `canvasapi.Submission.edit()` | Synchronous calls, wrap in error handling, record history |
| Backend ↔ Database | Context managers (`get_db_transaction()`) | Existing pattern, auto-commit/rollback |

## Build Order (Dependency-Based)

Based on dependencies between components, recommend building in this order:

### Phase 1: Database Foundation (Backend)
**Build first - no dependencies**
1. Add `comment_templates` table schema (database.py)
2. Add `comment_posting_history` table schema (database.py)
3. Implement template CRUD functions (database.py)
4. Implement history recording function (database.py)

### Phase 2: Canvas Integration (Backend)
**Depends on: Database schema**
1. Add `post_submission_comment()` function (canvas_sync.py)
2. Test Canvas API comment posting manually
3. Add error handling and logging

### Phase 3: API Endpoints (Backend)
**Depends on: Database functions, Canvas integration**
1. Add Pydantic models for templates and posting (main.py)
2. Implement template CRUD endpoints (`/api/templates/*`)
3. Implement comment preview endpoint (`/api/comments/preview`)
4. Implement comment posting endpoint (`/api/comments`)
5. Implement history query endpoint (`/api/comments/history/*`)

### Phase 4: Settings UI (Frontend)
**Depends on: Template API endpoints**
1. Build `CommentTemplateEditor.jsx` component
2. Add template tab to Settings.jsx
3. Wire up API calls (apiFetch)
4. Test template CRUD workflow

### Phase 5: Posting UI (Frontend)
**Depends on: Settings UI (for template creation), Posting API endpoints**
1. Build `CommentPostingPanel.jsx` component
2. Build `PostingHistoryTable.jsx` component
3. Modify LateDaysTracking.jsx to add posting UI
4. Implement preview workflow
5. Implement bulk posting workflow
6. Add posting history display

### Phase 6: Integration Testing
**Depends on: All previous phases**
1. End-to-end testing (create template → post comment → verify in Canvas)
2. Error handling testing (failed Canvas API calls)
3. Bulk posting testing (10+ students)

**Rationale for this order:**
- Backend first (database + API) enables frontend work without blockers
- Settings UI before Posting UI (need templates to exist before using them)
- Integration testing last (requires all components working)

## Implementation Notes

### Placeholder System

**Supported placeholders:** (extracted from student/assignment data)
- `{student_name}` - Student's full name
- `{late_days}` - Number of late days used (calculated)
- `{assignment_name}` - Assignment title
- `{due_date}` - Assignment due date (formatted)

**Template rendering:** Use Python's `.format()` method (backend) with data from SQLite queries.

### Canvas API Comment Posting

Based on Canvas API documentation research:

**Endpoint:** `PUT /api/v1/courses/:course_id/assignments/:assignment_id/submissions/:user_id`

**Method (using canvasapi library):**
```python
submission = assignment.get_submission(user_id)
submission.edit(comment={'text_comment': comment_text})
```

**Permissions required:** TA or Teacher role in course

**Error scenarios:**
- 401 Unauthorized: Invalid Canvas API token
- 403 Forbidden: Insufficient permissions (not TA/Teacher)
- 404 Not Found: Invalid course/assignment/user ID
- Rate limiting: Too many requests (Canvas enforces limits)

**Sources:**
- [Canvas Submissions API](https://www.canvas.instructure.com/doc/api/submissions.html)
- [Canvas Submission Comments API](https://canvas.instructure.com/doc/api/submission_comments.html)
- [Canvas Submissions API (alternate)](https://canvas.krsu.kg/doc/api/submissions.html)

### Database Schema Details

**comment_templates:**
```sql
CREATE TABLE comment_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    template_text TEXT NOT NULL,
    placeholders TEXT,  -- JSON array: ["student_name", "late_days"]
    is_default INTEGER DEFAULT 0,  -- Boolean: 1 = default template
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**comment_posting_history:**
```sql
CREATE TABLE comment_posting_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL,
    assignment_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    comment_text TEXT NOT NULL,
    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    posted_by TEXT DEFAULT 'TA Dashboard',
    status TEXT NOT NULL,  -- 'success' or 'failed'
    error_message TEXT,
    FOREIGN KEY (assignment_id) REFERENCES assignments(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_posting_history_assignment
    ON comment_posting_history(assignment_id);
CREATE INDEX idx_posting_history_user
    ON comment_posting_history(user_id);
```

### UI/UX Recommendations

**Settings Page - Template Tab:**
- List existing templates with edit/delete buttons
- "New Template" button → form (name, template text, placeholders)
- Mark one template as "default"
- Show placeholder syntax help text

**LateDaysTracking Page - Posting Panel:**
- Student selection: Checkboxes in existing table (or "Select All")
- Template dropdown (loads from `/api/templates`)
- "Preview" button → shows rendered comments (modal/panel)
- "Post Comments" button → confirmation dialog → bulk post
- Progress indicator during bulk posting
- Results summary (X posted, Y failed)
- Posting history section below (expandable)

## Sources

- Canvas TA Dashboard codebase analysis (main.py, database.py, canvas_sync.py, Settings.jsx, LateDaysTracking.jsx)
- [Canvas Submissions API Documentation](https://www.canvas.instructure.com/doc/api/submissions.html)
- [Canvas Submission Comments API](https://canvas.instructure.com/doc/api/submission_comments.html)
- [Canvas API - Submissions (KRSU)](https://canvas.krsu.kg/doc/api/submissions.html)
- [CanvasAPI Python Library](https://canvasapi.readthedocs.io/en/stable/) (via Context7: /ucfopen/canvasapi)
- Existing architecture patterns in `.planning/codebase/ARCHITECTURE.md`

---
*Architecture research for: Canvas TA Dashboard - Comment Posting Integration*
*Researched: 2026-02-15*
