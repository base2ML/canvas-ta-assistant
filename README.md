# CDA TA Dashboard

A Canvas LMS Teaching Assistant Dashboard application designed to streamline grading workflow and monitor assignment status across courses. Runs locally via Docker Compose with SQLite storage.

## Features

- **Assignment Tracking**: Monitor assignment status with due dates and direct Canvas links
- **TA Grading Management**: Specialized dashboard for workload distribution across TA groups with configurable grading deadlines
- **Grade Analysis**: Grade distribution histograms, box plots, and per-TA breakdowns by assignment
- **Late Days Tracking**: Track and manage student late day usage with semester bank system
- **Peer Review Tracking**: Monitor peer review completion status
- **Enrollment Tracking**: Enrollment history over time with step-chart visualization
- **Comment Templates**: Manage and post reusable grading comment templates to Canvas
- **Course Filtering**: Efficient workflow with course and assignment filtering
- **Settings UI**: Easy course configuration through web interface

## Architecture

### Backend (FastAPI + SQLite)
- **FastAPI**: Modern async Python web framework
- **SQLite**: Local database for Canvas data storage
- **canvasapi**: Official Canvas LMS Python library
- **Pydantic v2**: Data validation and settings management
- **Loguru**: Structured logging

### Frontend (React + Vite)
- **React 19.1.1**: Modern UI library with concurrent features
- **Vite**: Fast, modern build tool
- **Tailwind CSS v4**: Utility-first CSS framework
- **Lucide React**: Consistent iconography

### Deployment
- **Docker Compose**: Single-command local deployment
- **Nginx**: Reverse proxy for frontend with API proxying

## Quick Start

### Prerequisites

- **Docker** and **Docker Compose**
- **Canvas LMS API Token** ([How to generate](#generating-canvas-api-tokens))

### 1. Setup Environment

```bash
# Clone the repository
git clone https://github.com/base2ML/cda-ta-dashboard.git
cd cda-ta-dashboard

# Copy environment template
cp .env.example .env

# Edit .env with your Canvas credentials
nano .env
```

Configure these required values in `.env`:
```bash
CANVAS_API_URL=https://your-school.instructure.com
CANVAS_API_TOKEN=your-canvas-api-token-here
CANVAS_COURSE_ID=  # Optional - can be set via Settings UI
```

### 2. Build and Run

```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

### 3. Access the Dashboard

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### 4. Configure Course

1. Navigate to **Settings** in the dashboard
2. Enter your Canvas Course ID or browse available courses
3. Click **Save & Sync** to fetch Canvas data

## Development

### Local Backend Development

```bash
# Install dependencies using uv
uv sync

# Run development server
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Code formatting and linting
uv run ruff check .           # Lint code
uv run ruff check . --fix     # Lint and auto-fix
uv run ruff format .          # Format code

# Run tests
uv run pytest
```

### Local Frontend Development

```bash
cd canvas-react

# Install dependencies
npm install

# Start development server (http://localhost:5173)
npm run dev

# Build for production
npm run build

# Run ESLint
npm run lint

# Run tests (Vitest)
npm run test
```

## Project Structure

```
cda-ta-dashboard/
├── main.py                     # FastAPI application entry point
├── database.py                 # SQLite database schema and operations
├── canvas_sync.py              # Canvas API data fetcher
├── Dockerfile                  # Backend container
├── docker-compose.yml          # Service orchestration
├── pyproject.toml              # Backend dependencies (uv)
├── canvas-react/               # React frontend
│   ├── src/
│   │   ├── App.jsx             # Main application with routing
│   │   ├── Settings.jsx        # Course configuration page
│   │   ├── EnhancedTADashboard.jsx
│   │   ├── GradeAnalysis.jsx   # Grade distribution charts and per-TA breakdown
│   │   ├── LateDaysTracking.jsx
│   │   ├── EnrollmentTracking.jsx
│   │   ├── PeerReviewTracking.jsx
│   │   ├── components/
│   │   │   ├── Navigation.jsx
│   │   │   ├── AssignmentStatusBreakdown.jsx
│   │   │   ├── SubmissionStatusCards.jsx
│   │   │   ├── GradeBoxPlot.jsx
│   │   │   ├── GradeHistogram.jsx
│   │   │   └── GradingScheduleSummary.jsx
│   │   └── hooks/
│   │       ├── useExpandableSet.js
│   │       └── useSSEPost.js
│   ├── Dockerfile              # Frontend container
│   └── nginx.conf              # Nginx reverse proxy config
├── scripts/                    # Utility and deployment scripts
│   ├── deploy-production.sh
│   ├── deploy-sandbox.sh
│   ├── test-backend-local.sh
│   ├── test-frontend-local.sh
│   └── test-integration.sh
├── data/                       # SQLite database (persisted)
├── docs/                       # Documentation
└── .env.example                # Environment template
```

## API Endpoints

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Simple health check |
| GET | `/api/health` | Detailed health with DB status |

### Settings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings` | Get current settings |
| PUT | `/api/settings` | Update settings |
| GET | `/api/settings/courses` | List available Canvas courses |
| GET | `/api/settings/api-user` | Get Canvas API user info |

### Canvas Data
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/canvas/courses` | List configured courses |
| GET | `/api/canvas/data/{course_id}` | Get all course data (assignments, submissions, users, groups) |
| GET | `/api/canvas/assignments/{course_id}` | Get assignments |
| GET | `/api/canvas/submissions/{course_id}` | Get submissions |
| GET | `/api/canvas/users/{course_id}` | Get students |
| GET | `/api/canvas/groups/{course_id}` | Get groups |
| GET | `/api/canvas/ta-users/{course_id}` | Get TA users |
| GET | `/api/canvas/assignment-groups/{course_id}` | Get assignment groups |
| GET | `/api/canvas/peer-review-assignments/{course_id}` | Get peer review assignments |
| GET | `/api/canvas/peer-review-deadline/{course_id}` | Get peer review deadline |
| GET | `/api/canvas/peer-reviews/{course_id}` | Get peer review data |

### Sync
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/canvas/sync` | Trigger Canvas data sync |
| GET | `/api/canvas/sync/status` | Get last sync status |

### Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/submission-status/{course_id}` | Submission status breakdown |
| GET | `/api/dashboard/ta-grading/{course_id}` | TA grading workload data |
| GET | `/api/dashboard/grading-deadlines/{course_id}` | Assignments with grading deadlines and overdue status |
| PUT | `/api/dashboard/grading-deadlines/{course_id}/{assignment_id}` | Update grading deadline for assignment |
| POST | `/api/dashboard/grading-deadlines/{course_id}/propagate-defaults` | Apply default turnaround to all assignments |
| GET | `/api/dashboard/grade-distribution/{course_id}` | List assignments with graded submission counts |
| GET | `/api/dashboard/grade-distribution/{course_id}/{assignment_id}` | Full grade stats, histogram, and per-TA breakdown |
| GET | `/api/dashboard/late-days/{course_id}` | Late days usage per student |
| GET | `/api/dashboard/peer-reviews/{course_id}` | Peer review completion analysis |
| GET | `/api/dashboard/enrollment-history/{course_id}` | Enrollment history over time |

### Comment Templates
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/templates` | List comment templates |
| POST | `/api/templates` | Create comment template |
| PUT | `/api/templates/{template_id}` | Update comment template |
| DELETE | `/api/templates/{template_id}` | Delete comment template |
| POST | `/api/comments/preview/{assignment_id}` | Preview comment posting |
| POST | `/api/comments/post/{assignment_id}` | Post comments to Canvas |
| GET | `/api/comments/history` | Get comment post history |

Full API documentation available at `/docs` (Swagger UI) when running.

## Generating Canvas API Tokens

1. Log into your Canvas instance (e.g., `https://your-school.instructure.com`)
2. Navigate to **Account → Settings → Approved Integrations**
3. Click **+ New Access Token**
4. Set a descriptive purpose (e.g., "TA Dashboard")
5. Set an expiration date (recommended: 90 days)
6. Copy the token immediately (it will only be shown once)

## Docker Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# Remove volumes (reset database)
docker-compose down -v
```

## Data Storage

Canvas data is stored in a SQLite database at `./data/canvas.db`. This directory is mounted as a Docker volume for persistence.

### Database Tables
- `settings` - Application configuration (course ID, etc.)
- `assignments` - Canvas assignments
- `users` - Enrolled students
- `submissions` - Assignment submissions
- `groups` - TA grading groups
- `group_members` - Group membership
- `sync_history` - Data sync history

## Security

**IMPORTANT**: This application handles sensitive student data.

### Security Notes
- **API Token**: Store Canvas API token in `.env` file only (never commit)
- **Local Only**: This deployment is designed for local/single-user use
- **Data Privacy**: Student data is stored locally in SQLite
- **FERPA**: Handle student data according to your institution's policies

### What NOT to Commit
- `.env` files with real credentials
- The `data/` directory with actual Canvas data
- Screenshots with student information

## Troubleshooting

### "Connection refused" errors
- Ensure Docker containers are running: `docker-compose ps`
- Check logs: `docker-compose logs backend`

### No data showing in dashboard
- Verify Canvas API token is valid
- Check Settings page for sync errors
- Try manual sync via Settings → "Sync Now"

### Canvas API errors
- Verify your API token has appropriate permissions
- Check if course ID is correct
- Ensure Canvas instance URL is correct

## Contributing

### Code Style
- **Python**: Ruff (formatting + linting)
- **JavaScript/React**: ESLint with React hooks rules
- **Commits**: Conventional commits preferred

## License

[Add license information here]

---

**Maintained by**: CDA TA Dashboard Team
