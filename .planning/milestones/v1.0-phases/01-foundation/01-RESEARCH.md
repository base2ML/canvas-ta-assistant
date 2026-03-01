# Phase 1: Foundation - Research

**Researched:** 2026-02-15
**Domain:** Canvas API Comment Posting Infrastructure - Database schema, safety mechanisms, template storage
**Confidence:** HIGH

## Summary

Phase 1 establishes the foundational infrastructure required before any Canvas comment posting capability can be built safely. This includes database tables for storing comment templates and tracking posted comments (for duplicate prevention), template management functions with validation, safety mechanisms (test mode toggle, duplicate detection), and configuration settings. All requirements have been thoroughly researched using existing codebase patterns, Canvas API documentation, and SQLite best practices.

The research confirms that all Phase 1 requirements can be implemented using the existing technology stack (SQLite, FastAPI, Pydantic, canvasapi) without additional dependencies. The architecture follows established patterns in the codebase (database.py CRUD functions, settings table usage, context managers for transactions).

**Primary recommendation:** Implement database schema first (allows immediate testing), followed by CRUD functions and validation logic, then API endpoints and safety checks. Pre-populate default templates based on existing late day calculation logic already present in the codebase (main.py lines 702-803).

## Standard Stack

### Core (Already Present in Project)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLite | 3.x (Python built-in) | Template and history storage | Already used throughout project for Canvas data (assignments, submissions, users). No additional database needed. |
| Pydantic | 2.0.0+ | Request/response validation | Already integrated in FastAPI app. Used for validating template text, placeholders, settings updates. |
| FastAPI | 0.104.0+ | REST API endpoints | Already serving all backend endpoints. Will add template CRUD endpoints. |
| Python sqlite3 module | 3.11+ | Database operations | Already used via database.py context managers. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python `str.format()` | Built-in | Template variable substitution | For validating template placeholders during creation. Simple, no dependencies. |
| Python `string.Template` | Built-in | Safer template validation | Alternative to `str.format()` for validation - provides `is_valid()` method (Python 3.11+). |

**No additional dependencies required for Phase 1.**

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SQLite composite UNIQUE constraint | Application-level duplicate check | UNIQUE constraint is database-enforced (more reliable), application check is code-dependent. Always prefer database constraint. |
| Built-in `str.format()` | Jinja2 template engine | Jinja2 adds dependency, overkill for simple variable substitution. Only needed if templates require conditionals/loops (not in Phase 1). |
| Settings table for test mode | Environment variable only | Settings table allows runtime toggle from UI, environment variable requires restart. UI toggle is better UX. |

**Installation:**
```bash
# No additional packages needed - all requirements already in pyproject.toml
# Verify existing dependencies:
uv sync  # Ensures SQLite, Pydantic, FastAPI are available
```

## Architecture Patterns

### Recommended Project Structure

```
Backend (Python):
├── database.py                     # MODIFIED - Add new functions
│   ├── init_db()                  # MODIFIED - Add 2 new table schemas
│   │   ├── CREATE TABLE comment_templates
│   │   └── CREATE TABLE comment_posting_history
│   ├── Template CRUD functions    # NEW
│   │   ├── upsert_template()
│   │   ├── get_templates()
│   │   ├── get_template_by_id()
│   │   ├── delete_template()
│   │   └── populate_default_templates()
│   └── History recording          # NEW
│       ├── record_comment_posting()
│       └── get_posting_history()
│
├── main.py                        # MODIFIED - Add new endpoints
│   ├── Pydantic models           # NEW
│   │   ├── CommentTemplate
│   │   ├── CommentTemplateCreate
│   │   ├── CommentPostingHistory
│   │   └── SettingsUpdate (extend existing)
│   └── API endpoints             # NEW
│       ├── GET /api/templates
│       ├── POST /api/templates
│       ├── PUT /api/templates/{id}
│       ├── DELETE /api/templates/{id}
│       ├── GET /api/settings (MODIFIED - add test_mode, max_late_days)
│       └── PUT /api/settings (MODIFIED - validate new settings)
│
└── data/canvas.db                 # MODIFIED - New tables added
    ├── comment_templates          # NEW
    └── comment_posting_history    # NEW

Frontend (React):
├── Settings.jsx                   # MODIFIED in later phase
│   └── (Template management UI will be added in Phase 3)
│
└── (No frontend changes in Phase 1)
```

### Pattern 1: Database Schema with Composite UNIQUE Constraint

**What:** Use SQLite UNIQUE constraint on multiple columns to prevent duplicate comment postings at the database level.

**When to use:** For enforcing business rules that must never be violated (e.g., "never post the same template to the same student for the same assignment twice").

**Example:**
```sql
CREATE TABLE comment_posting_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL,
    assignment_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    template_id INTEGER,
    comment_text TEXT NOT NULL,
    canvas_comment_id INTEGER,
    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'posted',
    UNIQUE(course_id, assignment_id, user_id, template_id)
);
```

**Why composite UNIQUE constraint:**
- Database-enforced (cannot be bypassed by application bugs)
- Prevents race conditions (atomic check-and-insert)
- Allows re-posting with different template to same student/assignment
- NULL values in `template_id` are treated as distinct (allows manual comments)

**Sources:**
- [SQLite CREATE TABLE Documentation](https://www.sqlite.org/lang_createtable.html) - Official SQLite syntax
- [SQLite UNIQUE Constraint Tutorial](https://www.sqlitetutorial.net/sqlite-unique-constraint/) - Examples

### Pattern 2: Template Storage with Placeholder Metadata

**What:** Store both template text AND a JSON array of placeholder names for validation.

**When to use:** For templates that will be rendered with user data. Enables validation that all required placeholders are provided at render time.

**Example:**
```sql
CREATE TABLE comment_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_type TEXT NOT NULL,  -- 'penalty' or 'non_penalty'
    template_text TEXT NOT NULL,
    template_variables TEXT,      -- JSON: ["student_name", "late_days", "max_late_days"]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Python usage:**
```python
import json

# Store template
template_variables = ["student_name", "late_days", "max_late_days"]
db.upsert_template(
    template_type="penalty",
    template_text="Hi {student_name}, you used {late_days} late days (max: {max_late_days}).",
    template_variables=json.dumps(template_variables)
)

# Validate before rendering
template = db.get_template_by_id(template_id)
variables = json.loads(template["template_variables"])
required_keys = set(variables)
provided_keys = set(render_data.keys())
missing = required_keys - provided_keys
if missing:
    raise ValueError(f"Missing template variables: {missing}")
```

### Pattern 3: Settings Table for Configuration

**What:** Store test mode toggle and max late days setting in existing `settings` table.

**When to use:** For runtime-configurable settings that should persist across restarts and be changeable from UI.

**Example:**
```python
# In database.py (existing pattern)
def get_setting(key: str) -> str | None:
    """Get setting value by key."""
    # ... existing implementation ...

def set_setting(key: str, value: str) -> None:
    """Set setting value."""
    # ... existing implementation with UPSERT ...

# Settings keys (Phase 1):
# - "test_mode": "true" or "false"
# - "max_late_days_per_assignment": "7" (default)
# - "sandbox_course_id": "20960000000447574"

# Usage in safety check:
def is_test_mode() -> bool:
    return db.get_setting("test_mode") == "true"

def get_max_late_days() -> int:
    value = db.get_setting("max_late_days_per_assignment")
    return int(value) if value else 7
```

**Why settings table over environment variables:**
- Can be changed from Settings UI without restart
- Persists across deployments
- Follows existing pattern in codebase (see Settings.jsx lines 22-33)

### Pattern 4: Transaction-Based History Recording

**What:** Record comment posting in database transaction with error handling.

**When to use:** For audit trail and duplicate prevention. Ensures history is recorded atomically with posting attempt.

**Example:**
```python
from database import get_db_transaction

def post_comment_with_history(course_id, assignment_id, user_id, template_id, comment_text):
    """Post comment and record history in single transaction."""
    with get_db_transaction() as conn:
        cursor = conn.cursor()

        # Check for duplicate
        cursor.execute(
            """SELECT id FROM comment_posting_history
               WHERE course_id = ? AND assignment_id = ?
               AND user_id = ? AND template_id = ? AND status = 'posted'""",
            (course_id, assignment_id, user_id, template_id)
        )
        if cursor.fetchone():
            logger.info(f"Comment already posted to user {user_id}, skipping")
            return {"status": "skipped", "reason": "already_posted"}

        # Record as pending
        cursor.execute(
            """INSERT INTO comment_posting_history
               (course_id, assignment_id, user_id, template_id, comment_text, status)
               VALUES (?, ?, ?, ?, ?, 'pending')""",
            (course_id, assignment_id, user_id, template_id, comment_text)
        )
        history_id = cursor.lastrowid

        try:
            # Post to Canvas (Phase 2 will implement this)
            # canvas_comment_id = post_to_canvas(...)

            # Update as posted
            cursor.execute(
                """UPDATE comment_posting_history
                   SET status = 'posted', canvas_comment_id = ?
                   WHERE id = ?""",
                (None, history_id)  # canvas_comment_id placeholder
            )
            conn.commit()
            return {"status": "success", "history_id": history_id}

        except Exception as e:
            # Record failure
            cursor.execute(
                """UPDATE comment_posting_history
                   SET status = 'failed', error_message = ?
                   WHERE id = ?""",
                (str(e), history_id)
            )
            conn.commit()
            raise
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SQL injection prevention | String concatenation for queries | Parameterized queries (existing pattern) | SQL injection is trivial to prevent with `?` placeholders but easy to miss in string building. |
| Template variable validation | Regex to find `{variable}` patterns | Python `str.format()` with try/except OR `string.Template.is_valid()` | Python 3.11+ has built-in validation. Regex is fragile for edge cases (escaped braces, nested braces). |
| UNIQUE constraint enforcement | Application-level duplicate check before INSERT | SQLite UNIQUE constraint | Database constraints are atomic, application checks have race conditions. |
| Transaction management | Manual `conn.commit()` and `conn.rollback()` | Existing `get_db_transaction()` context manager | Already implemented in database.py (lines 37-45). Handles rollback automatically. |
| Settings validation | Custom validation functions | Pydantic models with validators | Pydantic provides declarative validation with clear error messages. |

**Key insight:** SQLite provides all necessary features (composite UNIQUE constraints, transactions, foreign keys) for this phase. No need for custom duplicate detection or validation logic beyond what's built-in.

## Common Pitfalls

### Pitfall 1: Missing Default Template Population

**What goes wrong:** Database tables are created but no default templates exist. User must manually create templates before any comment posting can work. Poor first-run experience.

**Why it happens:**
- Database migration creates empty `comment_templates` table
- No seed data or initial population logic
- Assumption that user will create templates via UI

**How to avoid:**
1. Create `populate_default_templates()` function in database.py
2. Call during `init_db()` only if `comment_templates` table is empty
3. Base default templates on existing late day logic in main.py (lines 702-803)
4. Use existing late day calculation patterns as template content source

**Example:**
```python
def populate_default_templates() -> None:
    """Populate default comment templates if table is empty."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM comment_templates")
        if cursor.fetchone()[0] > 0:
            return  # Templates already exist

        default_templates = [
            {
                "template_type": "penalty",
                "template_text": "You used {late_days} late day(s) on this assignment. Total late days used: {total_late_days}. Maximum allowed per assignment: {max_late_days}.",
                "template_variables": json.dumps(["late_days", "total_late_days", "max_late_days"])
            },
            {
                "template_type": "non_penalty",
                "template_text": "Your submission was received {late_days} day(s) late. This is noted for record-keeping purposes.",
                "template_variables": json.dumps(["late_days"])
            }
        ]

        for template in default_templates:
            cursor.execute(
                """INSERT INTO comment_templates
                   (template_type, template_text, template_variables)
                   VALUES (?, ?, ?)""",
                (template["template_type"], template["template_text"], template["template_variables"])
            )
        conn.commit()
        logger.info(f"Populated {len(default_templates)} default templates")
```

**Warning signs:**
- No data seeding logic in database.py
- Empty templates table after init
- UI requires manual template creation before use

### Pitfall 2: Unclosed Brace in Template Text

**What goes wrong:** User creates template with unclosed brace (e.g., "You have {late_days late days"). When rendered, Python's `str.format()` raises `ValueError: Single '{' encountered in format string`. Application crashes or posts malformed comment.

**Why it happens:**
- No validation when template is created
- User typo (missing closing `}`)
- Copy-paste error from external source
- Template saved to database without testing

**How to avoid:**
1. **Validate template syntax before saving:** Use `str.format()` test render with dummy data
2. **Provide clear error message:** "Template has unclosed braces at position X"
3. **Frontend preview:** Show rendered template with sample data before saving (Phase 3)

**Validation code:**
```python
def validate_template_syntax(template_text: str, variables: list[str]) -> tuple[bool, str]:
    """
    Validate template syntax by test-rendering with dummy data.

    Returns:
        (is_valid, error_message)
    """
    # Create dummy data for all variables
    dummy_data = {var: f"[{var}]" for var in variables}

    try:
        # Attempt to render
        rendered = template_text.format(**dummy_data)

        # Check for unreplaced braces (shouldn't happen if format() succeeded)
        if '{' in rendered or '}' in rendered:
            # Could be escaped braces ({{, }}) which is valid
            # Only error if unescaped
            import re
            unescaped_braces = re.search(r'(?<!{){(?!{)|(?<!})}(?!})', rendered)
            if unescaped_braces:
                return False, f"Template has unmatched braces: {unescaped_braces.group()}"

        return True, ""

    except KeyError as e:
        return False, f"Template references undefined variable: {e}"
    except ValueError as e:
        # Unclosed brace, invalid format
        return False, f"Invalid template syntax: {e}"
    except Exception as e:
        return False, f"Template validation error: {e}"

# Usage in API endpoint:
@app.post("/api/templates")
async def create_template(template: CommentTemplateCreate) -> dict:
    variables = json.loads(template.template_variables)
    is_valid, error = validate_template_syntax(template.template_text, variables)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )

    # Save to database...
```

**Alternative approach (Python 3.11+):**
```python
from string import Template

def validate_with_string_template(template_text: str) -> tuple[bool, str]:
    """Use string.Template for safer validation (Python 3.11+)."""
    try:
        t = Template(template_text)
        if not t.is_valid():  # Python 3.11+
            return False, "Template contains invalid placeholders"
        return True, ""
    except Exception as e:
        return False, f"Template validation error: {e}"
```

**Sources:**
- [Python String Formatting Guide](https://docs.python.org/3/library/string.html) - Official documentation
- [Python Template Validation](https://devtoolbox.dedyn.io/blog/python-string-formatting-complete-guide) - String validation patterns

**Warning signs:**
- No template validation before database insert
- Templates saved directly from user input without testing
- No error handling for `str.format()` in render code

### Pitfall 3: Settings Validation Missing Constraints

**What goes wrong:** User sets `max_late_days_per_assignment` to negative number or invalid value (e.g., "abc"). Application crashes when calculating late days or behaves unexpectedly.

**Why it happens:**
- Settings endpoint accepts any string value
- No validation in PUT /api/settings handler
- Settings table stores TEXT, no type checking
- Frontend doesn't validate before sending

**How to avoid:**
1. **Use Pydantic validators:** Define allowed value ranges
2. **Backend validation:** Check constraints before database update
3. **Return clear error:** "max_late_days must be positive integer"

**Pydantic model with validation:**
```python
from pydantic import BaseModel, field_validator, Field

class SettingsUpdate(BaseModel):
    course_id: str | None = None
    test_mode: bool | None = None
    max_late_days_per_assignment: int | None = Field(None, ge=0, le=365)  # 0-365 days
    sandbox_course_id: str | None = None

    @field_validator("max_late_days_per_assignment")
    @classmethod
    def validate_max_late_days(cls, v):
        if v is not None and v < 0:
            raise ValueError("max_late_days must be non-negative")
        if v is not None and v > 365:
            raise ValueError("max_late_days cannot exceed 365 days")
        return v

    @field_validator("test_mode")
    @classmethod
    def validate_test_mode(cls, v):
        # Pydantic automatically validates bool, but explicit check for clarity
        if v is not None and not isinstance(v, bool):
            raise ValueError("test_mode must be true or false")
        return v

# API endpoint:
@app.put("/api/settings")
async def update_settings(settings: SettingsUpdate) -> dict:
    # Pydantic validation happens automatically
    # If validation fails, FastAPI returns 422 with error details

    if settings.max_late_days_per_assignment is not None:
        db.set_setting("max_late_days_per_assignment", str(settings.max_late_days_per_assignment))

    if settings.test_mode is not None:
        db.set_setting("test_mode", "true" if settings.test_mode else "false")

    # ... other settings ...

    return {"status": "success", "message": "Settings updated"}
```

**Warning signs:**
- Settings endpoint accepts raw strings without validation
- No Pydantic model for settings update
- Settings stored without type checking
- No constraints on numeric settings

### Pitfall 4: Test Mode Bypass

**What goes wrong:** User enables test mode in Settings, but posting logic doesn't check test mode flag. Comments are posted to production course despite test mode being enabled. Safety mechanism fails.

**Why it happens:**
- Test mode flag stored but not checked before posting
- Posting function doesn't query settings
- Race condition (settings changed after posting started)
- Test mode check implemented but with logic error

**How to avoid:**
1. **Mandatory test mode check:** Every posting function MUST check test mode
2. **Sandbox course validation:** If test mode enabled, course_id MUST match sandbox
3. **Dual enforcement:** Check both test_mode flag AND course_id whitelist
4. **Log test mode status:** Every posting attempt logs test mode state

**Safety check pattern:**
```python
SANDBOX_COURSE_ID = "20960000000447574"  # From requirements

def validate_posting_safety(course_id: str) -> tuple[bool, str]:
    """
    Validate that posting is safe based on test mode and course ID.

    Returns:
        (is_safe, error_message)
    """
    test_mode = db.get_setting("test_mode") == "true"

    if test_mode:
        # In test mode, ONLY allow sandbox course
        if course_id != SANDBOX_COURSE_ID:
            return False, f"Test mode enabled but course_id {course_id} is not sandbox course {SANDBOX_COURSE_ID}"
        logger.info(f"Test mode: Posting to sandbox course {course_id}")
        return True, ""
    else:
        # Production mode - warn if posting to sandbox
        if course_id == SANDBOX_COURSE_ID:
            logger.warning(f"Production mode but posting to sandbox course {course_id}")
        # Allow any course in production mode (user's responsibility)
        return True, ""

# Usage in posting endpoint (Phase 2):
@app.post("/api/comments")
async def post_comments(request: CommentPostingRequest) -> dict:
    # Validate safety BEFORE any posting
    is_safe, error = validate_posting_safety(request.course_id)
    if not is_safe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error
        )

    # Proceed with posting...
```

**Warning signs:**
- Test mode setting exists but no usage in code
- No validation of course_id against test mode
- Posting functions don't check settings
- No logging of test mode status during posting

### Pitfall 5: Missing Database Indices on History Table

**What goes wrong:** Querying posting history by course/assignment is slow (>1 second for 1000+ records). UI becomes unresponsive when loading history. History table scans entire table for every query.

**Why it happens:**
- History table created without indices
- Queries filter by course_id and assignment_id (not indexed)
- As history grows, queries get slower
- No composite index for common query pattern

**How to avoid:**
1. **Add indices during table creation:** Index columns used in WHERE clauses
2. **Composite index for common queries:** `(course_id, assignment_id)`
3. **Follow existing pattern:** Other tables in codebase have indices (see database.py lines 74-76, 100-105)

**Correct schema with indices:**
```sql
CREATE TABLE comment_posting_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL,
    assignment_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    template_id INTEGER,
    comment_text TEXT NOT NULL,
    canvas_comment_id INTEGER,
    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'posted',
    error_message TEXT,
    UNIQUE(course_id, assignment_id, user_id, template_id)
);

-- Indices for common query patterns:
CREATE INDEX idx_posting_history_course_assignment
    ON comment_posting_history(course_id, assignment_id);

CREATE INDEX idx_posting_history_user
    ON comment_posting_history(user_id);

CREATE INDEX idx_posting_history_status
    ON comment_posting_history(status);  -- For querying failed posts

CREATE INDEX idx_posting_history_posted_at
    ON comment_posting_history(posted_at DESC);  -- For recent history
```

**Warning signs:**
- Table created without CREATE INDEX statements
- Queries taking >100ms on small datasets
- No EXPLAIN QUERY PLAN testing during development
- Copy-paste table schema without indices

## Code Examples

Verified patterns from official sources and existing codebase:

### Database Schema Definition (from init_db pattern)

```python
# In database.py, add to init_db() function:

def init_db() -> None:
    """Initialize database with schema."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # ... existing tables (settings, assignments, users, etc.) ...

        # Comment templates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comment_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_type TEXT NOT NULL,
                template_text TEXT NOT NULL,
                template_variables TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_comment_templates_type ON comment_templates(template_type)"
        )

        # Comment posting history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comment_posting_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id TEXT NOT NULL,
                assignment_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                template_id INTEGER,
                comment_text TEXT NOT NULL,
                canvas_comment_id INTEGER,
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'posted',
                error_message TEXT,
                UNIQUE(course_id, assignment_id, user_id, template_id)
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_posting_history_course_assignment ON comment_posting_history(course_id, assignment_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_posting_history_user ON comment_posting_history(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_posting_history_status ON comment_posting_history(status)"
        )

        conn.commit()
        logger.info(f"Database initialized at {DB_PATH}")

        # Populate default templates if table is empty
        populate_default_templates()
```

**Source:** Existing pattern in database.py (lines 48-267)

### Template CRUD Functions

```python
# In database.py

def upsert_template(
    template_type: str,
    template_text: str,
    template_variables: str | None = None,
    template_id: int | None = None,
    conn: sqlite3.Connection | None = None
) -> int:
    """Insert or update a comment template."""

    def _upsert(db_conn: sqlite3.Connection) -> int:
        cursor = db_conn.cursor()
        updated_at = datetime.now(UTC)

        if template_id:
            # Update existing template
            cursor.execute(
                """UPDATE comment_templates
                   SET template_type = ?, template_text = ?,
                       template_variables = ?, updated_at = ?
                   WHERE id = ?""",
                (template_type, template_text, template_variables, updated_at, template_id)
            )
            if conn is None:
                db_conn.commit()
            return template_id
        else:
            # Insert new template
            cursor.execute(
                """INSERT INTO comment_templates
                   (template_type, template_text, template_variables, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (template_type, template_text, template_variables, updated_at, updated_at)
            )
            if conn is None:
                db_conn.commit()
            return cursor.lastrowid

    if conn is not None:
        return _upsert(conn)
    else:
        with get_db_connection() as db_conn:
            return _upsert(db_conn)


def get_templates(template_type: str | None = None) -> list[dict[str, Any]]:
    """Get all comment templates, optionally filtered by type."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if template_type:
            cursor.execute(
                """SELECT id, template_type, template_text, template_variables,
                          created_at, updated_at
                   FROM comment_templates WHERE template_type = ?
                   ORDER BY created_at DESC""",
                (template_type,)
            )
        else:
            cursor.execute(
                """SELECT id, template_type, template_text, template_variables,
                          created_at, updated_at
                   FROM comment_templates
                   ORDER BY template_type, created_at DESC"""
            )

        return [dict(row) for row in cursor.fetchall()]


def get_template_by_id(template_id: int) -> dict[str, Any] | None:
    """Get a specific template by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, template_type, template_text, template_variables,
                      created_at, updated_at
               FROM comment_templates WHERE id = ?""",
            (template_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def delete_template(template_id: int) -> bool:
    """Delete a template by ID. Returns True if deleted, False if not found."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM comment_templates WHERE id = ?", (template_id,))
        conn.commit()
        return cursor.rowcount > 0
```

**Source:** Pattern from existing CRUD functions in database.py (upsert_assignments lines 373-422, get_assignments lines 591-603)

### History Recording Function

```python
# In database.py

def record_comment_posting(
    course_id: str,
    assignment_id: int,
    user_id: int,
    template_id: int | None,
    comment_text: str,
    status: str = 'posted',
    canvas_comment_id: int | None = None,
    error_message: str | None = None,
    conn: sqlite3.Connection | None = None
) -> int:
    """
    Record a comment posting attempt in history.

    Uses UNIQUE constraint to prevent duplicates. If duplicate, updates existing record.

    Args:
        status: 'posted', 'failed', or 'dry_run'

    Returns:
        History record ID
    """

    def _record(db_conn: sqlite3.Connection) -> int:
        cursor = db_conn.cursor()

        cursor.execute(
            """INSERT INTO comment_posting_history
               (course_id, assignment_id, user_id, template_id, comment_text,
                canvas_comment_id, status, error_message, posted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(course_id, assignment_id, user_id, template_id)
               DO UPDATE SET
                   comment_text = excluded.comment_text,
                   canvas_comment_id = excluded.canvas_comment_id,
                   status = excluded.status,
                   error_message = excluded.error_message,
                   posted_at = excluded.posted_at""",
            (course_id, assignment_id, user_id, template_id, comment_text,
             canvas_comment_id, status, error_message, datetime.now(UTC))
        )

        if conn is None:
            db_conn.commit()

        return cursor.lastrowid

    if conn is not None:
        return _record(conn)
    else:
        with get_db_connection() as db_conn:
            return _record(db_conn)


def get_posting_history(
    course_id: str,
    assignment_id: int | None = None,
    status: str | None = None,
    limit: int = 100
) -> list[dict[str, Any]]:
    """Get comment posting history with optional filters."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        query = """
            SELECT id, course_id, assignment_id, user_id, template_id,
                   comment_text, canvas_comment_id, posted_at, status, error_message
            FROM comment_posting_history
            WHERE course_id = ?
        """
        params: list[Any] = [course_id]

        if assignment_id is not None:
            query += " AND assignment_id = ?"
            params.append(assignment_id)

        if status is not None:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY posted_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
```

**Source:** Pattern from existing history functions (create_sync_record lines 707-719, get_sync_history lines 784-809)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Regex for template validation | `string.Template.is_valid()` | Python 3.11 (2022) | Built-in validation method, no regex needed. Use if targeting Python 3.11+. |
| Manual UNIQUE constraint checking | Database-level UNIQUE constraint with ON CONFLICT | SQLite 3.24.0 (2018) | UPSERT pattern prevents race conditions, atomic duplicate detection. |
| JSON storage as TEXT | SQLite JSON1 extension | SQLite 3.38.0 (2022) | Can query JSON fields directly, but TEXT is sufficient for template_variables (simple arrays). |
| Separate test/prod databases | Runtime configuration toggle | N/A | Settings table approach allows single database with test mode flag. |

**Deprecated/outdated:**
- **Manual transaction management:** Replaced by context managers (`get_db_transaction()`)
- **String concatenation for SQL:** Always use parameterized queries (`?` placeholders)
- **Regex for brace matching:** Use `str.format()` test render or `string.Template.is_valid()` (Python 3.11+)

## Open Questions

1. **Default template content - what messaging do students expect?**
   - What we know: Requirements specify "penalty" and "non-penalty" message types based on existing notebook logic
   - What's unclear: Exact wording that balances professionalism with clarity
   - Recommendation: Start with simple factual messages ("You used X late days"), iterate based on TA/instructor feedback

2. **Template variable naming - camelCase or snake_case?**
   - What we know: Existing code uses snake_case for Python (PEP 8 convention)
   - What's unclear: Whether template placeholders should match Python convention or be more user-friendly
   - Recommendation: Use snake_case for consistency (`{student_name}`, `{late_days}`) - matches existing codebase patterns

3. **History retention - how long to keep posting records?**
   - What we know: FERPA requires educational records to be retained per institutional policy
   - What's unclear: Whether posting history counts as educational record or audit log
   - Recommendation: Keep indefinitely (SQLite is small), add future cleanup feature if database grows too large (>100MB)

## Sources

### Primary (HIGH confidence)

**Canvas API:**
- [Canvas Submissions API](https://www.canvas.instructure.com/doc/api/submissions.html) - Comment posting endpoint
- [Canvas Submission Comments API](https://canvas.instructure.com/doc/api/submission_comments.html) - Comment management

**SQLite:**
- [SQLite CREATE TABLE Documentation](https://www.sqlite.org/lang_createtable.html) - UNIQUE constraint syntax
- [SQLite UNIQUE Constraint Tutorial](https://www.sqlitetutorial.net/sqlite-unique-constraint/) - Composite keys

**Python Standard Library:**
- [Python String Module](https://docs.python.org/3/library/string.html) - Template validation (updated 2026-02-14)
- [Python String Formatting Guide](https://devtoolbox.dedyn.io/blog/python-string-formatting-complete-guide) - Validation patterns

**Existing Codebase:**
- `/Users/mapajr/git/cda-ta-dashboard/database.py` - Database patterns, CRUD functions, context managers
- `/Users/mapajr/git/cda-ta-dashboard/main.py` - FastAPI patterns, Pydantic models, settings endpoints
- `/Users/mapajr/git/cda-ta-dashboard/canvas-react/src/Settings.jsx` - Settings UI patterns

### Secondary (MEDIUM confidence)

**Prior Research:**
- `.planning/research/STACK.md` - Stack research for comment posting (researched 2026-02-15)
- `.planning/research/ARCHITECTURE.md` - Architecture patterns (researched 2026-02-15)
- `.planning/research/PITFALLS.md` - Pitfall analysis (researched 2026-02-15)

**Community Resources:**
- [Canvas LMS Community](https://community.canvaslms.com) - Best practices and common patterns
- [SQLite Tutorial](https://www.sqlitetutorial.net) - SQLite patterns and examples

## Metadata

**Confidence breakdown:**
- Database schema design: HIGH - Based on existing patterns in database.py, SQLite documentation
- Template CRUD functions: HIGH - Following existing CRUD patterns (upsert_assignments, get_templates)
- Settings validation: HIGH - Pydantic validation is standard pattern in FastAPI
- Default template content: MEDIUM - Requires TA/instructor input for messaging tone
- Safety mechanisms: HIGH - Test mode toggle and course ID validation are proven patterns

**Research date:** 2026-02-15
**Valid until:** 90 days (stable technologies - SQLite, Python stdlib, FastAPI patterns)

---

*Research complete. Ready for planning phase.*
