# Testing

**Analysis Date:** 2026-02-15

## Framework

**Backend (Python):**
- pytest 7.4.0+ - Primary testing framework
- pytest-asyncio 0.21.0+ - Async test support
- httpx 0.25.0+ - HTTP client mocking
- Configured in `pyproject.toml` under `[tool.pytest.ini_options]`
- Test markers: `slow`, `integration`, `unit`
- Async mode: `auto`

**Frontend (JavaScript/React):**
- Vitest 4.0.14 - Primary testing framework
- React Testing Library 16.3.0 - React component testing
- jsdom 27.2.0 - DOM simulation
- user-event 14.6.1 - User interaction simulation
- @testing-library/jest-dom 6.9.1 - Jest DOM matchers
- Configured in `canvas-react/vite.config.js` under `test` section

## Test Structure

**Backend:**
- No dedicated `tests/` directory found in project root
- Tests appear to be minimal or absent
- Test configuration exists in `pyproject.toml` but no test files discovered

**Frontend:**
- Tests co-located with source files using `.test.jsx` suffix
- Test files found:
  - `canvas-react/src/EnhancedTADashboard.test.jsx`
  - `canvas-react/src/LateDaysTracking.test.jsx` (38 lines, minimal)
  - `canvas-react/src/PeerReviewTracking.test.jsx`
  - `canvas-react/src/EnrollmentTracking.test.jsx` (36 lines, minimal)
- Test files in `canvas-react/src/` directory, not in separate `tests/` folder

## Mocking

**Backend:**
- httpx library available for HTTP client mocking
- No explicit mock patterns observed in codebase

**Frontend:**
- API mocking with `vi.mock('./api')` in test files
- Example from `PeerReviewTracking.test.jsx`:
```javascript
import * as api from './api';
vi.mock('./api');
```
- Mocked functions return sample data:
```javascript
const mockPeerReviewData = {
    assignment_id: 1,
    assignment_name: 'Assignment 1',
    deadline: '2025-02-01T12:00:00Z',
    summary: { total_reviews: 10, on_time: 5, late: 3, missing: 2 },
    events: [...],
};
```

## Coverage

**No coverage reports found.** Neither pytest-cov nor Vitest coverage appears to be actively used or generated.

**Configuration present but likely not enforced:**
- Backend: `coverage` package in dev-dependencies with tool configuration in `pyproject.toml`
- Frontend: No explicit coverage configuration in `vite.config.js`

**Coverage tool configuration exists:**
- `tool.coverage.run` with source paths in `pyproject.toml`
- Omit patterns for tests, venv, cache, __pycache__
- `tool.coverage.report` with exclude lines for debug code, repr, etc.

**Gap:** No evidence of regular coverage runs or thresholds being enforced in CI.

## Test Execution

**Backend Commands:**
```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_file.py

# Run with markers
uv run pytest -m "not slow"
uv run pytest -m integration
uv run pytest -m unit
```

**Frontend Commands:**
```bash
# Run all tests (from canvas-react/)
npm run test

# Run tests in watch mode
npm run test -- --watch

# Run tests with UI
npm run test -- --ui
```

**CI Integration:**
- GitHub Actions workflow: `/.github/workflows/ci.yml`
- Jobs include:
  - `backend-tests` - Runs pytest
  - `frontend-tests` - Runs ESLint, build, Vitest tests

## Test Patterns

**Frontend Component Tests:**

**Common Pattern:**
```javascript
describe('ComponentName', () => {
  const mockCourses = [{ id: '123', name: 'Test Course' }];

  it('renders without crashing and shows page title', () => {
    render(
      <BrowserRouter>
        <ComponentName
          courses={mockCourses}
          onLoadCourses={vi.fn()}
        />
      </BrowserRouter>
    );

    expect(screen.getByText(/Page Title/i)).toBeInTheDocument();
  });

  it('shows no course message when courses are empty', () => {
    render(
      <BrowserRouter>
        <ComponentName courses={[]} onLoadCourses={vi.fn()} />
      </BrowserRouter>
    );

    expect(screen.getByText(/No course/i)).toBeInTheDocument();
  });
});
```

**Test Helper:**
- `vi.fn()` for mocking callback functions
- `render()` from React Testing Library for component mounting
- `screen` for querying rendered DOM
- `BrowserRouter` wrapper for components using routing

**Async Testing Pattern:**
```javascript
it('loads data and displays correctly', async () => {
  // Mock API response
  api.apiFetch.mockResolvedValue(mockData);

  render(<Component />);

  // Wait for async operations
  await waitFor(() => {
    expect(screen.getByText(/Data Item/i)).toBeInTheDocument();
  });
});
```

## CI/CD Testing

**GitHub Actions Workflows:**
Located in `/.github/workflows/ci.yml`

**Backend Test Job:**
```yaml
backend-tests:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: uv sync --dev
    - name: Run pytest
      run: uv run pytest
```

**Frontend Test Job:**
```yaml
frontend-tests:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Setup Node
      uses: actions/setup-node@v4
      with:
        node-version: '20'
    - name: Install dependencies
      run: npm ci
    - name: Run ESLint
      run: npm run lint
    - name: Build
      run: npm run build
    - name: Run Vitest
      run: npm run test
```

## Test Gaps

**Backend:**
- No test files found despite pytest configuration
- No API endpoint tests (all FastAPI routes untested)
- No database operation tests (SQLite CRUD functions untested)
- No Canvas API sync tests
- No error handling or edge case tests

**Frontend:**
- Test files exist but are minimal (lateDaysTracking: 38 lines, EnrollmentTracking: 36 lines)
- No integration tests for multi-component flows
- API error handling not tested
- User interaction flows not tested
- No visual regression tests
- Coverage not measured or enforced

**Recommendation:** Add comprehensive test coverage, especially for:
1. Backend API endpoints
2. Canvas sync process
3. Database operations
4. Frontend component edge cases
5. API error scenarios

---

*Testing analysis: 2026-02-15*
