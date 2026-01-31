# Canvas TA Dashboard - Local Docker Architecture

## Executive Summary

**Objective**: Deploy Canvas TA Dashboard as a local-only application using Docker Compose for single-user use.

**Key Features**:

- Single-command deployment via Docker Compose
- SQLite database for local data persistence
- No cloud dependencies or authentication
- Canvas data sync on startup and manual refresh
- Settings UI for course configuration

## Architecture Overview

### Design Principles

- **Local-First**: All data stored locally in SQLite
- **Simple Deployment**: Single `docker-compose up` command
- **No Authentication**: Single-user local deployment
- **Docker-Based**: Containerized services for consistency

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      User's Machine                              │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                  Docker Compose                             │ │
│  │                                                             │ │
│  │  ┌─────────────────────┐    ┌─────────────────────────┐   │ │
│  │  │   Frontend (Nginx)  │    │   Backend (FastAPI)     │   │ │
│  │  │   Port 3000         │───▶│   Port 8000             │   │ │
│  │  │                     │    │                         │   │ │
│  │  │  • React SPA        │    │  • REST API             │   │ │
│  │  │  • Reverse Proxy    │    │  • Canvas Sync          │   │ │
│  │  │  • Static Assets    │    │  • SQLite Access        │   │ │
│  │  └─────────────────────┘    └───────────┬─────────────┘   │ │
│  │                                          │                  │ │
│  │                              ┌───────────▼─────────────┐   │ │
│  │                              │   SQLite Database       │   │ │
│  │                              │   ./data/canvas.db      │   │ │
│  │                              │                         │   │ │
│  │                              │  • Settings             │   │ │
│  │                              │  • Assignments          │   │ │
│  │                              │  • Submissions          │   │ │
│  │                              │  • Users & Groups       │   │ │
│  │                              └─────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│                              │                                   │
│                              ▼                                   │
│                    ┌─────────────────┐                          │
│                    │   Canvas API    │                          │
│                    │   (External)    │                          │
│                    └─────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

## Service Components

### 1. Frontend Service (Nginx + React)

**Technology**: React SPA served by Nginx

**Container**: `ta-dashboard-frontend`

**Port**: 3000

**Responsibilities**:

- Serve React static assets
- Reverse proxy API requests to backend
- SPA routing (fallback to index.html)

**Nginx Configuration**:

- `/` → Static React files
- `/api/*` → Proxy to backend:8000
- `/health` → Proxy to backend:8000

### 2. Backend Service (FastAPI + SQLite)

**Technology**: Python 3.11 + FastAPI + SQLite

**Container**: `ta-dashboard-backend`

**Port**: 8000

**Responsibilities**:

- REST API endpoints
- Canvas API integration
- SQLite database operations
- Data synchronization

**Key Modules**:

- `main.py` - FastAPI application
- `database.py` - SQLite schema and operations
- `canvas_sync.py` - Canvas data fetching

### 3. Data Storage (SQLite)

**Location**: `./data/canvas.db`

**Persistence**: Docker volume mount

**Tables**:

| Table | Purpose |
|-------|---------|
| `settings` | Application configuration |
| `assignments` | Canvas assignments |
| `users` | Enrolled students |
| `submissions` | Assignment submissions |
| `groups` | TA grading groups |
| `group_members` | Group membership |
| `sync_history` | Sync operation history |

## Data Flow

### Startup Sync

```
1. Docker Compose starts services
2. Backend initializes SQLite database
3. If course ID configured:
   a. Backend connects to Canvas API
   b. Fetches assignments, users, submissions, groups
   c. Stores data in SQLite
4. Frontend becomes available
```

### Manual Sync

```
1. User clicks "Refresh Data" or "Sync Now"
2. Frontend calls POST /api/canvas/sync
3. Backend fetches fresh data from Canvas API
4. Backend updates SQLite database
5. Frontend reloads data from backend
```

### Data Query

```
1. Frontend requests data (e.g., GET /api/canvas/assignments/{course_id})
2. Backend queries SQLite database
3. Backend returns JSON response
4. Frontend renders data
```

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
| GET | `/api/canvas/assignments/{course_id}` | Get assignments |
| GET | `/api/canvas/submissions/{course_id}` | Get submissions |
| GET | `/api/canvas/users/{course_id}` | Get users |
| GET | `/api/canvas/groups/{course_id}` | Get groups |

### Sync

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/canvas/sync` | Trigger data sync |
| GET | `/api/canvas/sync/status` | Get last sync status |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Simple health check |
| GET | `/api/health` | Detailed health with DB status |

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CANVAS_API_URL` | Yes | Canvas instance URL |
| `CANVAS_API_TOKEN` | Yes | Canvas API token |
| `CANVAS_COURSE_ID` | No | Default course ID |
| `ENVIRONMENT` | No | Environment name (default: local) |

### Docker Compose Configuration

```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - CANVAS_API_URL=${CANVAS_API_URL}
      - CANVAS_API_TOKEN=${CANVAS_API_TOKEN}
      - CANVAS_COURSE_ID=${CANVAS_COURSE_ID:-}
    volumes:
      - ./data:/app/data

  frontend:
    build: ./canvas-react
    ports:
      - "3000:80"
    depends_on:
      - backend
```

## Deployment

### Quick Start

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with Canvas credentials

# 2. Build and run
docker-compose up --build

# 3. Access dashboard
open http://localhost:3000
```

### Docker Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild
docker-compose up -d --build

# Reset database
docker-compose down -v
```

## Security Considerations

### Local Deployment

- No authentication required (single-user)
- Data stored locally on user's machine
- Canvas API token stored in `.env` file
- SQLite database not encrypted

### Best Practices

- Never commit `.env` files
- Regenerate Canvas tokens periodically
- Handle student data per FERPA guidelines
- Keep `data/` directory in `.gitignore`

## Comparison with Previous AWS Architecture

| Aspect | Previous (AWS) | Current (Local Docker) |
|--------|----------------|------------------------|
| Deployment | Lambda + CloudFront | Docker Compose |
| Database | S3 JSON files | SQLite |
| Authentication | JWT + bcrypt | None (single-user) |
| Data Sync | Scheduled Lambda | On-demand + startup |
| Cost | ~$15-25/month | Free (local) |
| Scalability | Auto-scaling | Single user |
| Dependencies | AWS services | Docker only |
