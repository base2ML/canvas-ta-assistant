# Stack Research: Canvas API Comment Posting Feature

**Domain:** Canvas LMS Late Day Feedback Automation
**Researched:** 2026-02-15
**Confidence:** HIGH

## Recommended Stack

### Core Technologies (Already Present)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| canvasapi | 3.0.0+ | Canvas API Python wrapper | Already integrated in existing system. Provides high-level Python interface to Canvas REST API. Officially maintained by UCF Open. |
| FastAPI | 0.104.0+ | Backend REST API framework | Already integrated. Provides async support for bulk operations and built-in Pydantic validation. |
| SQLite | 3.x | Local data persistence | Already integrated. Sufficient for comment posting history tracking without additional dependencies. |
| Pydantic | 2.0.0+ | Data validation & schemas | Already integrated. Ideal for validating comment templates and API request/response models. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **Built-in `str.format()`** | Python 3.11+ | Simple variable substitution in comment templates | For basic templates with {variable_name} placeholders. No additional dependencies. **RECOMMENDED** |
| Jinja2 | 3.1+ (optional) | Advanced template rendering with logic | Only if templates need conditional logic, loops, or filters. **NOT NEEDED for initial implementation** |
| python-dateutil | 2.8.0+ | Date parsing for late day calculations | Already integrated. Used for calculating late days from submission timestamps. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest | Testing comment posting workflow | Already configured. Use for integration tests with sandbox course. |
| loguru | Structured logging | Already integrated. Critical for tracking comment posting operations and errors. |

## Canvas API Comment Posting

### Canvas REST API Endpoint

**Confidence:** HIGH (verified via Canvas official documentation)

**Endpoint:** `PUT /api/v1/courses/:course_id/assignments/:assignment_id/submissions/:user_id`

**Parameters for posting comments:**
```python
{
    'comment': {
        'text_comment': 'Your comment text here',  # Required
        'group_comment': False,                     # Optional: post to all group members
        'attempt': 1                                # Optional: associate with specific attempt
    }
}
```

**Source:** [Canvas Submissions API](https://canvas.instructure.com/doc/api/submissions.html)

### canvasapi Library Usage

**Confidence:** HIGH (verified via canvasapi documentation and community examples)

**Method:** `submission.edit(comment={'text_comment': 'message'})`

**Example:**
```python
from canvasapi import Canvas

# Get submission object
canvas = Canvas(api_url, api_token)
course = canvas.get_course(course_id)
assignment = course.get_assignment(assignment_id)
submission = assignment.get_submission(user_id)

# Post comment
submission.edit(comment={
    'text_comment': 'You have used 3 late days on this assignment.'
})
```

**Key Points:**
- Comments are posted synchronously (blocking operation)
- Returns updated Submission object on success
- Raises `CanvasException` on API errors (401, 403, 404, 429, etc.)

**Sources:**
- [canvasapi Submission Reference](https://canvasapi.readthedocs.io/en/stable/submission-ref.html)
- [Canvas Community: Add comments via Python API](https://community.canvaslms.com/t5/Canvas-Developers-Group/Add-comments-text-via-Python-API/m-p/133923)

## Rate Limiting Strategy

### Canvas API Rate Limits

**Confidence:** HIGH (verified via Canvas official throttling documentation)

**Rate Limiting Mechanism:**
- Canvas uses dynamic throttling based on CPU + DB time cost
- Cost calculated as: `CPU time (seconds) + Database time (seconds)`
- Each request returns `X-Request-Cost` header (floating-point cost)
- When throttled, API returns `429 Forbidden (Rate Limit Exceeded)`
- Quota automatically replenishes over time

**Key Headers:**
- `X-Request-Cost`: Cost of current request
- `X-Rate-Limit-Remaining`: Remaining quota (when throttling active)

**Critical Finding:** "Any API client that makes no more than one simultaneous request is unlikely to be throttled."

**Source:** [Canvas Throttling Documentation](https://canvas.instructure.com/doc/api/file.throttling.html)

### Recommended Rate Limiting Approach

**Confidence:** HIGH

**Strategy:** Sequential processing with exponential backoff on 429 errors

**Why Sequential:**
1. Sequential requests avoid pre-flight penalties for parallel requests
2. Bucket "leaks" faster than sequential requests can fill it
3. No rate limiting expected for single-threaded operation
4. Simplest implementation with lowest error rate

**Implementation Pattern:**
```python
import time
from canvasapi.exceptions import CanvasException

def post_comment_with_retry(submission, comment_text, max_retries=3):
    """Post comment with exponential backoff on rate limit errors."""
    for attempt in range(max_retries):
        try:
            submission.edit(comment={'text_comment': comment_text})
            logger.info(f"Comment posted to submission {submission.id}")
            return True
        except CanvasException as e:
            if '429' in str(e):  # Rate limit exceeded
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential: 1s, 2s, 4s
                    logger.warning(f"Rate limited, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Max retries exceeded for submission {submission.id}")
                    raise
            else:
                # Other error (401, 403, 404, etc.) - don't retry
                logger.error(f"Canvas API error: {e}")
                raise
    return False
```

**Delay Between Comments:** 0.5-1 second delay between sequential posts provides safety margin

**Sources:**
- [Canvas API Throttling Best Practices](https://developerdocs.instructure.com/services/canvas/basics/file.throttling)
- [API Rate Limiting Discussion](https://community.canvaslms.com/t5/Developers-Group/API-Rate-Limiting/ba-p/255845)

## Error Handling Strategies

### Canvas API Error Codes

**Confidence:** HIGH

| Error Code | Meaning | Retry? | Handling Strategy |
|------------|---------|--------|-------------------|
| 401 | Unauthorized (invalid token) | No | Log error, alert user to check Canvas credentials |
| 403 | Forbidden (insufficient permissions) | No | Log error, verify TA has comment permissions |
| 404 | Not Found (invalid submission/course/assignment ID) | No | Log error, skip this submission |
| 422 | Unprocessable Entity (invalid parameters) | No | Log error with parameters, skip this submission |
| 429 | Rate Limit Exceeded | Yes | Exponential backoff retry (see above) |
| 500/502/503 | Server error | Yes | Brief retry with backoff (max 2 attempts) |

### Exception Handling Pattern

```python
from canvasapi.exceptions import CanvasException

try:
    submission.edit(comment={'text_comment': message})
except CanvasException as e:
    error_str = str(e)
    if '429' in error_str:
        # Rate limit - handled by retry logic
        raise
    elif '401' in error_str:
        logger.error("Canvas API token invalid or expired")
        # Stop entire operation - credentials broken
        raise
    elif '403' in error_str:
        logger.warning(f"Permission denied for submission {submission.id}")
        # Skip this submission, continue with others
        return False
    elif '404' in error_str:
        logger.warning(f"Submission {submission.id} not found")
        # Skip this submission
        return False
    else:
        logger.error(f"Unexpected Canvas API error: {e}")
        raise
except Exception as e:
    logger.error(f"Unexpected error posting comment: {e}", exc_info=True)
    raise
```

## Template Variable Substitution

### Recommended: Python Built-in `str.format()`

**Confidence:** HIGH

**Why `str.format()` over Jinja2:**
1. No additional dependencies
2. Sufficient for simple variable substitution
3. Simpler debugging and testing
4. Native Python syntax familiar to maintainers

**Template Pattern:**
```python
# Template definition (stored in database or config)
template = "You have used {late_days} late day(s) on this assignment. Total used: {total_late_days}/{allowed_late_days}"

# Variable substitution
message = template.format(
    late_days=3,
    total_late_days=8,
    allowed_late_days=10
)
# Result: "You have used 3 late day(s) on this assignment. Total used: 8/10"
```

**Safe Substitution with Missing Variables:**
```python
from string import Template

# Use string.Template for safer substitution
template = Template("You have used $late_days late day(s). Total: $total_late_days")

# safe_substitute() replaces what it can, leaves rest as-is
message = template.safe_substitute(late_days=3)
# Result: "You have used 3 late day(s). Total: $total_late_days"
```

**Recommended Variables for Late Day Comments:**
- `{student_name}`: Student's display name
- `{assignment_name}`: Assignment title
- `{late_days}`: Days late for this assignment
- `{total_late_days}`: Total late days used across all assignments
- `{remaining_late_days}`: Remaining late days (if policy exists)
- `{submitted_at}`: Submission timestamp
- `{due_at}`: Assignment due date

**Sources:**
- [Python String Formatting Methods](https://medium.com/@bluebirz/3-ways-for-python-string-template-71d2bb5d3de1)
- [String Template vs Format Strings](https://engineeringfordatascience.com/posts/python_string_formatting_for_data_science/)

### When to Consider Jinja2

**Use Jinja2 if:**
- Templates need conditional logic: `{% if late_days > 5 %}severe warning{% else %}normal{% endif %}`
- Templates need loops: `{% for assignment in assignments %}...{% endfor %}`
- Templates are stored as external files for reusability
- Templates need filters: `{{ student_name|title }}`

**Installation:** `uv add jinja2` (not currently needed)

**Sources:**
- [Jinja2 for Python String Formatting](https://realpython.com/primer-on-jinja-templating/)

## Duplicate Prevention Strategy

### Database-Tracked Idempotency

**Confidence:** HIGH

**Pattern:** Track posted comments in SQLite to prevent duplicates

**Why Database Tracking over Canvas API Checks:**
1. Canvas API doesn't provide idempotency keys for comment posting
2. Fetching all submission comments to check for duplicates is slower than local DB lookup
3. Local tracking provides audit trail
4. Allows "dry run" mode without Canvas API calls

**Database Schema Addition:**

```sql
CREATE TABLE comment_posting_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL,
    assignment_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    submission_id INTEGER NOT NULL,
    comment_template_id TEXT,           -- Template used (for tracking)
    comment_text TEXT NOT NULL,         -- Actual posted comment
    late_days_count INTEGER,            -- Late days at time of posting
    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    posted_by TEXT DEFAULT 'system',    -- User who triggered posting
    status TEXT DEFAULT 'posted',       -- 'posted', 'failed', 'dry_run'
    error_message TEXT,                 -- If status='failed'
    UNIQUE(course_id, assignment_id, user_id, comment_template_id)
);

CREATE INDEX idx_comment_history_course
    ON comment_posting_history(course_id, assignment_id);
CREATE INDEX idx_comment_history_user
    ON comment_posting_history(user_id);
CREATE INDEX idx_comment_history_status
    ON comment_posting_history(status);
```

**Duplicate Check Pattern:**

```python
def check_comment_already_posted(
    course_id: str,
    assignment_id: int,
    user_id: int,
    template_id: str
) -> bool:
    """Check if comment with this template was already posted."""
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id FROM comment_posting_history
               WHERE course_id = ?
               AND assignment_id = ?
               AND user_id = ?
               AND comment_template_id = ?
               AND status = 'posted'""",
            (course_id, assignment_id, user_id, template_id)
        )
        return cursor.fetchone() is not None

def record_posted_comment(
    course_id: str,
    assignment_id: int,
    user_id: int,
    submission_id: int,
    template_id: str,
    comment_text: str,
    late_days: int,
    status: str = 'posted',
    error: str = None
):
    """Record comment posting in history."""
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO comment_posting_history
               (course_id, assignment_id, user_id, submission_id,
                comment_template_id, comment_text, late_days_count,
                status, error_message)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(course_id, assignment_id, user_id, comment_template_id)
               DO UPDATE SET
                   posted_at = CURRENT_TIMESTAMP,
                   status = excluded.status,
                   error_message = excluded.error_message""",
            (course_id, assignment_id, user_id, submission_id,
             template_id, comment_text, late_days, status, error)
        )
        conn.commit()
```

**Sources:**
- [Idempotency Key Pattern](https://multithreaded.stitchfix.com/blog/2017/06/26/patterns-of-soa-idempotency-key/)
- [Preventing Duplicate API Requests](https://medium.com/@sohail_saifi/designing-idempotent-apis-preventing-duplicate-requests-24f2305afa5e)

## Testing Approaches

### Sandbox Course Testing

**Confidence:** HIGH

**Test Course ID:** `20960000000447574` (provided sandbox course)

**Testing Strategy:**

1. **Unit Tests:** Mock canvasapi responses
2. **Integration Tests:** Real API calls to sandbox course only
3. **Dry Run Mode:** Simulate posting without actual Canvas API calls

**Test Environment Detection:**

```python
SANDBOX_COURSE_ID = "20960000000447574"

def is_test_mode(course_id: str) -> bool:
    """Detect if running in test/sandbox mode."""
    return course_id == SANDBOX_COURSE_ID or os.getenv("TEST_MODE") == "true"

def post_comment_safe(submission, comment_text, course_id, dry_run=False):
    """Post comment with dry-run support."""
    if dry_run or is_test_mode(course_id):
        logger.info(f"[DRY RUN] Would post: {comment_text}")
        return True

    # Actual posting
    submission.edit(comment={'text_comment': comment_text})
    return True
```

**Integration Test Pattern:**

```python
import pytest
from canvasapi import Canvas

@pytest.mark.integration
def test_post_comment_to_sandbox():
    """Test comment posting to real Canvas sandbox course."""
    canvas = Canvas(os.getenv("CANVAS_API_URL"), os.getenv("CANVAS_API_TOKEN"))
    course = canvas.get_course(SANDBOX_COURSE_ID)

    # Create test assignment if needed
    assignment = course.get_assignment(test_assignment_id)
    submission = assignment.get_submission(test_user_id)

    # Post test comment
    test_comment = f"Test comment posted at {datetime.now(UTC).isoformat()}"
    submission.edit(comment={'text_comment': test_comment})

    # Verify comment appears in submission comments
    submission.reload()  # Refresh from API
    comments = submission.submission_comments
    assert any(test_comment in c.get('comment', '') for c in comments)
```

### Mocking Strategy

```python
from unittest.mock import Mock, patch

@pytest.fixture
def mock_submission():
    """Mock Canvas submission for unit tests."""
    submission = Mock()
    submission.id = 12345
    submission.user_id = 67890
    submission.assignment_id = 11111
    submission.edit = Mock(return_value=submission)
    return submission

def test_post_comment_with_retry_success(mock_submission):
    """Test successful comment posting."""
    result = post_comment_with_retry(
        mock_submission,
        "You used 3 late days"
    )
    assert result is True
    mock_submission.edit.assert_called_once_with(
        comment={'text_comment': 'You used 3 late days'}
    )
```

## Installation

```bash
# All dependencies already present in pyproject.toml
# No additional packages needed for comment posting feature

# For testing only (already in dev-dependencies):
uv add --dev pytest pytest-asyncio

# Optional: Only if advanced templating needed (NOT RECOMMENDED initially)
# uv add jinja2
```

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Parallel comment posting with threading/asyncio | Canvas API throttling penalties for parallel requests. Risk of 429 errors. | Sequential posting with 0.5-1s delay |
| Canvas comment fetching for duplicate detection | Slow, requires extra API calls. No native idempotency keys. | Local SQLite tracking table |
| Jinja2 for simple templates | Unnecessary dependency for basic variable substitution | Python built-in `str.format()` or `string.Template` |
| Posting to production course first | Risk of duplicate/incorrect comments to real students | Always test on sandbox course (ID: 20960000000447574) |
| Hardcoded comment text | Inflexible, requires code changes to update messages | Template system with database-stored templates |

## Stack Patterns by Variant

**If implementing bulk posting (100+ comments):**
- Add progress tracking with database status updates
- Implement pause/resume capability using posted comment history
- Add bulk operation logging to separate log file
- Consider batch size limits (e.g., 50 comments per batch)

**If implementing scheduled posting:**
- Use existing FastAPI background tasks (no celery needed for local deployment)
- Add job queue table to SQLite
- Log scheduled job results to separate table

**If implementing template management UI:**
- Add template CRUD endpoints to FastAPI
- Store templates in new `comment_templates` table
- Add template preview/validation before saving

## Version Compatibility

All required packages are already compatible in existing `pyproject.toml`:

| Package | Current Version | Compatible With | Notes |
|---------|-----------------|-----------------|-------|
| canvasapi | >=3.0.0 | Python >=3.11 | No breaking changes in comment API since 3.0 |
| FastAPI | >=0.104.0 | Pydantic 2.x | Fully compatible |
| SQLite | 3.x (built-in) | Python 3.11+ | No version conflicts |
| python-dateutil | >=2.8.0 | Python 3.11+ | Used for date parsing |

## Sources

### Canvas API Documentation (HIGH Confidence)
- [Canvas Submissions API](https://canvas.instructure.com/doc/api/submissions.html) - Comment posting endpoint
- [Canvas Throttling Documentation](https://canvas.instructure.com/doc/api/file.throttling.html) - Rate limiting
- [Canvas Submission Comments API](https://canvas.instructure.com/doc/api/submission_comments.html) - Comment management

### canvasapi Library (HIGH Confidence)
- [canvasapi Submission Reference](https://canvasapi.readthedocs.io/en/stable/submission-ref.html) - Python API
- [Canvas Community: Python API Comments](https://community.canvaslms.com/t5/Canvas-Developers-Group/Add-comments-text-via-Python-API/m-p/133923) - Community examples

### Rate Limiting & Error Handling (HIGH Confidence)
- [Canvas API Throttling Best Practices](https://developerdocs.instructure.com/services/canvas/basics/file.throttling) - Official throttling guide
- [API Rate Limiting Discussion](https://community.canvaslms.com/t5/Developers-Group/API-Rate-Limiting/ba-p/255845) - Community best practices

### Template Substitution (MEDIUM Confidence)
- [Python String Formatting Methods](https://medium.com/@bluebirz/3-ways-for-python-string-template-71d2bb5d3de1) - Comparison guide
- [Jinja2 Primer](https://realpython.com/primer-on-jinja-templating/) - Advanced templating

### Idempotency & Duplicate Prevention (HIGH Confidence)
- [Idempotency Key Pattern](https://multithreaded.stitchfix.com/blog/2017/06/26/patterns-of-soa-idempotency-key/) - Architecture pattern
- [Preventing Duplicate API Requests](https://medium.com/@sohail_saifi/designing-idempotent-apis-preventing-duplicate-requests-24f2305afa5e) - Implementation guide

---
*Stack research for: Canvas API Comment Posting Feature*
*Researched: 2026-02-15*
