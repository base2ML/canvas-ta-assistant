# Feature Research: Canvas Comment Posting Automation

**Domain:** Canvas LMS Comment Posting Automation
**Researched:** 2026-02-15
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete or unsafe.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Preview before posting** | TAs must verify comments before they reach students | MEDIUM | Show computed comment text with all variables resolved for each student before posting |
| **Confirmation dialog** | Prevent accidental posting to live course | LOW | Standard "Are you sure?" confirmation with count of students affected |
| **Comment template management** | Reusability - same messages each semester | LOW | Store templates in settings; Canvas SpeedGrader has built-in Comment Library for manual grading |
| **Variable substitution** | Personalization - each student sees their own data | MEDIUM | {days_late}, {days_remaining}, {penalty_days}, {penalty_percent}, {max_late_days} already defined in project context |
| **Duplicate prevention** | Don't post same comment twice to same student | MEDIUM | Track posted comments in SQLite with (assignment_id, user_id, comment_hash) to detect duplicates |
| **Error handling & rollback** | API failures shouldn't leave partial state | MEDIUM | If posting fails midway, log which students got comments and allow retry/recovery |
| **Bulk posting by assignment** | TAs grade by assignment, not by student | LOW | Primary workflow: select assignment → preview comments → post all |
| **Test mode / dry run** | Must test safely without affecting students | HIGH | Critical safety feature - prevent posting to live course during development/testing |
| **Posted comment history** | Audit trail - what was posted when | MEDIUM | Track in SQLite: timestamp, assignment, student, comment text, posted by (TA/system) |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Conditional templates** | Smart automation - different messages based on penalty threshold | MEDIUM | Two templates (penalty vs non-penalty) already in project context; could extend to more conditions |
| **Batch preview grouping** | Efficiency - see all penalty cases together before posting | MEDIUM | Group preview by template type so TA can review all "penalty" messages before confirming |
| **Comment edit before posting** | Flexibility - adjust individual comments in preview | HIGH | Allow TA to edit computed comment text for specific students before final post |
| **Rate limiting awareness** | Reliability - respect Canvas API throttling | MEDIUM | Canvas API throttles at ~700 req/hr/token; add delays (250ms) between posts; show progress bar |
| **Undo recently posted** | Safety net - delete comments posted in last N minutes | MEDIUM | Track recent posts; provide "Undo last batch" button that deletes via Canvas API within grace period |
| **Template variable tester** | Developer experience - validate templates before using | LOW | Show sample output with mock data when editing templates in Settings |
| **Multi-assignment posting** | Efficiency - post late day comments for all assignments at once | HIGH | Less common workflow but saves time at semester end; increases complexity significantly |
| **Group assignment support** | Completeness - handle group submissions | MEDIUM | Canvas API supports `group_comment` parameter; post once to reach all group members |
| **Comment attachments** | Rich feedback - attach rubrics or grade breakdowns | HIGH | Canvas API supports file uploads with comments; useful for complex penalty calculations |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Automated posting on submission** | "Set it and forget it" convenience | Students expect immediate feedback; auto-comments without TA review violates academic integrity norms | Use manual trigger after TA reviews submissions |
| **Complex template logic (if/else/loops)** | Power users want full programming | Becomes hard to maintain; errors affect students; testing burden increases exponentially | Use simple variable substitution + conditional template selection (2-3 templates max) |
| **Student-facing template library** | Students want to see all possible comments | Undermines pedagogical value; students game the system; reduces personalization | Keep templates instructor-only; students see final comment only |
| **Real-time sync with Canvas** | Users expect live data always | Canvas API rate limiting makes this impractical; polling creates unnecessary load | Use manual refresh + cache data locally in SQLite |
| **Email notifications for posted comments** | Extra student notification | Canvas already sends notifications for comments; duplicates create spam; users can't opt out | Rely on Canvas's built-in notification system |

## Feature Dependencies

```
Comment Template Management
    └──requires──> Variable Substitution System
                       └──requires──> Late Days Data (already exists)

Preview Before Posting
    └──requires──> Variable Substitution System
    └──requires──> Duplicate Detection (to show warning in preview)

Bulk Posting
    └──requires──> Preview Before Posting
    └──requires──> Confirmation Dialog
    └──requires──> Duplicate Prevention
    └──requires──> Posted Comment History

Test Mode
    └──requires──> Settings Configuration (test course ID)
    └──enhances──> All posting features (wraps them with safety check)

Rate Limiting Awareness
    └──enhances──> Bulk Posting (prevents throttling errors)

Undo Recently Posted
    └──requires──> Posted Comment History
    └──requires──> Canvas API delete comment endpoint
```

### Dependency Notes

- **Variable Substitution requires Late Days Data:** The variables {days_late}, {penalty_days}, etc. are computed from existing late days tracking data structure
- **Preview requires Duplicate Detection:** Preview should show warnings if comment already exists for a student
- **Bulk Posting requires Preview:** Must show all computed comments before posting; no "blind" bulk operations
- **Test Mode wraps all posting:** Check test mode flag BEFORE any Canvas API write operation
- **Rate Limiting enhances Bulk Posting:** Without delays, bulk posting to 100+ students will hit Canvas throttling (429 errors)

## MVP Definition

### Launch With (v1 - Initial Release)

Minimum viable product — what's needed to replicate Jupyter notebook workflow safely.

- [x] **Comment Template Management** — Store two templates (penalty/non-penalty) in Settings page
- [x] **Variable Substitution** — Replace {days_late}, {days_remaining}, {penalty_days}, {penalty_percent}, {max_late_days} with student data
- [x] **Preview Before Posting** — Show table of computed comments grouped by template type (penalty vs non-penalty)
- [x] **Confirmation Dialog** — Final "Post N comments?" confirmation with student count
- [x] **Duplicate Prevention** — Track posted comments in SQLite; warn if comment already exists
- [x] **Bulk Posting by Assignment** — Select assignment → preview → confirm → post to all students with late submissions
- [x] **Test Mode Toggle** — Settings page checkbox: "Use test course" with test course ID field
- [x] **Posted Comment History** — SQLite table logging all posted comments with timestamp
- [x] **Error Handling** — Log failures; show which students got comments vs which failed; allow retry

**Why this is MVP:** Replicates the existing Jupyter notebook workflow with safety improvements (preview, duplicate prevention, test mode). TAs can post late day penalty comments with confidence.

### Add After Validation (v1.x)

Features to add once core is working and TAs request them.

- [ ] **Rate Limiting Awareness** — Trigger: TAs report throttling errors when posting to large courses (100+ students)
- [ ] **Batch Preview Grouping** — Trigger: TAs want to review all penalty cases separately from non-penalty cases
- [ ] **Template Variable Tester** — Trigger: TAs make template mistakes and post incorrect comments; want to test first
- [ ] **Undo Recently Posted** — Trigger: TAs request ability to delete comments posted by mistake
- [ ] **Conditional Template Selection** — Trigger: TAs want >2 templates (e.g., different messages for different penalty tiers)
- [ ] **Group Assignment Support** — Trigger: Course uses group assignments; TAs need to post once per group
- [ ] **Comment Edit Before Posting** — Trigger: TAs want to personalize specific comments before posting

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **Multi-Assignment Posting** — Complexity too high for MVP; defer until TAs request it
- [ ] **Comment Attachments** — Useful for advanced grading but increases scope significantly
- [ ] **Template Versioning** — Track template changes over time; useful for multi-semester use
- [ ] **Comment Analytics** — Show stats on comment types posted, student response rates, etc.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Preview Before Posting | HIGH | MEDIUM | P1 |
| Test Mode Toggle | HIGH | LOW | P1 |
| Duplicate Prevention | HIGH | MEDIUM | P1 |
| Variable Substitution | HIGH | MEDIUM | P1 |
| Comment Template Management | HIGH | LOW | P1 |
| Confirmation Dialog | HIGH | LOW | P1 |
| Bulk Posting by Assignment | HIGH | LOW | P1 |
| Posted Comment History | HIGH | MEDIUM | P1 |
| Error Handling & Rollback | HIGH | MEDIUM | P1 |
| Rate Limiting Awareness | MEDIUM | MEDIUM | P2 |
| Batch Preview Grouping | MEDIUM | MEDIUM | P2 |
| Template Variable Tester | MEDIUM | LOW | P2 |
| Undo Recently Posted | MEDIUM | MEDIUM | P2 |
| Group Assignment Support | MEDIUM | MEDIUM | P2 |
| Comment Edit Before Posting | MEDIUM | HIGH | P2 |
| Multi-Assignment Posting | LOW | HIGH | P3 |
| Comment Attachments | LOW | HIGH | P3 |
| Template Versioning | LOW | MEDIUM | P3 |
| Comment Analytics | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch (replicates Jupyter notebook workflow safely)
- P2: Should have, add when requested by TAs
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Canvas SpeedGrader | TimelyGrader (AI) | Our Approach |
|---------|---------------------|-------------------|--------------|
| **Comment Templates** | Comment Library (manual, per-instructor, no variables) | AI-generated, rubric-aware | Template with variable substitution (middle ground) |
| **Bulk Posting** | None (SpeedGrader is one-at-a-time) | Batch grading with AI review | Bulk posting by assignment with preview |
| **Duplicate Prevention** | None | None (AI always generates new) | Track in SQLite, warn before posting |
| **Preview/Confirmation** | Live preview in SpeedGrader | AI confirmation before posting to Canvas | Table preview with grouping |
| **Test Mode** | Student View (limited - only 1 test student) | Separate test environment | Toggle in Settings (point to test course) |
| **Variable Substitution** | None (manual typing or static library) | AI generates personalized content | Template variables: {days_late}, etc. |
| **Rate Limiting** | N/A (manual grading is slow) | Built-in throttling for API calls | Add delays between posts (250ms) |
| **Undo Posted Comments** | Manual delete in SpeedGrader | None | API-based delete within grace period |

### Key Differentiators vs Canvas SpeedGrader

1. **Bulk posting with preview** - SpeedGrader requires grading one student at a time; we batch by assignment
2. **Variable substitution** - SpeedGrader Comment Library is static text; we compute personalized values
3. **Duplicate prevention** - SpeedGrader doesn't track what you've posted; we prevent re-posting
4. **Test mode** - SpeedGrader Student View is limited to 1 test student; we point to entire test course

### Key Differentiators vs AI Grading Tools

1. **Deterministic templates** - AI tools generate variable content; we use predictable templates (important for grade penalties)
2. **Lower cost** - AI tools charge per submission; our variable substitution is free
3. **Faster feedback** - No AI processing time; instant template rendering
4. **Academic integrity** - Grade penalties should use consistent, pre-approved language, not AI-generated text

## Implementation Notes

### Canvas API Constraints

Based on research, the Canvas API has the following constraints that affect feature design:

1. **Comment Posting Endpoint:**
   - **Method:** `PUT /api/v1/courses/:course_id/assignments/:assignment_id/submissions/:user_id`
   - **Parameters:** `comment[text_comment]` (string), `comment[group_comment]` (boolean, default: false)
   - **Python canvasapi:** `submission.edit(comment={'text_comment': 'Your comment here'})`

2. **Rate Limiting (Critical for Bulk Posting):**
   - **Mechanism:** Leaky bucket algorithm with dynamic throttling
   - **Error Response:** 429 Forbidden (Rate Limit Exceeded)
   - **Headers:** `X-Request-Cost` (quota deducted), `X-Rate-Limit-Remaining` (quota left)
   - **Best Practice:** Sequential requests with 250ms delay for submissions (per Canvas community)
   - **Throttling Trigger:** Parallel requests or rapid sequential requests
   - **Safe Rate:** ~700 requests/hour/token (community observation, not official limit)

3. **Comment Editing/Deletion:**
   - **Edit:** `PUT /api/v1/courses/:course_id/assignments/:assignment_id/submissions/:user_id/comments/:id`
   - **Delete:** `DELETE /api/v1/courses/:course_id/assignments/:assignment_id/submissions/:user_id/comments/:id`
   - **Use Case:** Supports "Undo Recently Posted" feature

4. **No Native Duplicate Prevention:**
   - Canvas API does not prevent duplicate comments
   - Must track posted comments client-side (SQLite table)

5. **No Dry Run Mode:**
   - Canvas API has no "preview" or "test" parameter for comment posting
   - Must implement test mode by posting to separate test course

### Testing Strategy

Based on Canvas community research, testing should use:

1. **Test Course with Test Students:**
   - Canvas Student View creates a "Test Student" but has limitations (no groups, no peer review)
   - Better approach: Create a separate sandbox/test course with multiple fake students
   - Test mode toggle in Settings points to test course ID

2. **Manual Verification:**
   - After posting to test course, manually check SpeedGrader to verify comments appear correctly
   - Verify variable substitution is correct for each test student

3. **SQLite Duplicate Detection Testing:**
   - Post same comment twice to test course; second attempt should show warning
   - Verify `posted_comments` table tracks correctly

## Sources

### HIGH Confidence (Official Documentation & Context7)

- [Canvas LMS REST API - Submission Comments](https://canvas.instructure.com/doc/api/submission_comments.html)
- [Canvas LMS REST API - Submissions](https://www.canvas.instructure.com/doc/api/submissions.html)
- [Canvas API Throttling Documentation](https://canvas.instructure.com/doc/api/file.throttling.html)
- [canvasapi Python Library Documentation - Context7 Verified](/ucfopen/canvasapi)
- [Canvas LMS API - Context7 Verified](/websites/canvas_instructure_doc_api)

### MEDIUM Confidence (Community Best Practices)

- [Canvas Community: Add comments via Python API](https://community.canvaslms.com/t5/Canvas-Developers-Group/Add-comments-text-via-Python-API/m-p/133923)
- [Canvas Community: API Rate Limiting Discussion](https://community.canvaslms.com/t5/Developers-Group/API-Rate-Limiting/m-p/211140)
- [Canvas SpeedGrader Comment Library Feature](https://community.instructure.com/en/kb/articles/661177-how-do-i-use-the-comment-library-in-speedgrader)
- [Canvas Test Student Documentation](https://community.canvaslms.com/t5/Instructor-Guide/How-do-I-view-a-course-as-a-test-student-using-Student-View/ta-p/1122)
- [TimelyGrader AI-Assisted Grading with Canvas](https://www.instructure.com/resources/blog/ai-assisted-grading-scale-enabled-canvas-lms)

### Research Methodology

1. **Canvas API Documentation (Context7):** Verified submission comment parameters, rate limiting mechanism
2. **Canvas Community Forums:** Best practices for rate limiting (250ms delay for submissions), test student usage
3. **Competitor Analysis:** Canvas SpeedGrader Comment Library (static templates), TimelyGrader (AI grading)
4. **Existing Project Context:** Late days tracking data structure, Jupyter notebook workflow, two-template design

---
*Feature research for: Canvas Comment Posting Automation*
*Researched: 2026-02-15*
