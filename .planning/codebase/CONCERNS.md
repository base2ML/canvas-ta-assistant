# Codebase Concerns

**Analysis Date:** 2026-02-15

## Tech Debt

### Hardcoded Timezone and Time Format

**Issue**: Multiple frontend components hardcode timezone and locale assumptions.

**Files**:
- `/Users/mapajr/git/cda-ta-dashboard/canvas-react/src/EnhancedTADashboard.jsx` (line 237-241)
- `/Users/mapajr/git/cda-ta-dashboard/canvas-react/src/LateDaysTracking.jsx` (line 331-335)

**Impact**:
- Timezone hardcoded to "America/New_York" (EST)
- Locale hardcoded to "en-US"
- Inconsistent behavior for users in different time zones
- Displays incorrect times for non-US users

**Fix approach**: Extract timezone and locale to environment variables or user preferences, use relative time display where possible

### SQL Injection Risk in Dynamic Query Construction

**Issue**: `upsert_groups()` in database.py constructs SQL dynamically using string interpolation.

**Files**: `/Users/mapajr/git/cda-ta-dashboard/database.py` (lines 550-556)

**Code**:
```python
placeholders = ",".join("?" * len(group_ids))
cursor.execute(
    f"DELETE FROM group_members WHERE group_id IN ({placeholders})",
    group_ids,
)
```

**Impact**:
- While currently using parameterized values for IDs, the pattern is fragile
- Future changes could inadvertently introduce SQL injection

**Fix approach**: Consider using SQLite's more explicit parameter binding or add strict validation before query construction

### Missing Frontend Test Configuration

**Issue**: No vitest.config.js or equivalent found in frontend project.

**Files**: `/Users/mapajr/git/cda-ta-dashboard/canvas-react/` (root directory)

**Impact**:
- Test behavior may be undefined or rely on defaults
- Inconsistent test environment between runs
- Potential test reliability issues

**Fix approach**: Create vitest.config.js with explicit settings for test environment, coverage, and mocks

### Inconsistent Error Handling Patterns

**Issue**: Error handling varies significantly between components and backend endpoints.

**Files**:
- `/Users/mapajr/git/cda-ta-dashboard/canvas-react/src/api.js` (lines 27-35)
- `/Users/mapajr/git/cda-ta-dashboard/main.py` (various endpoints)

**Impact**:
- Some endpoints log errors with `exc_info=True`, others don't
- Frontend errors are logged to console but may not be reported to monitoring
- Inconsistent user error messages

**Fix approach**: Establish consistent error handling patterns, add error reporting/monitoring integration

### Typo in eslint.config.js Import

**Issue**: Import statement uses "config" instead of "config" from eslint package.

**Files**: `/Users/mapajr/git/cda-ta-dashboard/canvas-react/eslint.config.js` (line 5)

**Code**:
```javascript
import { defineConfig, globalIgnores } from 'eslint/config'
```

**Impact**:
- May cause linting configuration failures
- Linting may not work correctly

**Fix approach**: Change import to `import { defineConfig, globalIgnores } from 'eslint/config'` (note: correct path is `eslint/config`)

### Duplicated Code for Assignment Filtering

**Issue**: LateDaysTracking.jsx has complex assignment filtering logic that duplicates patterns.

**Files**: `/Users/mapajr/git/cda-ta-dashboard/canvas-react/src/LateDaysTracking.jsx` (lines 281-349)

**Impact**:
- Assignment filter UI is 69 lines of code
- Similar filtering needs in other components will lead to duplication
- Maintenance burden when adding filter features

**Fix approach**: Extract assignment filter to reusable component in `components/` directory

## Known Bugs

### Typo in EnrollmentTracking.jsx Status Comparisons

**Issue**: Multiple typos in status comparison strings using "dropped" instead of "dropped".

**Files**: `/Users/mapajr/git/cda-ta-dashboard/canvas-react/src/EnrollmentTracking.jsx` (lines 60, 62, 71)

**Code**:
```javascript
} else if (newStatus === 'dropped') {  // typo: missing 'p'
  return <UserMinus className="w-4 h-4 text-red-600" />;
} else if (previousStatus === 'dropped' && newStatus === 'active') {  // typo
  return <UserCheck className="w-4 h-4 text-blue-600" />;
} else if (previousStatus === 'new' && newStatus === 'active') {
  return 'Newly enrolled';
} else if (newStatus === 'dropped') {  // typo
  return 'Dropped';
} else if (previousStatus === 'dropped' && newStatus === 'active') {  // typo
  return 'Re-enrolled';
```

**Symptoms**:
- Enrollment status icons and descriptions won't display correctly for dropped/re-enrolled students
- UI shows fallback gray icons instead of red/orange icons
- Status descriptions may appear incorrectly

**Trigger**: When a student drops a course or re-enrolls

**Workaround**: None - functionality is broken for these cases

**Fix approach**: Correct all instances of "dropped" to "dropped" (lines 60, 62, 71, 72, 74, 75)

### Incomplete Student Name Display

**Issue**: Student email addresses may be empty/null but display logic doesn't handle gracefully.

**Files**:
- `/Users/mapajr/git/cda-ta-dashboard/canvas-react/src/LateDaysTracking.jsx` (line 504)
- `/Users/mapajr/git/cda-ta-dashboard/canvas-react/src/EnhancedTADashboard.jsx` (various locations)

**Impact**:
- Empty email fields may display as "undefined" or blank
- Inconsistent display across views

**Trigger**: When Canvas returns users without email addresses

**Workaround**: None - cosmetic issue only

**Fix approach**: Add fallback display when email is null/empty

## Security Considerations

### No API Rate Limiting for Authenticated Requests

**Issue**: Slowapi rate limiter is configured but may be too permissive for local deployment.

**Files**: `/Users/mapajr/git/cda-ta-dashboard/main.py` (lines 67-70)

**Impact**:
- Single-user local deployment has rate limiting that may be unnecessary
- In production (if deployed publicly), default limits may be insufficient

**Current mitigation**: Slowapi limiter is configured but limits not specified in code

**Recommendations**:
- Configure explicit rate limits if deploying to shared environment
- Consider disabling rate limiting for pure local single-user deployment
- Document rate limit values in environment variables

### CORS Configuration Overly Permissive

**Issue**: CORS allows all methods and headers from localhost origins.

**Files**: `/Users/mapajr/git/cda-ta-dashboard/main.py` (lines 72-88)

**Code**:
```python
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    # ... more localhost origins
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # All methods
    allow_headers=["*"],  # Any header
)
```

**Risk**: If deployed beyond localhost, overly permissive CORS could be exploited

**Current mitigation**: Deployment is documented as local-only

**Recommendations**:
- Restrict to production domains when not deploying locally
- Limit `allow_methods` to only those actually used
- Specify exact headers needed instead of wildcard

### SQLite Database Not Encrypted

**Issue**: SQLite database at `./data/canvas.db` stores student PII unencrypted.

**Files**: `/Users/mapajr/git/cda-ta-dashboard/database.py` (line 19)

**Risk**:
- Student names, emails, grades stored in plaintext
- Database file accessible to anyone with filesystem access
- Violates FERPA best practices for data at rest

**Current mitigation**:
- `.gitignore` prevents database from being committed
- Docker volumes are local-only by design
- Application documented for single-user local deployment

**Recommendations**:
- Add database encryption option for multi-user scenarios
- Document that database contains FERPA-protected data
- Consider SQLite encryption extensions for production deployments

### Canvas API Token Stored in Environment Variable

**Issue**: Canvas API token stored in `.env` file in plaintext.

**Files**: `/Users/mapajr/git/cda-ta-dashboard/.gitignore` (lines 142-146)

**Risk**:
- Token exposed if filesystem is compromised
- Token can be stolen from running process environment
- No token rotation mechanism

**Current mitigation**:
- `.env` is in `.gitignore`
- Documentation warns about security
- No tokens in committed files

**Recommendations**:
- Consider using OS keychain for token storage
- Add token expiration warnings to UI
- Document token rotation procedures

## Performance Bottlenecks

### N+1 Query Pattern in Late Days Calculation

**Issue**: Frontend calculates late days by iterating through all students and assignments nested loops.

**Files**: `/Users/mapajr/git/cda-ta-dashboard/canvas-react/src/LateDaysTracking.jsx` (lines 496-527)

**Impact**:
- For 100 students × 20 assignments = 2000 table cells rendered
- Each cell may trigger re-renders on state changes
- Sorting/filtering requires re-computing entire dataset

**Cause**:
- Computation happens in JavaScript on frontend
- No memoization at row level
- Table re-renders frequently

**Improvement path**:
- Implement virtual scrolling for large tables
- Add row-level memoization with React.memo
- Consider pagination for large student counts
- Move late days calculation to backend API

### Missing Database Indexes for Common Queries

**Issue**: Some frequently queried columns lack composite indexes.

**Files**: `/Users/mapajr/git/cda-ta-dashboard/database.py` (lines 60-132)

**Missing indexes**:
- No index on `submissions(course_id, assignment_id, user_id)` for late days queries
- No index on `peer_review_comments(course_id, submission_id, author_id)` for peer review queries

**Impact**:
- Queries joining submissions by course, assignment, and user may be slow
- Peer review comment lookups perform table scans

**Improvement path**:
- Add composite indexes for common query patterns
- Analyze query patterns with EXPLAIN QUERY PLAN
- Benchmark performance before/after index changes

### Canvas API Sequential Fetching

**Issue**: `canvas_sync.py` fetches data sequentially rather than in parallel where possible.

**Files**: `/Users/mapajr/git/cda-ta-dashboard/canvas_sync.py` (lines 114-236)

**Impact**:
- Sync time scales linearly with number of assignments
- Each assignment's submissions fetched one after another
- Large courses with many assignments take significant time

**Cause**:
- Loop structure processes assignments sequentially
- No parallel fetching for independent data

**Improvement path**:
- Use `asyncio.gather()` or ThreadPoolExecutor for parallel API calls
- Fetch multiple assignments' submissions concurrently
- Respect Canvas API rate limits with backoff

### Frontend Bundle Size Not Optimized

**Issue**: No evidence of code splitting or lazy loading in frontend.

**Files**: `/Users/mapajr/git/cda-ta-dashboard/canvas-react/src/` (all components)

**Impact**:
- Initial bundle loads all views even if user only visits one
- Slower initial page load
- Unnecessary code shipped to browser

**Improvement path**:
- Implement React.lazy() for route-based code splitting
- Use Suspense boundaries for loading states
- Analyze bundle size with vite build analyzer

## Fragile Areas

### Canvas API Data Structure Assumptions

**Issue**: Code assumes specific Canvas API data structures that may change.

**Files**:
- `/Users/mapajr/git/cda-ta-dashboard/canvas_sync.py` (lines 115-128, 136-143)
- `/Users/mapajr/git/cda-ta-dashboard/database.py` (lines 374-423)

**Impact**:
- API field changes break sync functionality
- Missing fields cause KeyError or attribute errors
- Hard to debug when Canvas updates their API

**Safe modification**:
- Add defensive `getattr()` calls with defaults
- Add schema validation for Canvas responses
- Monitor Canvas API changelog
- Write integration tests against Canvas API mock

### TA Group Name Hardcoding

**Issue**: Group filtering uses hardcoded string matching to exclude project groups.

**Files**:
- `/Users/mapajr/git/cda-ta-dashboard/canvas_sync.py` (line 154)
- `/Users/mapajr/git/cda-ta-dashboard/canvas-react/src/EnhancedTADashboard.jsx` (line 25)

**Code**:
```python
if "Term Project" in getattr(group, "name", ""):
    continue
```

**Why fragile**:
- Group naming conventions vary by institution
- Hardcoded "Term Project" may not match all cases
- Case-sensitive matching may miss variations

**Test coverage**: Unknown - no tests found for this logic

**Safe modification**:
- Add configurable group name patterns
- Support multiple exclusion patterns
- Make matching case-insensitive
- Document expected group naming convention

### Date Parsing Without Timezone Handling

**Issue**: Multiple locations parse dates without explicit timezone handling.

**Files**:
- `/Users/mapajr/git/cda-ta-dashboard/canvas-react/src/EnhancedTADashboard.jsx` (lines 96, 101, 134, 139)
- `/Users/mapajr/git/cda-ta-dashboard/canvas-react/src/LateDaysTracking.jsx` (lines 108, 331)
- `/Users/mapajr/git/cda-ta-dashboard/main.py` (lines 410-416, 748-749, 920-921)

**Impact**:
- Dates may display incorrectly depending on browser timezone
- Late day calculations may be wrong if due dates have timezone info
- Inconsistent date handling across components

**Safe modification**:
- Use a centralized date utility library
- Parse all dates with timezone awareness
- Store and display dates consistently in UTC
- Add tests for timezone edge cases

### Environment Variable Handling Inconsistency

**Issue**: Some environment variables have required field validation, others don't.

**Files**:
- `/Users/mapajr/git/cda-ta-dashboard/docker-compose.yml` (lines 10-11)
- `/Users/mapajr/git/cda-ta-dashboard/main.py` (lines 34-36)

**Impact**:
- Docker compose enforces CANVAS_API_URL and CANVAS_API_TOKEN
- Python code defaults to empty strings if missing
- Inconsistent startup behavior

**Safe modification**:
- Add pydantic-settings for all environment variables
- Fail fast on missing required configuration
- Document all environment variables with required/optional status

## Scaling Limits

### Single-User Design by Default

**Resource**: User authentication and session management

**Current capacity**: 1 user (no authentication system)

**Limit**:
- Cannot support multiple users simultaneously
- No role-based access control
- No audit trail of user actions

**Scaling path**:
- Add authentication system (OAuth, JWT, or Canvas SSO)
- Implement user roles (admin, TA, viewer)
- Add user-specific data isolation in database
- Add audit logging for compliance

### SQLite Concurrency Limitations

**Resource**: Database write operations during sync

**Current capacity**: Single write operation at a time (WAL mode enabled)

**Limit**:
- Multiple concurrent syncs would be serialized
- Database may become locked under heavy load
- No connection pooling

**Scaling path**:
- Add database migration path to PostgreSQL for multi-user scenarios
- Implement connection pooling
- Add read replicas for dashboard queries

### Canvas API Rate Limits

**Resource**: Canvas API calls

**Current capacity**: Dependent on Canvas instance limits (typically 1000 requests/hour)

**Limit**:
- Large courses with many assignments may hit rate limits
- No exponential backoff implemented
- Sync may fail silently on rate limit

**Scaling path**:
- Implement exponential backoff in canvas_sync.py
- Cache Canvas responses where appropriate
- Add progress indicators for long syncs
- Document expected sync times for course sizes

## Dependencies at Risk

### CanvasAPI Library Version Constraints

**Package**: canvasapi>=3.0.0

**Risk**:
- Canvas API changes may break compatibility
- Library may not stay updated with Canvas changes
- No pinned version means auto-upgrades could break things

**Impact**: Canvas API changes break sync functionality

**Migration plan**:
- Pin to specific patch version in pyproject.toml
- Monitor CanvasAPI changelog for breaking changes
- Add integration tests that mock Canvas API responses
- Consider alternative: direct Canvas API REST client

### React 19.1.1 Recent Release

**Package**: react@19.1.1

**Risk**:
- React 19 is very recent, may have undocumented bugs
- Some third-party libraries may not be fully compatible
- React 19 has breaking changes from 18

**Impact**: Potential rendering bugs, component lifecycle issues

**Migration plan**:
- Monitor React 19 issue tracker
- Ensure all React hooks usage follows 19 best practices
- Test thoroughly in multiple browsers
- Consider pinning to React 18.3 if issues arise

## Missing Critical Features

### No Data Export Functionality

**Problem**: No way to export student data, grades, or late days to CSV/Excel.

**Blocks**:
- TAs cannot generate reports
- Instructors cannot archive data
- No offline analysis capability

**Impact**: Limited utility for reporting and record-keeping

### No User Settings/Preferences

**Problem**: No user preferences stored (timezone, display settings, etc.).

**Blocks**:
- Users cannot customize their experience
- Timezone always hardcoded to EST
- No way to persist filter preferences

**Impact**: Reduced usability for non-Eastern timezone users

### No Notification System

**Problem**: No notifications for dropped students, late submissions, or sync failures.

**Blocks**:
- Proactive monitoring requires manual checking
- No alerts for urgent issues
- Silent failures possible

**Impact**: TAs must actively check dashboard for problems

## Test Coverage Gaps

### No Backend Integration Tests

**What's not tested**:
- Canvas API sync process end-to-end
- Database transaction rollbacks
- Canvas API error scenarios (rate limits, 500 errors)
- Enrollment tracking logic

**Files**: `/Users/mapajr/git/cda-ta-dashboard/` (no test/ directory)

**Risk**:
- Sync failures may not be caught until production
- Database migrations could break data
- Edge cases in Canvas API handling untested

**Priority**: High

### Limited Frontend Component Tests

**What's not tested**:
- EnrollmentTracking.jsx (has test file but unknown coverage)
- Integration flows between components
- API error handling scenarios
- Form validation logic

**Files**:
- `/Users/mapajr/git/cda-ta-dashboard/canvas-react/src/EnrollmentTracking.test.jsx` (exists, coverage unknown)
- `/Users/mapajr/git/cda-ta-dashboard/canvas-react/src/EnhancedTADashboard.test.jsx` (exists, minimal tests)
- `/Users/mapajr/git/cda-ta-dashboard/canvas-react/src/LateDaysTracking.test.jsx` (38 lines, likely minimal)

**Risk**:
- UI regressions may go undetected
- Bug fix typos (like "dropped" → "dropped") not caught by tests
- API error states not properly tested

**Priority**: High (especially after fixing enrollment tracking typo)

### No E2E Tests

**Framework**: Not used

**What's not tested**:
- Complete user flows (login → select course → view data)
- Docker deployment end-to-end
- Canvas sync triggers through UI

**Impact**:
- No confidence in complete workflows
- Integration issues discovered late in development cycle

**Priority**: Medium (local deployment tool, but workflows are user-facing)

---

*Concerns audit: 2026-02-15*
