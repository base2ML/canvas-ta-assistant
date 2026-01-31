# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Canvas LMS TA Dashboard application with a FastAPI backend and React frontend, designed specifically for Teaching Assistants to manage grading workflow and monitor assignment status across courses.

**Backend**: FastAPI application with SQLite database for Canvas data storage
**Frontend**: React 19.1.1 application built with Vite, styled with Tailwind CSS v4
**Deployment**: Docker Compose for local deployment with Nginx reverse proxy

## Modern Development Stack

- **Frontend Build Tool**: Vite (fast, modern build tool)
- **CSS Framework**: Tailwind CSS v4 (latest version with modern features)
- **React**: 19.1.1 with modern hooks and concurrent features
- **Icons**: Lucide React for consistent iconography
- **Linting**: ESLint 9.x with modern configuration
- **Database**: SQLite for local data persistence

## Development Commands

### Backend (FastAPI)

Run from project root directory:

```bash
# Install dependencies using uv
uv sync

# Run development server locally
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Run with Python directly
uv run python main.py

# Code formatting and linting with Ruff
uv run ruff check .           # Lint code
uv run ruff check . --fix     # Lint and auto-fix
uv run ruff format .          # Format code
uv run mypy .                 # Type checking

# Testing
uv run pytest
```

### Docker Deployment

```bash
# Build and start all services
docker-compose up --build

# Run in background
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Reset database (remove volumes)
docker-compose down -v
```

### Frontend (React + Vite)

Navigate to `canvas-react/` directory:

```bash
# Install dependencies
npm install

# Start Vite development server (http://localhost:5173)
npm run dev

# Build for production (outputs to dist/)
npm run build

# Preview production build
npm run preview

# Run ESLint
npm run lint
```

## Project Structure

```
cda-ta-dashboard/
├── canvas-react/              # Frontend React application
│   ├── src/
│   │   ├── components/        # Reusable UI components
│   │   ├── App.jsx            # Main application with routing
│   │   ├── Settings.jsx       # Course configuration page
│   │   ├── EnhancedTADashboard.jsx
│   │   ├── LateDaysTracking.jsx
│   │   └── PeerReviewTracking.jsx
│   ├── Dockerfile             # Frontend container
│   ├── nginx.conf             # Nginx reverse proxy config
│   └── package.json           # Frontend dependencies
├── main.py                    # FastAPI backend application
├── database.py                # SQLite database schema and operations
├── canvas_sync.py             # Canvas API data fetcher
├── Dockerfile                 # Backend container
├── docker-compose.yml         # Service orchestration
├── pyproject.toml             # Backend dependencies (uv)
├── data/                      # SQLite database (persisted)
└── docs/                      # Documentation
```

## Architecture

### Backend Structure

- **main.py**: FastAPI application with SQLite data integration
- **database.py**: SQLite schema and CRUD operations
- **canvas_sync.py**: Canvas API data fetching and synchronization
- **Dependencies**: FastAPI, canvasapi, Pydantic, Loguru
- **Endpoints**:
  - `GET /health` - Simple health check
  - `GET /api/health` - Detailed health check with DB status
  - **Settings endpoints**:
    - `GET /api/settings` - Get current settings
    - `PUT /api/settings` - Update settings (course ID)
    - `GET /api/settings/courses` - List available Canvas courses
  - **Canvas data endpoints**:
    - `GET /api/canvas/courses` - Get configured courses
    - `GET /api/canvas/assignments/{course_id}` - Get assignments
    - `GET /api/canvas/submissions/{course_id}` - Get submissions
    - `GET /api/canvas/users/{course_id}` - Get users
    - `GET /api/canvas/groups/{course_id}` - Get groups
  - **Sync endpoints**:
    - `POST /api/canvas/sync` - Trigger Canvas data sync
    - `GET /api/canvas/sync/status` - Get last sync status
- **Data Source**: SQLite database with Canvas data synced on startup and manually

### Frontend Structure

- **React 19.1.1** with Vite build system
- **No Authentication** (single-user local deployment)
- **Tailwind CSS v4** for styling
- **Lucide React** for icons
- **Main Views**:
  - `App.jsx` - Main application with routing and refresh button
  - `Settings.jsx` - Course configuration and sync management
  - `EnhancedTADashboard.jsx` - Main TA dashboard
  - `LateDaysTracking.jsx` - Late days tracking
  - `PeerReviewTracking.jsx` - Peer review tracking
- **UI Components** (in components/):
  - `Navigation.jsx` - Navigation bar with Settings link
  - `AssignmentStatusBreakdown.jsx` - Assignment status visualization
  - `SubmissionStatusCards.jsx` - Submission status cards

### Data Models

The backend defines Pydantic models for:

- Health check responses (HealthResponse)
- Settings management
- Course and assignment information
- Assignment status tracking
- TA groups and grading management
- Sync status and history

### Database Schema

SQLite tables in `data/canvas.db`:

- `settings` - Application configuration
- `assignments` - Canvas assignments
- `users` - Enrolled students
- `submissions` - Assignment submissions
- `groups` - TA grading groups
- `group_members` - Group membership
- `sync_history` - Data sync history

## Package Management

- **Backend**: Uses `uv` package manager with pyproject.toml configuration
- **Frontend**: Uses npm with package.json
- **Backend Python version**: >=3.11

## Key Integration Points

- Canvas API integration via `canvasapi` library
- SQLite database for local data persistence
- Data sync on application startup
- Manual sync via Settings page or Refresh button
- Docker Compose for service orchestration
- Nginx reverse proxy for frontend with API routing

## Environment Setup

### Docker Deployment (Recommended)

1. Copy `.env.example` to `.env`
2. Configure Canvas API credentials in `.env`:
   - `CANVAS_API_URL` - Your Canvas instance URL
   - `CANVAS_API_TOKEN` - Your Canvas API token
   - `CANVAS_COURSE_ID` - Optional default course ID
3. Run `docker-compose up --build`

### Local Development

**Backend**:

```bash
# Create .env with Canvas credentials
cp .env.example .env

# Install and run
uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend**:

```bash
cd canvas-react
npm install
npm run dev
```

## Security Best Practices

**CRITICAL**: This application handles sensitive student data (names, grades, submissions) and Canvas API credentials.

### Security Checklist

- [ ] **Never commit `.env` files** - they contain Canvas API tokens
- [ ] **Use placeholder data** in examples and documentation
- [ ] **Check git status** before commits to verify no sensitive files staged
- [ ] **Handle student data** according to FERPA guidelines

### What NOT to Commit

❌ **Files:**

- `.env` files with real credentials
- The `data/` directory with Canvas data
- Screenshots with student information

✅ **Always Use:**

- `.env.example` files with placeholder values
- Generic examples in documentation

### Data Privacy

This application accesses protected student data under FERPA:

- **Student names and IDs**: Personally identifiable information
- **Grades and submissions**: Educational records
- **Course enrollment**: Student status information

## Development Guidelines

- Ensure that any logging is done via Loguru following all best practices
- Canvas API integration uses the `canvasapi` library
- The full documentation for CanvasAPI: https://canvasapi.readthedocs.io/en/stable/
