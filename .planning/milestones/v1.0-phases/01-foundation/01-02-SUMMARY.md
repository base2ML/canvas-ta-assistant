---
phase: 01-foundation
plan: 02
subsystem: api
tags: [templates, settings, validation, safety]
dependency_graph:
  requires:
    - 01-01-PLAN (database schema for templates and settings)
  provides:
    - Template CRUD API endpoints
    - Template syntax validation
    - Extended settings API (test mode, max late days)
    - Posting safety validation function
  affects:
    - Phase 02 posting endpoints (will use validate_posting_safety)
    - Frontend Settings UI (will consume extended settings)
    - Frontend template management (will consume template API)
tech_stack:
  added:
    - Pydantic field validators for settings and template validation
  patterns:
    - Template syntax validation via test-rendering with dummy data
    - Partial update pattern for settings (optional fields)
    - Safety gate pattern (validate_posting_safety for Phase 2)
key_files:
  created: []
  modified:
    - path: main.py
      changes:
        - Added Pydantic models for template CRUD (CommentTemplateCreate, CommentTemplateUpdate, CommentTemplateResponse)
        - Added validate_template_syntax function with unknown variable and syntax checking
        - Added 4 template CRUD endpoints (GET, POST, PUT, DELETE)
        - Extended SettingsResponse and SettingsUpdateRequest models
        - Added validate_posting_safety function for Phase 2
        - Added SANDBOX_COURSE_ID constant
decisions:
  - context: Template validation approach
    decision: Test-render templates with dummy data to catch syntax errors
    rationale: Python's str.format() naturally catches unclosed braces and undefined variables, simpler than regex parsing
    alternatives:
      - Regex-based validation (brittle, hard to maintain)
      - AST parsing (overkill for simple string templates)
  - context: Settings update pattern
    decision: Allow partial updates with optional fields
    rationale: Frontend can update one setting at a time without sending entire settings object
    alternatives:
      - Require full settings object (forces frontend to read-modify-write)
      - Separate endpoints per setting (more endpoints to maintain)
  - context: Posting safety validation
    decision: Separate validate_posting_safety function (not middleware)
    rationale: Posting endpoints will explicitly call validation for clear control flow
    alternatives:
      - Middleware (implicit, harder to test and debug)
      - Decorator (less flexible for conditional application)
metrics:
  duration_minutes: 4
  tasks_completed: 2
  files_modified: 1
  api_endpoints_added: 4
  validation_functions_added: 2
  completed_at: "2026-02-15T19:13:31Z"
---

# Phase 01 Plan 02: Template CRUD & Settings Extensions Summary

**One-liner:** REST API for template management with syntax validation and extended settings (test mode, max late days, posting safety)

## What Was Built

### Template CRUD API
- **GET /api/templates** - List all templates (with optional type filter), parses JSON variables to arrays
- **POST /api/templates** - Create template with syntax validation (rejects unknown vars, unclosed braces)
- **PUT /api/templates/{id}** - Update template with merge logic and validation
- **DELETE /api/templates/{id}** - Remove template (returns 404 if not found)

### Template Validation
- **validate_template_syntax()** - Test-renders templates with dummy data to catch:
  - Unknown variables (not in ALLOWED_TEMPLATE_VARIABLES)
  - Unclosed or unmatched braces
  - KeyError, ValueError, or other format errors
- Returns `(is_valid, error_message)` tuple

### Extended Settings API
- **GET /api/settings** - Now includes:
  - `test_mode` (bool, default false)
  - `max_late_days_per_assignment` (int, default 7)
  - `sandbox_course_id` (string constant)
- **PUT /api/settings** - Accepts partial updates:
  - `course_id` (optional)
  - `test_mode` (optional bool)
  - `max_late_days_per_assignment` (optional int, validated 0-365)
  - Rejects empty updates with 400
  - Returns list of updated_fields

### Posting Safety (for Phase 2)
- **validate_posting_safety()** - Validates posting is safe:
  - In test mode: blocks non-sandbox courses
  - Logs warnings for sandbox usage in production mode
  - Returns `(is_safe, reason)` tuple
  - Phase 2 posting endpoints will call this before Canvas API calls

## Deviations from Plan

None - plan executed exactly as written.

## Technical Implementation

### Validation Approach
Templates are validated by test-rendering with dummy data for all allowed variables:
```python
dummy_data = {var: f"[{var}]" for var in ALLOWED_TEMPLATE_VARIABLES}
template_text.format(**dummy_data)  # Raises ValueError for syntax errors
```

This approach naturally catches:
- Unclosed braces: `"Bad {days_late"` → ValueError
- Unknown variables: Pre-checked against ALLOWED_TEMPLATE_VARIABLES set
- Undefined variables: `"{missing}"` → KeyError

### Partial Updates Pattern
Settings now support partial updates via optional fields:
```python
class SettingsUpdateRequest(BaseModel):
    course_id: str | None = None
    test_mode: bool | None = None
    max_late_days_per_assignment: int | None = None
```

Endpoint logic checks `if field is not None` before updating, enabling:
- Update only test_mode: `{"test_mode": true}`
- Update only max_late_days: `{"max_late_days_per_assignment": 5}`
- Update multiple fields: `{"test_mode": false, "max_late_days_per_assignment": 7}`

### Safety Gate Pattern
`validate_posting_safety()` implements defense-in-depth for posting:
- **SAFE-01**: Test mode toggle stored in settings
- **SAFE-02**: Course ID validation before posting
- **CONF-02**: Test mode defaults to false in database

Phase 2 posting endpoints will call this function before any Canvas API calls.

## Testing Results

### Task 1: Template CRUD
- GET /api/templates returned 2 default templates with parsed variables ✓
- POST created template with valid syntax ✓
- POST rejected unknown variable `unknown_var` with clear error ✓
- POST rejected unclosed brace `{days_late` with syntax error ✓
- PUT updated template and merged with existing values ✓
- DELETE removed template ✓
- DELETE non-existent returned 404 ✓

### Task 2: Settings Extensions
- GET returned test_mode=false, max_late_days=7, sandbox_course_id ✓
- PUT enabled test_mode (partial update) ✓
- Settings persisted across requests ✓
- PUT updated max_late_days ✓
- Validation rejected negative max_late_days with 422 ✓
- Validation rejected max_late_days > 365 with 422 ✓
- Backward compatibility: course_id still works ✓
- Empty update rejected with 400 ✓

### Linting
- `uv run ruff check main.py` passed ✓
- Pre-commit hooks passed ✓

## Integration Points

### Database Layer (database.py)
- Uses existing `get_templates()`, `create_template()`, `update_template()`, `delete_template()`
- Uses existing `get_setting()`, `set_setting()` for test_mode and max_late_days
- Default templates populated by `init_db()` → `populate_default_templates()`

### Frontend (Future)
- Settings.jsx will read and update test_mode, max_late_days_per_assignment
- Template management UI will consume GET/POST/PUT/DELETE /api/templates
- Posting UI will be blocked by safety validation when test mode enabled

### Phase 2 (Posting Endpoints)
- POST /api/comments/post will call `validate_posting_safety()` before Canvas API calls
- Posting history endpoints will reference template_id from templates table
- Template rendering will use max_late_days_per_assignment from settings

## Key Files Modified

**main.py** (+283 lines, -7 lines):
- Added Pydantic models: CommentTemplateCreate, CommentTemplateUpdate, CommentTemplateResponse
- Added SettingsUpdateRequest with @field_validator for max_late_days
- Added validate_template_syntax() function
- Added validate_posting_safety() function
- Added 4 template CRUD endpoints
- Extended GET /api/settings to return test_mode, max_late_days, sandbox_course_id
- Extended PUT /api/settings to support partial updates with validation
- Added SANDBOX_COURSE_ID constant

## Verification

### Must-Haves Met
- [x] GET /api/templates returns list of all templates
- [x] POST /api/templates creates template after validating syntax
- [x] PUT /api/templates/{id} updates template after validating syntax
- [x] DELETE /api/templates/{id} removes template
- [x] Template validation rejects unclosed braces and unknown variables
- [x] GET /api/settings returns test_mode and max_late_days fields
- [x] PUT /api/settings accepts test_mode (bool) and max_late_days_per_assignment (int, 0-365)
- [x] Settings validation rejects negative max_late_days and non-boolean test_mode
- [x] Test mode defaults to false, max_late_days defaults to 7

### Success Criteria Met
- [x] GET /api/templates returns default templates with parsed template_variables arrays
- [x] POST /api/templates validates syntax before creating (rejects bad templates with clear error)
- [x] PUT /api/templates/{id} merges updates and validates, returns 404 for missing
- [x] DELETE /api/templates/{id} removes template, returns 404 for missing
- [x] GET /api/settings includes test_mode=false, max_late_days_per_assignment=7, sandbox_course_id
- [x] PUT /api/settings validates: max_late_days 0-365, test_mode is boolean, rejects empty updates
- [x] validate_posting_safety function available for Phase 2 (blocks non-sandbox in test mode)
- [x] All linting passes

## Self-Check

### Files Created/Modified
```bash
[ -f "/Users/mapajr/git/cda-ta-dashboard/main.py" ] && echo "FOUND: main.py" || echo "MISSING: main.py"
```
**Result:** FOUND: main.py

### Commits Exist
```bash
git log --oneline --all | grep -q "926828e" && echo "FOUND: 926828e (Task 1)" || echo "MISSING: 926828e"
git log --oneline --all | grep -q "797beba" && echo "FOUND: 797beba (Task 2)" || echo "MISSING: 797beba"
```
**Result:**
- FOUND: 926828e (Task 1)
- FOUND: 797beba (Task 2)

## Self-Check: PASSED

All files modified, all commits exist, all endpoints verified, all must-haves met.

## Next Steps

Phase 01 Plan 02 is complete. Ready to proceed to Phase 02 (Late Day Posting UI & API).

The foundation is now in place:
- Template CRUD API ready for frontend consumption
- Settings API extended for test mode and max late days configuration
- Posting safety validation ready for Phase 2 posting endpoints
- Database schema from Plan 01 fully exposed via REST API
