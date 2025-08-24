# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Canvas LMS TA Dashboard application with a FastAPI backend and React frontend, designed specifically for Teaching Assistants to manage grading workflow and monitor assignment status across courses.

**Backend**: FastAPI application using the official canvasapi Python library to interact with Canvas LMS
**Frontend**: React 19.1.1 application built with Vite, styled with Tailwind CSS v4

## Modern Development Stack

- **Frontend Build Tool**: Vite (fast, modern build tool replacing Create React App)
- **CSS Framework**: Tailwind CSS v4 (latest version with modern features)
- **React**: 19.1.1 with modern hooks and concurrent features
- **Icons**: Lucide React for consistent iconography
- **Linting**: ESLint 9.x with modern configuration

## Development Commands

### Backend (FastAPI)
Navigate to `backend-canvas-fastapi/` directory:

```bash
# Install dependencies using uv
uv sync

# Run development server
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Run with Python directly
uv run python main.py

# Code formatting and linting
uv run black .
uv run isort .
uv run flake8 .
uv run mypy .

# Testing
uv run pytest
uv run pytest --cov=src
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

# Run tests (if configured)
npm test
```

## Architecture

### Backend Structure
- **main.py**: Single FastAPI application file containing all endpoints and business logic
- **Dependencies**: Uses canvasapi library for Canvas LMS integration, FastAPI for REST API, Pydantic for data validation
- **Endpoints**:
  - `GET /api/health` - Health check
  - `POST /api/validate-credentials` - Validate Canvas API credentials
  - `POST /api/test-connection` - Test Canvas connection
  - `POST /api/assignments` - Fetch assignments from specified courses
  - `POST /api/assignment/{id}/details` - Get detailed assignment information
  - `POST /api/ta-groups/{course_id}` - Fetch TA groups (excluding Term Project groups)
  - `POST /api/ta-grading` - Get ungraded submissions with TA assignment information
- **Async Design**: Uses ThreadPoolExecutor to run synchronous Canvas API calls in async context
- **CORS**: Configured to allow all origins (should be restricted in production)

### Frontend Structure
- **React 19.1.1** with Vite build system
- **Tailwind CSS v4** for styling (configured as dev dependency via @tailwindcss/vite)
- **Lucide React** for icons
- **Modern Hooks**: Uses useCallback, useEffect, useState with proper dependency arrays
- **ESLint**: Configured with react-hooks rules and modern JavaScript standards
- **Components**:
  - `App.jsx` - Main TA dashboard with assignment tracking and filtering
  - `TAGradingDashboard.jsx` - Specialized TA grading management interface
- **Features**:
  - Assignment status tracking with due dates and direct Canvas links
  - TA grading dashboard with workload distribution across TA groups
  - Course and assignment filtering for efficient workflow
  - Real-time Canvas API integration
  - Dual view system: Assignment List + TA Grading Management

### Data Models
The backend defines comprehensive Pydantic models for:
- Canvas credentials and user profiles
- Course and assignment information
- Assignment status tracking (not_submitted, pending, graded, excused)
- TA groups and grading management (TAGroup, UngradedSubmission, TAGradingResponse)
- API responses with error handling

## Package Management

- **Backend**: Uses `uv` package manager with pyproject.toml configuration
- **Frontend**: Uses npm with package.json
- **Backend Python version**: >=3.8.1

## Key Integration Points

- Canvas API authentication via API tokens
- Assignment status determination based on submission state
- Concurrent processing of multiple courses
- Error handling for Canvas API exceptions
- Thread-safe async/sync bridging for Canvas API calls

## Environment Setup

### Backend Configuration
The backend expects Canvas base URL and API token to be provided via API requests (no environment variables for credentials).
Port configuration: Backend defaults to port 8000, configurable via PORT environment variable.

### Frontend Environment Variables
The React frontend supports environment variables for default Canvas API configuration. Create a `.env` file in the `canvas-react/` directory:

```bash
# Canvas API Configuration - Default values for UI
VITE_CANVAS_API_URL=https://your-school.instructure.com
VITE_CANVAS_API_KEY=your-canvas-api-token-here
VITE_CANVAS_COURSE_ID=12345
VITE_BACKEND_URL=http://localhost:8000
```

**Priority Order:**
1. **Saved user values** (localStorage) - highest priority
2. **Environment variables** (.env file) - fallback defaults  
3. **Empty/placeholder values** - lowest priority

**Security Notes:**
- The `.env` file is gitignored to prevent committing sensitive credentials
- Use `.env.example` as a template for team members
- Environment variables are prefixed with `VITE_` to be accessible in the frontend
- API tokens in environment variables will show as dots (••••) in password fields

## Development Guidelines

### Using Context7 MCP Server for Modern Coding Practices

When working with this codebase, leverage the Context7 MCP server to ensure modern, up-to-date coding practices:

#### For React/Frontend Development
Use Context7 to get the latest documentation and best practices for:
- **React 19.1.1**: `resolve-library-id "react"` then `get-library-docs` for latest hooks, concurrent features, and patterns
- **Vite**: `resolve-library-id "vite"` for modern build configuration and optimization
- **Tailwind CSS v4**: `resolve-library-id "tailwindcss"` for latest utility classes and configuration
- **Lucide React**: `resolve-library-id "lucide-react"` for icon usage and best practices

#### For Backend Development  
Use Context7 to get current documentation for:
- **FastAPI**: `resolve-library-id "fastapi"` for latest async patterns, dependency injection, and API design
- **Pydantic**: `resolve-library-id "pydantic"` for v2 models, validation, and serialization
- **Python AsyncIO**: `resolve-library-id "asyncio"` for modern concurrent programming patterns

#### Key Areas to Validate with Context7
1. **React Hooks**: Ensure proper useCallback, useEffect dependency arrays, and modern patterns
2. **Vite Configuration**: Verify build optimizations and plugin usage
3. **Tailwind v4**: Check for latest utility classes and configuration options
4. **FastAPI Async**: Confirm modern async/await patterns and error handling
5. **TypeScript/ESLint**: Validate modern linting rules and type safety

#### Best Practices to Follow
- Always use Context7 before implementing new features to get latest syntax
- Check for deprecation warnings and modern alternatives
- Validate dependency management and security practices
- Ensure accessibility and performance best practices

#### Example Context7 Usage
```bash
# Before adding new React features
resolve-library-id "react"
get-library-docs "/facebook/react" topic:"hooks"

# Before modifying Vite config
resolve-library-id "vite" 
get-library-docs "/vitejs/vite" topic:"configuration"

# Before styling changes
resolve-library-id "tailwindcss"
get-library-docs "/tailwindlabs/tailwindcss" topic:"utilities"
```