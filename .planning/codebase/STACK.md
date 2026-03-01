# Technology Stack

**Analysis Date:** 2026-02-15

## Languages

**Primary:**
- Python 3.11+ - Backend (FastAPI application, Canvas API integration, SQLite operations)

**Secondary:**
- JavaScript (ES2020+) - Frontend (React components, API client)
- HTML - Frontend templates and markup

## Runtime

**Environment:**
- Python 3.11 (backend container)
- Node.js 20 (frontend build stage)
- Docker for containerized deployment

**Package Manager:**
- Backend: `uv` (modern Python package manager)
  - Lockfile: `uv.lock` present
- Frontend: `npm`
  - Lockfile: `canvas-react/package-lock.json` present

## Frameworks

**Core:**
- FastAPI 0.104.0+ - REST API framework for backend (`/main.py`)
- React 19.1.1 - Frontend UI library (`/canvas-react/src/`)
- React Router DOM 7.9.6 - Client-side routing (`/canvas-react/src/App.jsx`)

**Testing:**
- pytest 7.4.0+ - Python testing framework
- Vitest 4.0.14 - React testing framework
- React Testing Library 16.3.0 - React component testing (`/canvas-react/src/*.test.jsx`)
- pytest-asyncio 0.21.0+ - Async testing support
- jsdom 27.2.0 - DOM simulation for frontend tests

**Build/Dev:**
- Vite 7.1.2 - Frontend build tool and dev server (`/canvas-react/vite.config.js`)
- Tailwind CSS 4.1.12 - CSS framework with Vite plugin (`/canvas-react/vite.config.js`)
- Ruff 0.8.0+ - Python linting and formatting (replaces Black, flake8, isort)
- mypy 1.5.0+ - Python type checking
- ESLint 9.33.0 - JavaScript/React linting (`/canvas-react/eslint.config.js`)

## Key Dependencies

**Critical:**
- canvasapi 3.0.0+ - Canvas LMS API client library (`/canvas_sync.py`)
- pydantic 2.0.0+ - Data validation and settings (`/main.py`, `/database.py`)
- uvicorn[standard] 0.24.0+ - ASGI server for FastAPI

**Infrastructure:**
- Docker/Docker Compose - Container orchestration (`/docker-compose.yml`, `/Dockerfile`, `/canvas-react/Dockerfile`)
- nginx:alpine - Frontend web server and reverse proxy (`/canvas-react/nginx.conf`)
- sqlite3 (Python stdlib) - Local database (`/database.py`)

**Frontend UI:**
- lucide-react 0.539.0+ - Icon library (`/canvas-react/src/App.jsx`)
- @tailwindcss/vite 4.1.12 - Tailwind Vite plugin

**Frontend Dev:**
- @vitejs/plugin-react 5.0.0 - React plugin for Vite
- eslint-plugin-react-hooks 5.2.0 - React hooks linting
- eslint-plugin-react-refresh 0.4.20 - Fast refresh linting

**Backend Utilities:**
- loguru 0.7.3+ - Structured logging (`/main.py`, `/canvas_sync.py`, `/database.py`)
- python-dateutil 2.8.0+ - Date parsing (`/main.py`)
- httpx 0.25.0+ - Async HTTP client
- slowapi 0.1.9+ - Rate limiting

## Configuration

**Environment:**
- Environment variables via `.env` file (gitignored)
- Template: `/.env.example`
- `.env.test` for test-specific settings

**Key configs required:**
- `CANVAS_API_URL` - Canvas instance URL
- `CANVAS_API_TOKEN` - Canvas API token
- `CANVAS_COURSE_ID` - Default course ID (optional)
- `ENVIRONMENT` - Environment name (default: local)

**Build:**
- `pyproject.toml` - Python dependencies and tooling config
- `/canvas-react/package.json` - Frontend dependencies
- `/canvas-react/vite.config.js` - Vite configuration
- `/canvas-react/eslint.config.js` - ESLint configuration
- `/.pre-commit-config.yaml` - Pre-commit hooks configuration

**Docker:**
- `/docker-compose.yml` - Service orchestration
- `/Dockerfile` - Backend container definition
- `/canvas-react/Dockerfile` - Frontend container definition
- `/canvas-react/nginx.conf` - Nginx reverse proxy config

## Platform Requirements

**Development:**
- Python 3.11 or higher
- Node.js 20
- uv package manager (for Python)
- npm (for Node.js)
- Docker and Docker Compose (optional for local dev)

**Production:**
- Docker-compatible environment
- No external cloud services required
- Canvas LMS API access (external dependency)

---

*Stack analysis: 2026-02-15*
