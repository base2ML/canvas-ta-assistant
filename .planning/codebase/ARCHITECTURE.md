# Architecture

**Analysis Date:** 2026-02-15

## Pattern Overview

**Overall:** Client-Server SPA with Local Database

**Key Characteristics:**
- Single-page React application communicating via REST API to FastAPI backend
- SQLite database for local data persistence (no cloud dependencies)
- Canvas API integration for LMS data synchronization
- Docker-based deployment with Nginx reverse proxy
- No authentication (single-user local deployment)
- Data sync on startup and on-demand via Settings page

## Layers

**Frontend Layer (React SPA):**
- Purpose: User interface for TA dashboard, settings, and data visualization
- Location: `canvas-react/src/`
- Contains: React components, hooks, utilities, routing
- Depends on: Backend API (via `/api/*` endpoints proxied by Nginx)
- Used by: End users (Teaching Assistants)

**API Layer (FastAPI Backend):**
- Purpose: REST API serving Canvas data and dashboard metrics
- Location: `main.py` (API routes), `database.py` (data access), `canvas_sync.py` (Canvas integration)
- Contains: FastAPI endpoints, Pydantic models, business logic
- Depends on: SQLite database, Canvas API (via canvasapi library)
- Used by: Frontend via Nginx proxy

**Data Layer (SQLite):**
- Purpose: Local persistent storage of Canvas data
- Location: `./data/canvas.db` (volume mount in Docker)
- Contains: `settings`, `assignments`, `users`, `submissions`, `groups`, `group_members`, `sync_history`, `peer_reviews`, `peer_review_comments`, `enrollment_history`, `enrollment_events`
- Depends on: File system
- Used by: Backend (database.py module)

**Canvas Integration Layer:**
- Purpose: Fetch and synchronize data from Canvas LMS API
- Location: `canvas_sync.py`
- Contains: `get_canvas_client()`, `fetch_available_courses()`, `sync_course_data()`, `sync_on_startup()`
- Depends on: Canvas API (external), SQLite database
- Used by: Backend (triggered on startup and manual sync)

## Data Flow

**Startup Sync:**

1. Docker Compose starts backend and frontend containers
2. Backend initializes SQLite database in `./data/canvas.db`
3. If `CANVAS_COURSE_ID` configured:
   a. Backend connects to Canvas API using `canvas_sync.get_canvas_client()`
   b. `canvas_sync.sync_course_data()` fetches assignments, users, submissions, groups
   c. Data is upserted to SQLite tables via `database.py`
   d. Sync record created in `sync_history` table
4. Frontend Nginx container becomes available on port 3000
5. Frontend loads and fetches courses from `/api/canvas/courses`

**Manual Sync (via Settings or Refresh Button):**

1. User clicks "Sync Now" or "Refresh Data" button
2. Frontend calls `POST /api/canvas/sync` via Nginx proxy
3. Backend triggers `canvas_sync.sync_course_data()` with current course ID
4. Clear operation: `database.clear_refreshable_data()` removes assignments, groups, peer reviews
5. Upsert operations insert/update assignments, users, groups, submissions
6. Enrollment tracking: users marked `pending_check`, then `active` or `dropped`
7. Frontend reloads data from backend API endpoints

**Data Query Flow:**

1. Frontend component mounts (e.g., `EnhancedTADashboard.jsx`)
2. Component calls `apiFetch('/api/canvas/assignments/{course_id}')` (proxied to backend)
3. Nginx forwards `/api/*` requests to `backend:8000`
4. Backend endpoint queries SQLite via `database.get_assignments()`
5. Backend returns JSON response to frontend
6. Frontend renders data using React components

**Enrollment Tracking Flow:**

1. During sync, `database.mark_all_users_pending()` marks all users as `pending_check`
2. Canvas users are fetched and upserted with `enrollment_status='active'`
3. `database.mark_dropped_users()` marks remaining `pending_check` users as `dropped`
4. `database.get_enrollment_state_snapshot()` captures before/after state
5. `database.record_enrollment_events()` records individual status changes
6. `database.record_enrollment_snapshot()` records aggregate counts per sync

**State Management:**
- Frontend: React `useState` hooks for component-level state
- No global state management (Redux/Context not used)
- Props drilling for shared state (courses, course selection)
- Backend: Stateless FastAPI endpoints (SQLite is single source of truth)

## Key Abstractions

**SQLite Context Managers:**
- Purpose: Safe database connection handling with automatic cleanup
- Examples: `database.get_db_connection()`, `database.get_db_transaction()`
- Pattern: Context manager with `with` statement, auto-commit/rollback

**Upsert Pattern:**
- Purpose: Insert or update records based on primary key
- Examples: `database.upsert_assignments()`, `database.upsert_users()`, `database.upsert_submissions()`
- Pattern: `INSERT ... ON CONFLICT(key) DO UPDATE SET ...`

**Pydantic Models:**
- Purpose: Type-safe API request/response schemas
- Examples: `SettingsResponse`, `SyncResponse`, `HealthResponse`, `PeerReviewAnalysis`, `SubmissionStatusMetrics`
- Pattern: BaseModel with field validation, auto-JSON conversion

**API Client Wrapper:**
- Purpose: Centralized fetch with error handling and JSON parsing
- Location: `canvas-react/src/api.js`
- Pattern: `apiFetch(endpoint, options)` wraps native fetch

## Entry Points

**Backend Entry Point:**
- Location: `main.py`
- Triggers: Docker container startup, or `uv run uvicorn main:app`
- Responsibilities:
  - Initialize FastAPI application with CORS and rate limiting
  - Define all API routes (health, settings, canvas data, dashboard metrics)
  - Run startup sync via `canvas_sync.sync_on_startup()`
  - Serve on port 8000

**Frontend Entry Point:**
- Location: `canvas-react/src/main.jsx`
- Triggers: Browser loads index.html (served by Nginx)
- Responsibilities:
  - Mount React root component
  - Initialize React Router DOM

**Application Entry Point:**
- Location: `canvas-react/src/App.jsx`
- Triggers: React app renders
- Responsibilities:
  - Define routing with `<Routes>` components
  - Manage global state (courses list, sync status, sync messages)
  - Provide refresh functionality to all routes
  - Render `<Navigation>` and main content area

**Docker Compose Entry Point:**
- Location: `docker-compose.yml`
- Triggers: `docker-compose up --build`
- Responsibilities:
  - Build and start backend container (Python 3.11 + FastAPI)
  - Build and start frontend container (Nginx + React build)
  - Mount `./data` volume for SQLite persistence
  - Configure environment variables from `.env`

## Error Handling

**Strategy:** Try-except with HTTP status codes and user-friendly messages

**Patterns:**
- Backend: HTTPException with status codes (400, 404, 500) raised in endpoints
- Frontend: `apiFetch()` throws errors with `errorData.detail` or `errorData.message`
- Database: Transaction rollback on exception via `get_db_transaction()` context manager
- Logging: Loguru logger with levels (info, warning, error, debug)

## Cross-Cutting Concerns

**Logging:** Loguru logger in backend (`logger.add("logs/app.log")`), console.error in frontend
**Validation:** Pydantic models for request validation, React prop validation not enforced
**Authentication:** None (single-user local deployment)
**Rate Limiting:** Slowapi middleware with `get_remote_address` key function
**CORS:** Permissive CORS for localhost development (ports 3000, 5173, 8000)

---

*Architecture analysis: 2026-02-15*
