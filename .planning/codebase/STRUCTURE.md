# Codebase Structure

**Analysis Date:** 2026-02-15

## Directory Layout

```
cda-ta-dashboard/
├── canvas-react/              # Frontend React application
│   ├── src/
│   │   ├── components/        # Reusable UI components
│   │   ├── hooks/             # Custom React hooks
│   │   ├── utils/             # Utility functions
│   │   ├── assets/            # Static assets
│   │   ├── App.jsx            # Main application with routing
│   │   ├── main.jsx           # React entry point
│   │   ├── Settings.jsx       # Course configuration page
│   │   ├── EnhancedTADashboard.jsx
│   │   ├── TAGradingDashboard.jsx  # TA grading workload view
│   │   ├── LateDaysTracking.jsx
│   │   ├── PeerReviewTracking.jsx
│   │   ├── EnrollmentTracking.jsx
│   │   └── api.js             # Centralized API client
│   ├── Dockerfile             # Frontend container (Nginx + React)
│   ├── nginx.conf             # Nginx reverse proxy config
│   ├── package.json           # Frontend dependencies
│   └── vite.config.js        # Vite build configuration
├── main.py                    # FastAPI backend application
├── database.py                # SQLite database schema and operations
├── canvas_sync.py             # Canvas API data fetcher
├── pyproject.toml             # Backend dependencies (uv)
├── Dockerfile                 # Backend container (Python + FastAPI)
├── docker-compose.yml         # Service orchestration
├── data/                      # SQLite database (persisted)
├── docs/                      # Documentation
└── scripts/                   # Test and utility scripts
```

## Directory Purposes

**canvas-react/** - Frontend Application
- Purpose: React 19.1.1 SPA with Vite build system, Tailwind CSS v4 styling
- Contains: All frontend code, tests, build artifacts
- Key files: `src/App.jsx`, `src/api.js`, `package.json`, `vite.config.js`

**canvas-react/src/components/** - UI Components
- Purpose: Reusable React components for shared UI patterns
- Contains: Navigation, AssignmentStatusBreakdown, SubmissionStatusCards
- Key files: `Navigation.jsx`, `AssignmentStatusBreakdown.jsx`, `SubmissionStatusCards.jsx`

**canvas-react/src/hooks/** - Custom Hooks
- Purpose: Reusable React hooks for state management patterns
- Contains: `useExpandableSet` for expandable UI elements
- Key files: `useExpandableSet.js`

**canvas-react/src/utils/** - Utility Functions
- Purpose: Helper functions for common operations
- Contains: Date formatting utilities
- Key files: `dates.js`

**data/** - Persistent Data Storage
- Purpose: SQLite database file and logs directory
- Contains: `canvas.db` (SQLite database), logs/
- Generated: Yes (by backend on first run)
- Committed: No (gitignored)

**docs/** - Documentation
- Purpose: Project documentation and guides
- Contains: ARCHITECTURE.md, AGENTS.md, CANVAS_DATA_STRUCTURES.md, SECURITY.md
- Key files: `AGENTS.md` (development guide), `ARCHITECTURE.md` (system overview)

**scripts/** - Utility Scripts
- Purpose: Test and development helper scripts
- Contains: `test-backend-local.sh`, `test-frontend-local.sh`, `test-integration.sh`

## Key File Locations

**Entry Points:**
- `main.py`: FastAPI backend application entry point
- `canvas-react/src/main.jsx`: React application mount point
- `canvas-react/src/App.jsx`: Main React component with routing
- `docker-compose.yml`: Docker Compose orchestration entry

**Configuration:**
- `pyproject.toml`: Backend Python dependencies and tool config
- `canvas-react/package.json`: Frontend npm dependencies
- `canvas-react/vite.config.js`: Vite build and test configuration
- `canvas-react/nginx.conf`: Nginx reverse proxy configuration
- `.env`: Environment variables (not committed)
- `.env.example`: Environment variable template

**Core Logic:**
- `database.py`: SQLite schema, CRUD operations, transaction management
- `canvas_sync.py`: Canvas API client, data synchronization
- `canvas-react/src/api.js`: Centralized API fetch wrapper

**Testing:**
- `canvas-react/src/*.test.jsx`: Vitest test files (EnhancedTADashboard.test.jsx, LateDaysTracking.test.jsx, PeerReviewTracking.test.jsx, EnrollmentTracking.test.jsx)

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `canvas_sync.py`, `database.py`)
- React components: `PascalCase.jsx` (e.g., `EnhancedTADashboard.jsx`, `Settings.jsx`)
- React hooks: `camelCase.js` (e.g., `useExpandableSet.js`)
- Utils: `camelCase.js` (e.g., `dates.js`)
- Config files: `kebab-case` (e.g., `vite.config.js`, `nginx.conf`)

**Directories:**
- Source directories: `camelCase` (e.g., `canvas-react`, `components`, `hooks`, `utils`)
- Config directories: `kebab-case` or lowercase (e.g., `docs`, `scripts`, `logs`, `data`)

## Where to Add New Code

**New Feature (Backend API):**
- Primary code: Add endpoints to `main.py` under appropriate section (health, settings, canvas data, dashboard)
- Database operations: Add CRUD functions to `database.py`
- Tests: Add tests to `tests/` directory (Python pytest)

**New Feature (Frontend UI):**
- Primary code: Add component to `canvas-react/src/` as `PascalCase.jsx`
- Reusable components: Add to `canvas-react/src/components/` directory
- Routing: Add route to `canvas-react/src/App.jsx` `<Routes>` section
- Tests: Add test to `canvas-react/src/` as `ComponentName.test.jsx`

**New Component/Module (Frontend):**
- Implementation: `canvas-react/src/` for pages, `canvas-react/src/components/` for reusable components
- Custom hooks: `canvas-react/src/hooks/` as `useHookName.js`
- Utilities: `canvas-react/src/utils/` as `utilityName.js`

**Utilities:**
- Shared helpers: `canvas-react/src/utils/` (date formatting, data transformation)
- API helpers: Extend `canvas-react/src/api.js` with new fetch wrappers

## Special Directories

**.venv/** - Python Virtual Environment
- Purpose: Python dependencies installed by uv
- Generated: Yes
- Committed: No (gitignored)

**canvas-react/node_modules/** - npm Dependencies
- Purpose: JavaScript dependencies installed by npm
- Generated: Yes
- Committed: No (gitignored)

**canvas-react/dist/** - Production Build Artifacts
- Purpose: Vite build output (served by Nginx)
- Generated: Yes (via `npm run build`)
- Committed: No (gitignored)

**logs/** - Application Logs
- Purpose: Loguru logger output directory
- Generated: Yes
- Committed: No (gitignored)

**data/** - SQLite Database
- Purpose: Persistent SQLite database file
- Generated: Yes (via `database.init_db()`)
- Committed: No (gitignored)

---

*Structure analysis: 2026-02-15*
