# Coding Conventions

**Analysis Date:** 2026-02-15

## Naming Patterns

**Files:**
- **Backend Python**: `snake_case.py` for all modules (e.g., `canvas_sync.py`, `database.py`, `main.py`)
- **Frontend React**: `PascalCase.jsx` for components, `camelCase.js` for utilities and hooks (e.g., `EnhancedTADashboard.jsx`, `api.js`, `dates.js`)
- **Test files**: Co-located with source file using `.test.jsx` or `.test.py` suffix (e.g., `EnhancedTADashboard.test.jsx`)

**Functions:**
- **Backend Python**: `snake_case` (e.g., `get_canvas_client()`, `sync_course_data()`, `init_db()`)
- **Frontend React**: `camelCase` for handlers and data fetching (e.g., `loadCourses()`, `handleRefreshData()`, `fetchLateDaysData()`)

**Variables:**
- **Backend Python**: `snake_case` (e.g., `course_id`, `sync_id`, `assignments`)
- **Frontend React**: `camelCase` (e.g., `selectedCourse`, `loading`, `syncMessage`)

**Types/Classes:**
- **Backend Python**: `PascalCase` for classes and Pydantic models (e.g., `HealthResponse`, `SettingsResponse`, `SyncResponse`)
- **Frontend React**: No explicit types (JavaScript), uses PropTypes through prop documentation

## Code Style

**Formatting:**
- **Backend Python**: Ruff formatter (replaces Black)
  - Line length: 88 characters
  - Quote style: Double quotes
  - Indent style: Spaces
  - Configured in `pyproject.toml` under `[tool.ruff.format]`
- **Frontend React**: No explicit formatter configured (Tailwind CSS handles styling, minimal CSS files)
  - Import statement format: Single quotes for imports
  - JSX structure: No inline styles, uses Tailwind CSS utility classes exclusively

**Linting:**
- **Backend Python**: Ruff linter (replaces flake8, isort, Black)
  - Rules: E (pycodestyle errors), W (pycodestyle warnings), F (pyflakes), I (isort), B (flake8-bugbear), C4 (flake8-comprehensions), UP (pyupgrade), ARG (flake8-unused-arguments), SIM (flake8-simplify)
  - Type checking: mypy with strict mode enabled
  - Config: `pyproject.toml`
  - Run commands: `uv run ruff check .`, `uv run ruff check . --fix`, `uv run ruff format .`, `uv run mypy .`
- **Frontend React**: ESLint 9.x with modern flat config
  - Config: `canvas-react/eslint.config.js`
  - Plugins: `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`
  - Run command: `npm run lint`
  - Rule: Unused vars allowed if prefixed with uppercase (e.g., `BACKEND_URL`, `COMPONENT_NAME`)

## Import Organization

**Python Backend Order:**
1. Standard library imports (e.g., `import os`, `from datetime import UTC, datetime`)
2. Third-party imports (e.g., `from fastapi import FastAPI`, `from loguru import logger`)
3. Local imports (e.g., `import canvas_sync`, `import database as db`)
4. Grouped with 2 blank lines between sections

**Python Import Style:**
```python
# Standard library
import os
from datetime import UTC, datetime
from typing import Any

# Third-party
from fastapi import FastAPI, HTTPException, status
from loguru import logger
from pydantic import BaseModel

# Local
import canvas_sync
import database as db
```

**Frontend React Order:**
1. React imports (e.g., `import React, { useState, useEffect } from 'react'`)
2. Third-party library imports (e.g., `import { BrowserRouter, Routes, Route } from 'react-router-dom'`)
3. Icon imports from `lucide-react`
4. Local component imports (e.g., `import EnhancedTADashboard from './EnhancedTADashboard'`)
5. Utility imports (e.g., `import { apiFetch } from './api'`)

**Frontend Import Style:**
```jsx
import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { RefreshCw } from 'lucide-react';
import { apiFetch, BACKEND_URL } from './api';
```

**Path Aliases:**
- No path aliases configured in Vite
- All imports use relative paths from `src/` directory

## Error Handling

**Backend Python Patterns:**
- Use `loguru.logger` for all logging (never `print`)
- Re-raise exceptions with context using `raise ... from e`
- Use `HTTPException` from FastAPI for API errors with appropriate status codes
- Use context managers (`with`) for resource cleanup
- Specific exception handling for `CanvasException` from canvasapi

Example from `/Users/mapajr/git/cda-ta-dashboard/main.py`:
```python
except ValueError as e:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(e),
    ) from e
except Exception as e:
    logger.error(f"Sync failed: {e}", exc_info=True)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Canvas data sync failed",
    ) from e
```

**Frontend React Patterns:**
- Wrap async operations in try-catch blocks
- Set error state variables to display user-friendly messages
- Use `console.error()` for debugging (allowed in frontend)
- Error state is typically a string displayed to user

Example from `/Users/mapajr/git/cda-ta-dashboard/canvas-react/src/Settings.jsx`:
```jsx
try {
    await apiFetch('/api/settings', {
        method: 'PUT',
        body: JSON.stringify({ course_id: manualCourseId.trim() }),
    });
    setMessage({ type: 'success', text: 'Settings saved successfully' });
    loadSettings();
} catch (err) {
    console.error('Error saving settings:', err);
    setMessage({ type: 'error', text: err.message || 'Failed to save settings' });
} finally {
    setSaving(false);
}
```

## Logging

**Backend Framework**: Loguru (`logger`)
- Configured in `/Users/mapajr/git/cda-ta-dashboard/main.py`
- Logs to file: `logs/app.log` with rotation (500 MB) and retention (10 days)
- Default level: INFO

**Backend Logging Patterns:**
```python
logger.info(f"Starting sync for course {course_id} (sync_id: {sync_id})")
logger.warning(f"Startup sync skipped or failed: {e}")
logger.error(f"Canvas API error fetching courses: {e}")
```
- Use f-strings for formatted messages
- Include relevant context (IDs, timestamps, counts)
- Use `exc_info=True` for errors to capture stack traces

**Frontend Logging**: `console` methods
- `console.error()` for errors during development
- `console.log()` for debugging navigation and state changes
- No production logging framework configured

## Comments

**When to Comment:**
- Complex business logic or algorithms
- Database schema migration notes
- Security-sensitive operations
- Non-obvious function behavior
- Why (not what) - comments explain reasoning

**JSDoc/TSDoc:**
- JSDoc comments used for utility functions in `/Users/mapajr/git/cda-ta-dashboard/canvas-react/src/utils/dates.js` and `/Users/mapajr/git/cda-ta-dashboard/canvas-react/src/api.js`
- Include parameter descriptions and return types
- Example:
```javascript
/**
 * Fetch wrapper with error handling and JSON parsing
 * @param {string} endpoint - API endpoint (e.g., '/api/settings')
 * @param {RequestInit} options - Fetch options
 * @returns {Promise<any>} - Parsed JSON response
 */
```

**Python Docstrings:**
- Docstrings on all public functions (Google style not enforced, but descriptive)
- Example from `/Users/mapajr/git/cda-ta-dashboard/database.py`:
```python
def clear_refreshable_data(course_id: str, conn: sqlite3.Connection) -> None:
    """Clear refreshable data for a course (preserves users and submissions).

    This function clears data that gets fully re-fetched during sync:
    - Peer review comments and peer reviews
    - Groups and group members
    - Assignments
    """
```

## Function Design

**Size:** No strict size limit enforced
- Functions should be focused on single responsibility
- Use helper functions and modules for complex operations

**Parameters:**
- **Backend Python**: Type hints required for all function parameters (mypy strict mode)
- **Frontend React**: No type hints (JavaScript), use prop destructuring and comments

**Return Values:**
- **Backend Python**: Explicit return types with type hints (e.g., `dict[str, Any]`, `str | None`)
- **Frontend React**: No explicit return type declarations
- API functions return JSON data from `/Users/mapajr/git/cda-ta-dashboard/canvas-react/src/api.js` via `apiFetch()`

## Module Design

**Exports:**
- **Backend Python**: Named exports via function definitions
- **Frontend React**: Default exports for components (`export default ComponentName`)
- Utilities use named exports (`export function formatDate()`)

**Barrel Files:**
- No barrel files used in current codebase
- Components imported directly from their file paths

**Backend Module Organization:**
- `main.py`: FastAPI app definition and endpoints
- `database.py`: SQLite schema and CRUD operations
- `canvas_sync.py`: Canvas API data fetching and synchronization
- Each module has clear single responsibility

**Frontend Module Organization:**
- `src/components/`: Reusable UI components
- `src/hooks/`: Custom React hooks (e.g., `useExpandableSet.js`)
- `src/utils/`: Utility functions (e.g., `dates.js`)
- `api.js`: Centralized API client
- All pages in `src/` directory root

## Styling Conventions

**Tailwind CSS v4:**
- All styling via Tailwind utility classes
- No custom CSS files except `index.css` with `@import "tailwindcss"`
- No inline styles or CSS modules
- Responsive design using Tailwind breakpoints (e.g., `sm:`, `md:`, `lg:`)

**Color Scheme:**
- Status colors: `green-` for success, `red-` for errors, `amber-`/`yellow-` for warnings, `slate-` for neutral
- Button colors: `blue-600` for primary actions

**Component Pattern:**
- Functional components with hooks only (no class components)
- Props destructured in function signature
- Early returns for null/empty states

---

*Convention analysis: 2026-02-15*
