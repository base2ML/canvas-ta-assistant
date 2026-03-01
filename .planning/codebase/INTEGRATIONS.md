# External Integrations

**Analysis Date:** 2026-02-15

## APIs & External Services

**Canvas LMS API:**
- Canvas LMS API - Fetches assignments, submissions, users, groups
  - SDK/Client: `canvasapi` 3.0.0+ (`/canvas_sync.py`)
  - Auth: `CANVAS_API_TOKEN` (environment variable)
  - Configuration: `CANVAS_API_URL` (environment variable)
  - Documentation: https://canvas.instructure.com/doc/api/
  - Documentation: https://canvasapi.readthedocs.io/en/stable/

**Canvas API Endpoints Used:**
- `GET /api/v1/courses` - List available courses (TA enrollment)
- `GET /api/v1/courses/{course_id}/assignments` - Get assignments
- `GET /api/v1/courses/{course_id}/assignments/{assignment_id}/submissions` - Get submissions
- `GET /api/v1/courses/{course_id}/users` - Get enrolled students
- `GET /api/v1/courses/{course_id}/groups` - Get TA grading groups

## Data Storage

**Databases:**
- SQLite (Python stdlib)
  - Connection: `sqlite3` module
  - Location: `./data/canvas.db`
  - Client: Direct SQL queries with sqlite3 (`/database.py`)
  - ORM: None (raw SQL with context managers)
  - Persistence: Docker volume mount at `./data/`

**File Storage:**
- Local filesystem only
- No cloud storage services used

**Caching:**
- No caching layer
- Data stored directly in SQLite

## Authentication & Identity

**Auth Provider:**
- Custom (Canvas API token-based)
  - Implementation: Single token authentication via `CANVAS_API_TOKEN` environment variable
  - No user authentication system (single-user local deployment)
  - No JWT, OAuth, or session management

**Canvas API Authentication:**
- Bearer token authentication
- Token generated in Canvas LMS UI: Account > Settings > Approved Integrations
- Token should be regenerated periodically for security

## Monitoring & Observability

**Error Tracking:**
- None
- Errors logged via Loguru to `/logs/app.log`

**Logs:**
- Framework: `loguru` 0.7.3+
- Approach: File-based logging to `./logs/app.log` with rotation
- Rotation: 500 MB file size, 10 day retention
- Location: `/logs/` directory (Docker volume mount)

## CI/CD & Deployment

**Hosting:**
- Platform: Local Docker deployment
- No cloud hosting
- No CDN

**CI Pipeline:**
- Service: GitHub Actions
- Config: `/.github/workflows/ci.yml`
- Jobs:
  - `backend-lint` - Python linting with Ruff, type checking with mypy
  - `backend-tests` - pytest execution
  - `frontend-tests` - ESLint, build, Vitest tests
  - `pre-commit-hooks` - Run all pre-commit hooks
  - `ci-summary` - Report overall CI status
- Triggered on: Push/PR to main or development branches

**Deployment:**
- Manual via Docker Compose
- No automated deployment
- Scripts in `/scripts/`:
  - `test-backend-local.sh` - Backend testing
  - `test-frontend-local.sh` - Frontend testing
  - `test-integration.sh` - Integration testing
  - `deploy-production.sh` - Production deployment
  - `deploy-sandbox.sh` - Sandbox deployment

## Environment Configuration

**Required env vars:**
- `CANVAS_API_URL` - Canvas LMS instance URL
- `CANVAS_API_TOKEN` - Canvas API access token

**Optional env vars:**
- `CANVAS_COURSE_ID` - Default course ID
- `ENVIRONMENT` - Environment name (default: local)
- `DATA_DIR` - Database directory (default: ./data)
- `VITE_API_ENDPOINT` - Frontend API endpoint (default: empty for relative URLs)

**Secrets location:**
- Local `.env` file (gitignored)
- Template: `/.env.example`
- No secret management service
- No cloud secrets manager

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None
- No webhook subscriptions or outgoing notifications

## Service Dependencies

**Backend Services:**
- None (self-contained SQLite backend)

**Frontend Services:**
- None (static assets served via Nginx)

**Network:**
- Backend exposes port 8000 (internal only)
- Frontend exposes port 3000 (public)
- Nginx reverse proxy at port 3000 routes `/api/*` to backend:8000

---

*Integration audit: 2026-02-15*
