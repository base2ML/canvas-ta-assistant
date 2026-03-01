# Phase 2: Posting Logic - Research

**Researched:** 2026-02-15
**Domain:** Canvas API comment posting with FastAPI SSE streaming
**Confidence:** HIGH

## Summary

Phase 2 implements Canvas submission comment posting via the canvasapi Python library with Server-Sent Events (SSE) for real-time progress updates, rate limiting, duplicate prevention, and comprehensive error handling. The foundation from Phase 1 (database tables for templates and posting history) is already in place.

**Key technical components:**
- Canvas API submission.edit() method for posting comments via canvasapi library
- FastAPI StreamingResponse with sse-starlette for real-time progress updates
- Rate limiting with exponential backoff to handle Canvas 429 errors
- Template variable substitution using Python str.format()
- Best-effort bulk posting with detailed failure reporting

**Primary recommendation:** Use SSE streaming response for synchronous bulk posting with real-time progress updates. This provides immediate feedback, simpler error handling, and no polling overhead compared to background tasks.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Bulk Posting Flow:**
- Best-effort execution: If one post fails during bulk posting, continue with remaining students. Log failures and report all at end
- Real-time progress updates: Use Server-Sent Events (SSE) to stream progress to frontend during bulk posting
- Progress information: Include overall progress count (e.g., "Posting 5/12") and error details for any failures
- Single endpoint for flexibility: Bulk posting endpoint handles both single-student (for testing) and multi-student posting - frontend passes array of 1 or many user_ids
- Final response format: Return summary counts (attempted, successful, failed, skipped) and list of failed students with error reasons

**API Endpoint Design:**
- Preview capability: Preview endpoint returns rendered comment text (with variables substituted) and duplicate detection status (which students already have comments)
- Request body structure: Posting requests include course_id, assignment_id, template selection (penalty/non_penalty or template_id), student IDs array, and optional override comment text for edge cases
- Variable substitution: Backend resolves template variables ({days_late}, {days_remaining}, {penalty_days}, {penalty_percent}, {max_late_days}) from student submission data before posting

### Claude's Discretion

- Rate limiting strategy (fixed delays, exponential backoff, or adaptive)
- Duplicate checking approach (pre-flight check vs during posting loop)
- Endpoint structure (single unified endpoint vs separate endpoints for preview/post)
- Synchronous vs asynchronous posting (SSE connection vs background job with polling)

### Deferred Ideas (OUT OF SCOPE)

None - discussion stayed within phase scope

</user_constraints>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| canvasapi | 3.2.0+ | Canvas LMS API wrapper | Official Python wrapper for Canvas API, handles pagination and object mapping |
| sse-starlette | 2.x | SSE streaming for FastAPI | Production-ready SSE implementation following W3C specification, native FastAPI/Starlette integration |
| asyncio | stdlib | Async operations | Built-in Python async runtime for rate limiting and async iteration |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| backoff | 2.x | Retry with exponential backoff | Canvas 429 error handling (alternative to custom implementation) |
| aiolimiter | 1.x | Async rate limiting | Precise rate limiting with leaky bucket algorithm (if custom rate limiter needed) |

### Already in Project
| Library | Purpose |
|---------|---------|
| FastAPI | API framework - StreamingResponse built-in |
| Pydantic | Request/response validation |
| loguru | Structured logging |
| canvasapi | Already in use for data sync |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SSE streaming | BackgroundTasks + polling | SSE: immediate feedback, simpler. BackgroundTasks: better for very heavy loads, requires polling endpoint |
| sse-starlette | Custom SSE implementation | sse-starlette: W3C compliant, battle-tested. Custom: more control, more complexity |
| backoff library | Custom retry logic | backoff: decorators, less code. Custom: more control over retry strategy |

**Installation:**
```bash
# Add to pyproject.toml dependencies
sse-starlette = "^2.0"
backoff = "^2.2"  # Optional: if using library instead of custom retry

# Already installed (no action needed)
# canvasapi, fastapi, pydantic, loguru
```

---

## Architecture Patterns

### Recommended Project Structure

```
# Existing structure - no new files needed
main.py                         # Add SSE endpoints here
canvas_sync.py                  # Add post_submission_comment() function
database.py                     # Already has template/history functions
```

### Pattern 1: SSE Streaming Endpoint for Bulk Posting

**What:** FastAPI endpoint that streams progress events using Server-Sent Events while posting comments

**When to use:** For bulk posting operations where real-time progress feedback is needed

**Example:**
```python
# Source: sse-starlette documentation + FastAPI patterns
from fastapi import FastAPI
from sse_starlette import EventSourceResponse
import asyncio

@app.post("/api/comments/post/{assignment_id}")
async def post_comments(
    assignment_id: int,
    request: PostCommentsRequest
):
    """Post comments to Canvas with SSE progress streaming."""

    async def generate_progress():
        total = len(request.user_ids)
        successful = []
        failed = []
        skipped = []

        for idx, user_id in enumerate(request.user_ids, 1):
            # Progress event
            yield {
                "event": "progress",
                "data": json.dumps({
                    "current": idx,
                    "total": total,
                    "user_id": user_id,
                    "status": "posting"
                })
            }

            try:
                # Check duplicate
                if db.check_duplicate_posting(...):
                    skipped.append({"user_id": user_id, "reason": "already_posted"})
                    continue

                # Post comment
                result = await asyncio.to_thread(
                    canvas_sync.post_submission_comment,
                    course_id, assignment_id, user_id, comment_text
                )
                successful.append(user_id)

                # Rate limiting delay
                await asyncio.sleep(0.5)

            except Exception as e:
                failed.append({"user_id": user_id, "error": str(e)})
                logger.error(f"Failed to post comment: {e}")

        # Final summary event
        yield {
            "event": "complete",
            "data": json.dumps({
                "attempted": total,
                "successful": len(successful),
                "failed": len(failed),
                "skipped": len(skipped),
                "failed_details": failed
            })
        }

    return EventSourceResponse(generate_progress())
```

**Key points:**
- EventSourceResponse automatically handles SSE protocol (data: prefix, \n\n separator)
- Use asyncio.to_thread() to run blocking Canvas API calls without blocking event loop
- Yield event dictionaries with "event" and "data" keys for structured events
- Final event signals completion with summary statistics

### Pattern 2: Canvas Comment Posting with Retry

**What:** Function that posts submission comments via Canvas API with exponential backoff retry

**When to use:** For all Canvas comment posting operations

**Example:**
```python
# Source: Canvas API documentation + backoff patterns
import time
from canvasapi.exceptions import CanvasException

def post_submission_comment(
    course_id: str,
    assignment_id: int,
    user_id: int,
    comment_text: str,
    template_id: int | None = None,
    max_retries: int = 3
) -> dict:
    """Post comment to Canvas submission with retry logic.

    Returns:
        dict with keys: canvas_comment_id, posted_at, status
    """
    canvas = canvas_sync.get_canvas_client()
    course = canvas.get_course(course_id)
    assignment = course.get_assignment(assignment_id)
    submission = assignment.get_submission(user_id)

    retry_count = 0
    base_delay = 1.0

    while retry_count <= max_retries:
        try:
            # Canvas API: submission.edit(comment={'text_comment': '...'})
            result = submission.edit(comment={'text_comment': comment_text})

            # Record success in posting history
            db.record_comment_posting(
                course_id=course_id,
                assignment_id=assignment_id,
                user_id=user_id,
                template_id=template_id,
                comment_text=comment_text,
                status='posted',
                canvas_comment_id=getattr(result, 'id', None)
            )

            return {
                'canvas_comment_id': getattr(result, 'id', None),
                'posted_at': datetime.now(UTC).isoformat(),
                'status': 'success'
            }

        except CanvasException as e:
            # Check for rate limit (429)
            if '429' in str(e) or 'rate limit' in str(e).lower():
                if retry_count >= max_retries:
                    raise

                # Exponential backoff: 1s, 2s, 4s
                delay = base_delay * (2 ** retry_count)
                logger.warning(f"Rate limited, retrying in {delay}s (attempt {retry_count + 1})")
                time.sleep(delay)
                retry_count += 1
            else:
                # Non-rate-limit error, don't retry
                raise

    raise Exception(f"Failed after {max_retries} retries")
```

**Key points:**
- submission.edit() is the canvasapi method for posting comments (confirmed via official docs)
- Exponential backoff: 1s, 2s, 4s for 429 errors
- Non-rate-limit errors fail immediately (don't retry Canvas auth errors, missing submissions, etc.)
- Record to posting history on success for duplicate prevention

### Pattern 3: Template Variable Substitution

**What:** Render templates with student-specific data using Python str.format()

**When to use:** Before posting comments or in preview endpoint

**Example:**
```python
# Source: Python stdlib string.format() documentation
def render_template(
    template_text: str,
    submission_data: dict
) -> str:
    """Render template with student submission data.

    Args:
        template_text: Template with {variable} placeholders
        submission_data: Dict with keys: days_late, days_remaining, etc.

    Returns:
        Rendered comment text with variables substituted

    Raises:
        ValueError: If template has invalid syntax or unknown variables
    """
    # Validate required variables are present
    required_vars = {
        'days_late', 'days_remaining', 'penalty_days',
        'penalty_percent', 'max_late_days'
    }

    # Create full context with all allowed variables
    context = {var: submission_data.get(var, 0) for var in required_vars}

    try:
        rendered = template_text.format(**context)
        return rendered
    except KeyError as e:
        raise ValueError(f"Template references undefined variable: {e}")
    except ValueError as e:
        raise ValueError(f"Invalid template syntax: {e}")
```

**Key points:**
- str.format() raises KeyError for missing variables, ValueError for syntax errors
- Provide all allowed variables even if template doesn't use them (safer than partial substitution)
- Catch and re-raise with user-friendly error messages
- Validation should happen at template creation time (already implemented in main.py validate_template_syntax)

### Pattern 4: Preview Endpoint

**What:** Render templates and check duplicates without posting to Canvas

**When to use:** Before bulk posting to show user what will be posted

**Example:**
```python
# Source: FastAPI patterns + project requirements
@app.post("/api/comments/preview/{assignment_id}")
async def preview_comments(
    assignment_id: int,
    request: PostCommentsRequest
) -> dict:
    """Preview rendered comments and duplicate status."""

    # Get template
    if request.template_id:
        template = db.get_template_by_id(request.template_id)
    else:
        templates = db.get_templates(request.template_type)
        template = templates[0] if templates else None

    if not template:
        raise HTTPException(404, "Template not found")

    # Get submission data for variable substitution
    submissions = db.get_submissions(request.course_id, assignment_id)
    users = db.get_users(request.course_id)

    previews = []
    for user_id in request.user_ids:
        # Calculate late days data for this user
        submission_data = calculate_late_days_for_user(user_id, assignment_id, submissions)

        # Render template (or use override)
        if request.override_comment:
            comment_text = request.override_comment
        else:
            comment_text = render_template(template['template_text'], submission_data)

        # Check duplicate
        duplicate = db.check_duplicate_posting(
            request.course_id,
            assignment_id,
            user_id,
            template['id'] if not request.override_comment else None
        )

        user = next((u for u in users if u['id'] == user_id), None)

        previews.append({
            'user_id': user_id,
            'user_name': user['name'] if user else f'User {user_id}',
            'comment_text': comment_text,
            'already_posted': duplicate is not None,
            'variables_used': submission_data
        })

    return {
        'assignment_id': assignment_id,
        'template_id': template['id'],
        'previews': previews,
        'total': len(previews),
        'already_posted_count': sum(1 for p in previews if p['already_posted'])
    }
```

**Key points:**
- Preview shows exact text that will be posted (with variables substituted)
- Includes duplicate detection status for each student
- Shows which students would be skipped during actual posting
- Uses same render_template function as actual posting for consistency

### Anti-Patterns to Avoid

- **Posting comments in parallel without rate limiting:** Canvas API throttles requests; parallel posting will trigger 429 errors and penalties. Always post sequentially with delays.

- **Retrying all Canvas errors:** Only retry 429 rate limit errors. Auth errors (401), not found errors (404), and permission errors (403) should fail immediately.

- **Using BackgroundTasks for real-time progress:** BackgroundTasks execute after response is sent, preventing progress updates. Use SSE streaming instead.

- **Ignoring duplicate detection:** Always check posting history before posting to prevent duplicate comments on student submissions.

- **Template rendering without validation:** Template syntax errors or missing variables should be caught at template creation time, not during bulk posting.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE protocol implementation | Custom HTTP streaming with manual event formatting | sse-starlette library | SSE requires specific format (data: prefix, \n\n separator, event types). sse-starlette handles W3C SSE spec, connection management, client disconnect detection |
| Exponential backoff retry | Manual retry loops with time.sleep() | backoff library decorators | backoff handles retry logic, jitter, max attempts, and selective exception filtering. Less code, fewer bugs |
| Rate limiting with token bucket | Custom request counter with time windows | aiolimiter library | Token bucket/leaky bucket algorithms are complex. aiolimiter provides async-safe rate limiting with precise request/second control |
| Canvas API object mapping | Manual JSON parsing and dict access | canvasapi library | Already in project. Handles pagination, authentication, object relationships, and API changes |

**Key insight:** SSE streaming, retry logic, and rate limiting all have subtle edge cases (client disconnects, thundering herd, clock skew). Battle-tested libraries handle these edge cases that custom implementations miss.

---

## Common Pitfalls

### Pitfall 1: Canvas 429 Rate Limiting with Parallel Requests

**What goes wrong:** Attempting to post comments in parallel triggers Canvas rate limiting penalties and causes cascading 429 errors.

**Why it happens:** Canvas API documentation states: "Parallel requests are subject to an additional pre-flight penalty to prevent a large number of incoming requests being able to bring the system down before their cost is counted."

**How to avoid:**
- Always post comments sequentially (one at a time)
- Add 0.5-1.0 second delay between posts
- Implement exponential backoff for 429 errors (1s, 2s, 4s)
- Monitor X-Request-Cost header to track quota usage

**Warning signs:**
- Multiple 429 errors in logs
- X-Rate-Limit-Remaining header decreasing rapidly
- Canvas API returning "Rate Limit Exceeded" messages

### Pitfall 2: SSE Client Disconnect Not Detected

**What goes wrong:** Server continues processing and posting comments after client disconnects, wasting resources and potentially posting partial batches.

**Why it happens:** SSE is server-push only; server doesn't know client disconnected unless it checks.

**How to avoid:**
- Check `await request.is_disconnected()` in SSE generator loop
- Use sse-starlette's automatic disconnect detection
- Log disconnect events for debugging
- Return early if client disconnects mid-batch

**Warning signs:**
- SSE endpoint continues running after frontend closed
- Database shows partial posting batches with no corresponding frontend completion
- Server logs show full batch completion but frontend shows timeout

### Pitfall 3: Template Variable Substitution Errors in Production

**What goes wrong:** Templates work in preview but fail during bulk posting due to missing submission data.

**Why it happens:** Preview uses mock data or subset of students; bulk posting encounters edge cases (no submission, missing due date, null values).

**How to avoid:**
- Validate templates at creation time with all allowed variables
- Provide default values (0, "N/A") for optional variables
- Use str.format() which raises clear KeyError/ValueError exceptions
- Test templates with edge case students (no submission, dropped, etc.)

**Warning signs:**
- KeyError: 'days_late' in production logs
- Comments posted for some students but not others in same batch
- Template renders in preview but fails in bulk posting

### Pitfall 4: Duplicate Detection Race Conditions

**What goes wrong:** Two simultaneous posting requests for same student create duplicate comments.

**Why it happens:** check_duplicate_posting() + record_comment_posting() is not atomic; race window exists between check and insert.

**How to avoid:**
- Use SQLite UNIQUE constraint (already implemented in schema)
- Handle IntegrityError on duplicate insert as "already posted"
- Check duplicate before posting AND catch database errors
- Consider row-level locking for high-concurrency scenarios (not needed for single-user deployment)

**Warning signs:**
- Students report duplicate late day comments on submissions
- Database has multiple posting_history records for same (course_id, assignment_id, user_id, template_id)
- Logs show "posted successfully" but frontend shows "skipped as duplicate"

### Pitfall 5: Not Handling Missing Submissions

**What goes wrong:** Attempting to post comment to non-existent submission causes Canvas 404 error.

**Why it happens:** Student hasn't submitted yet, or submission was deleted.

**How to avoid:**
- Check submission exists before calling submission.edit()
- Use assignment.get_submission() and handle CanvasException
- Log warning and continue to next student (best-effort execution)
- Include "missing submission" in final error report

**Warning signs:**
- Canvas 404 Not Found errors in logs during bulk posting
- Comments successfully posted to some students but not others with "submission not found"
- Preview shows all students but bulk posting reports many failures

---

## Code Examples

Verified patterns from official sources:

### Canvas Submission Comment Posting
```python
# Source: Canvas API Submissions documentation (canvas.instructure.com/doc/api/submissions.html)
# and canvasapi library examples (canvasapi.readthedocs.io)

from canvasapi import Canvas
from canvasapi.exceptions import CanvasException
import os

def post_submission_comment(
    course_id: str,
    assignment_id: int,
    user_id: int,
    comment_text: str
) -> dict:
    """Post a text comment to a student's submission.

    Uses Canvas API endpoint:
    PUT /api/v1/courses/:course_id/assignments/:assignment_id/submissions/:user_id

    With parameter: comment[text_comment]
    """
    canvas = Canvas(os.getenv('CANVAS_API_URL'), os.getenv('CANVAS_API_TOKEN'))
    course = canvas.get_course(course_id)
    assignment = course.get_assignment(assignment_id)

    try:
        submission = assignment.get_submission(user_id)

        # submission.edit() maps to PUT /submissions/:user_id
        # with comment parameter
        result = submission.edit(comment={'text_comment': comment_text})

        return {
            'status': 'success',
            'canvas_comment_id': getattr(result, 'id', None),
            'user_id': user_id
        }

    except CanvasException as e:
        # Handle specific Canvas errors
        if '404' in str(e):
            raise ValueError(f"Submission not found for user {user_id}")
        elif '429' in str(e):
            raise Exception("Rate limit exceeded")
        else:
            raise
```

### SSE Progress Streaming
```python
# Source: sse-starlette documentation (pypi.org/project/sse-starlette/)
# and FastAPI streaming examples

from fastapi import FastAPI
from sse_starlette import EventSourceResponse
import asyncio
import json

app = FastAPI()

@app.post("/api/comments/post/{assignment_id}")
async def post_comments_with_progress(
    assignment_id: int,
    request: PostCommentsRequest
):
    """Stream progress events while posting comments."""

    async def event_generator():
        """Generate SSE events for each posting step."""
        total = len(request.user_ids)

        for idx, user_id in enumerate(request.user_ids, 1):
            # Progress update event
            yield {
                "event": "progress",
                "data": json.dumps({
                    "current": idx,
                    "total": total,
                    "user_id": user_id,
                    "percent": round((idx / total) * 100, 1)
                })
            }

            try:
                # Post comment (blocking call wrapped in asyncio.to_thread)
                result = await asyncio.to_thread(
                    post_submission_comment,
                    request.course_id,
                    assignment_id,
                    user_id,
                    comment_text
                )

                # Success event
                yield {
                    "event": "success",
                    "data": json.dumps({
                        "user_id": user_id,
                        "comment_id": result['canvas_comment_id']
                    })
                }

            except Exception as e:
                # Error event
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "user_id": user_id,
                        "error": str(e)
                    })
                }

            # Rate limiting delay
            await asyncio.sleep(0.5)

        # Completion event
        yield {
            "event": "complete",
            "data": json.dumps({"message": "All comments posted"})
        }

    return EventSourceResponse(event_generator())
```

### Exponential Backoff Retry
```python
# Source: Python backoff library (github.com/litl/backoff)
# and Canvas API throttling docs

import backoff
from canvasapi.exceptions import CanvasException

def is_rate_limit_error(e):
    """Check if exception is Canvas rate limit error."""
    return isinstance(e, CanvasException) and '429' in str(e)

@backoff.on_exception(
    backoff.expo,              # Exponential backoff
    CanvasException,           # Exception type
    giveup=lambda e: not is_rate_limit_error(e),  # Only retry 429 errors
    max_tries=4,               # Try once + 3 retries
    factor=1                   # Base delay: 1s, 2s, 4s
)
def post_with_retry(submission, comment_text):
    """Post comment with automatic retry on 429 errors."""
    return submission.edit(comment={'text_comment': comment_text})

# Alternative: Manual implementation
def post_with_manual_retry(submission, comment_text, max_retries=3):
    """Manual exponential backoff implementation."""
    import time

    for attempt in range(max_retries + 1):
        try:
            return submission.edit(comment={'text_comment': comment_text})
        except CanvasException as e:
            if '429' not in str(e) or attempt >= max_retries:
                raise

            delay = 2 ** attempt  # 1s, 2s, 4s
            logger.warning(f"Rate limited, retry in {delay}s")
            time.sleep(delay)
```

### Template Variable Rendering
```python
# Source: Python str.format() documentation (docs.python.org/3/library/string.html)

def render_template(template_text: str, submission_data: dict) -> str:
    """Render template with submission-specific variables.

    Args:
        template_text: Template with {days_late}, {days_remaining}, etc.
        submission_data: Dict with variable values

    Returns:
        Rendered comment text

    Raises:
        ValueError: If template syntax invalid or variables missing
    """
    # Ensure all allowed variables present (use defaults if missing)
    allowed_vars = {
        'days_late', 'days_remaining', 'penalty_days',
        'penalty_percent', 'max_late_days'
    }

    context = {
        var: submission_data.get(var, 0)
        for var in allowed_vars
    }

    try:
        return template_text.format(**context)
    except KeyError as e:
        raise ValueError(f"Template uses undefined variable: {e}")
    except ValueError as e:
        raise ValueError(f"Template syntax error: {e}")

# Example usage
template = (
    "Days late: {days_late}\n"
    "Penalty: {penalty_percent}%\n"
    "Days remaining: {days_remaining}"
)

submission_data = {
    'days_late': 3,
    'penalty_days': 3,
    'penalty_percent': 30,
    'days_remaining': 4,
    'max_late_days': 7
}

rendered = render_template(template, submission_data)
# Output:
# Days late: 3
# Penalty: 30%
# Days remaining: 4
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Polling for long operations | Server-Sent Events (SSE) streaming | 2023-2024 | Real-time updates without polling overhead, simpler client code |
| Custom retry loops | backoff library decorators | 2020+ | Declarative retry logic, jitter support, less code |
| Threading for async I/O | asyncio with asyncio.to_thread() | Python 3.9+ | Better async/await patterns, easier to reason about concurrency |
| Manual SSE implementation | sse-starlette library | 2021+ | W3C compliant, handles edge cases, less boilerplate |

**Deprecated/outdated:**
- **Polling endpoints for background task status:** Replaced by SSE streaming for real-time updates. Polling adds latency and server load.
- **ThreadPoolExecutor for API calls in FastAPI:** Use asyncio.to_thread() instead (simpler, integrated with async/await).
- **Manual SSE event formatting:** sse-starlette handles protocol details automatically.

---

## Open Questions

None - all technical domains have been researched with sufficient depth for planning.

---

## Sources

### Primary (HIGH confidence)

#### Canvas API and canvasapi Library
- [Canvas API Submissions Documentation](https://canvas.instructure.com/doc/api/submissions.html) - PUT endpoint for posting comments
- [Canvas API Throttling Documentation](https://canvas.instructure.com/doc/api/file.throttling.html) - Rate limiting rules and 429 error handling
- [canvasapi Submission Reference](https://canvasapi.readthedocs.io/en/stable/submission-ref.html) - Official Python library documentation
- [Canvas API Submission Comments](https://canvas.instructure.com/doc/api/submission_comments.html) - Comment endpoints and parameters

#### FastAPI and SSE
- [sse-starlette PyPI](https://pypi.org/project/sse-starlette/) - Production-ready SSE library for FastAPI/Starlette
- [FastAPI Background Tasks Documentation](https://fastapi.tiangolo.com/tutorial/background-tasks/) - Background tasks vs streaming comparison

#### Python Libraries
- [Python string.format() Documentation](https://docs.python.org/3/library/string.html) - Template variable substitution
- [backoff Library](https://github.com/litl/backoff) - Exponential backoff retry decorators

### Secondary (MEDIUM confidence)

- [Implementing Server-Sent Events (SSE) with FastAPI](https://mahdijafaridev.medium.com/implementing-server-sent-events-sse-with-fastapi-real-time-updates-made-simple-6492f8bfc154) - Practical SSE implementation guide
- [Real-Time Notifications in Python: Using SSE with FastAPI](https://medium.com/@inandelibas/real-time-notifications-in-python-using-sse-with-fastapi-1c8c54746eb7) - SSE patterns for real-time updates
- [Python asyncio retries rate limited](https://dev-kit.io/blog/python/python-asyncio-retries-rate-limited) - Rate limiting strategies
- [Effective Strategies for Rate Limiting Asynchronous Requests in Python](https://proxiesapi.com/articles/effective-strategies-for-rate-limiting-asynchronous-requests-in-python) - Async rate limiting patterns
- [Managing Background Tasks and Long-Running Operations in FastAPI](https://leapcell.io/blog/managing-background-tasks-and-long-running-operations-in-fastapi) - Background tasks vs streaming trade-offs

### Tertiary (LOW confidence)

None used - all findings verified with official documentation or authoritative sources.

---

## Metadata

**Confidence breakdown:**
- Canvas API comment posting: HIGH - Verified with official Canvas API docs and canvasapi library documentation
- SSE streaming with FastAPI: HIGH - Verified with sse-starlette official docs and FastAPI examples
- Rate limiting strategies: HIGH - Verified with Canvas throttling docs and Python backoff library
- Error handling patterns: HIGH - Verified with canvasapi exception handling and Canvas API error codes

**Research date:** 2026-02-15
**Valid until:** 60 days (2026-04-15) - Canvas API and FastAPI/SSE patterns are stable

**Claude's recommendations (for discretion areas):**

1. **Rate limiting strategy:** Use fixed 0.5-1.0s delay between posts + exponential backoff (1s, 2s, 4s) on 429 errors. This is simpler than adaptive rate limiting and sufficient for single-user deployment.

2. **Duplicate checking:** Check during posting loop (not pre-flight). Pre-flight check could become stale if user waits between preview and post. In-loop checking guarantees freshness.

3. **Endpoint structure:** Single unified /api/comments/post endpoint for both preview (dry_run=true) and actual posting. Simpler API surface, shared validation logic.

4. **Posting approach:** Synchronous SSE streaming (not background tasks). Provides real-time feedback, simpler error handling, no polling overhead. Background tasks better for very heavy loads (not applicable here).
