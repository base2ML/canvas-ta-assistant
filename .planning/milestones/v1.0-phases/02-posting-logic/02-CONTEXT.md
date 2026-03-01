# Phase 2: Posting Logic - Context

**Gathered:** 2026-02-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Canvas API comment posting with all safety mechanisms integrated. This phase delivers backend API endpoints for posting late day comments to Canvas submissions via the canvasapi library. Includes variable substitution, preview capability, bulk posting with rate limiting, duplicate prevention, and graceful error handling.

Foundation from Phase 1 (templates, posting history, safety checks) is in place - this phase builds the Canvas integration layer.

</domain>

<decisions>
## Implementation Decisions

### Bulk Posting Flow
- **Best-effort execution**: If one post fails during bulk posting, continue with remaining students. Log failures and report all at end.
- **Real-time progress updates**: Use Server-Sent Events (SSE) to stream progress to frontend during bulk posting
- **Progress information**: Include overall progress count (e.g., "Posting 5/12") and error details for any failures
- **Single endpoint for flexibility**: Bulk posting endpoint handles both single-student (for testing) and multi-student posting - frontend passes array of 1 or many user_ids
- **Final response format**: Return summary counts (attempted, successful, failed, skipped) and list of failed students with error reasons

### API Endpoint Design
- **Preview capability**: Preview endpoint returns rendered comment text (with variables substituted) and duplicate detection status (which students already have comments)
- **Request body structure**: Posting requests include course_id, assignment_id, template selection (penalty/non_penalty or template_id), student IDs array, and optional override comment text for edge cases
- **Variable substitution**: Backend resolves template variables ({days_late}, {days_remaining}, {penalty_days}, {penalty_percent}, {max_late_days}) from student submission data before posting

### Claude's Discretion
- Rate limiting strategy (fixed delays, exponential backoff, or adaptive)
- Duplicate checking approach (pre-flight check vs during posting loop)
- Endpoint structure (single unified endpoint vs separate endpoints for preview/post)
- Synchronous vs asynchronous posting (SSE connection vs background job with polling)

</decisions>

<specifics>
## Specific Ideas

- Testing workflow: TAs should be able to test with a single student before bulk posting to entire class
- Override comment text enables manual edits for edge cases where template doesn't fit

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-posting-logic*
*Context gathered: 2026-02-15*
