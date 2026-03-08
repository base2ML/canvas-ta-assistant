# SQLite Lock During Sync — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow settings saves (and other writes) to work freely during Canvas sync by moving all Canvas API network calls before the database write transaction.

**Architecture:** Two-phase sync — Phase 1 fetches everything from Canvas into memory (no DB lock), Phase 2 writes atomically in a short transaction (~5–10 sec lock vs current ~5 min). Also increases connection timeout to 30s and stops auto-dismissing error messages.

**Tech Stack:** Python sqlite3, FastAPI, React 19.1.1

---

### Task 1: Increase SQLite connection timeout

**Files:**
- Modify: `database.py:27`

**Step 1: Change the connect call**

In `database.py`, line 27, change:
```python
conn = sqlite3.connect(DB_PATH)
```
to:
```python
conn = sqlite3.connect(DB_PATH, timeout=30)
```

**Step 2: Verify the change**

Run:
```bash
grep -n "sqlite3.connect" database.py
```
Expected: `conn = sqlite3.connect(DB_PATH, timeout=30)` on line 27.

**Step 3: Run backend tests**

Run from project root:
```bash
uv run pytest tests/ -x -q 2>&1 | tail -20
```
Expected: all tests pass.

**Step 4: Commit**

```bash
git add database.py
git commit -m "fix: increase SQLite connection timeout to 30s for concurrent write safety"
```

---

### Task 2: Fetch-first sync restructure in canvas_sync.py

**Files:**
- Modify: `canvas_sync.py:345-493`

This is the core fix. The current code fetches Canvas submissions and peer reviews *inside* `get_db_transaction()`, holding the write lock during all that network I/O. The fix moves both fetch loops before the transaction.

**Step 1: Read the current structure**

Read `canvas_sync.py` lines 345–500 to confirm the current layout before editing.

**Step 2: Move submission fetching before the transaction**

Find this block (currently inside `with db.get_db_transaction() as conn:`, around lines 366–392):

```python
        # Fetch and store submissions per-assignment to reduce memory usage
        submissions_start = time.time()
        for assignment_obj in assignment_objects:
            assignment_submissions = []
            for submission in assignment_obj.get_submissions(
                include=["submission_history"]
            ):
                assignment_submissions.append(
                    {
                        "id": submission.id,
                        "user_id": submission.user_id,
                        "assignment_id": assignment_obj.id,
                        "submitted_at": getattr(submission, "submitted_at", None),
                        "workflow_state": submission.workflow_state,
                        "late": getattr(submission, "late", False),
                        "score": getattr(submission, "score", None),
                    }
                )

            # Write submissions for this assignment
            if assignment_submissions:
                db.upsert_submissions(course_id, assignment_submissions, conn)
                total_submissions += len(assignment_submissions)

        logger.info(
            f"Submissions fetched and stored in {time.time() - submissions_start:.2f}s ({total_submissions} submissions)"  # noqa: E501
        )
```

Delete this block from inside the transaction. Replace it with a fetch-only version **before** the `with db.get_db_transaction() as conn:` line:

```python
        # PHASE 1b: Fetch submissions (outside transaction — no DB lock during network I/O)
        submissions_start = time.time()
        all_submissions: list[dict[str, Any]] = []
        for assignment_obj in assignment_objects:
            for submission in assignment_obj.get_submissions(
                include=["submission_history"]
            ):
                all_submissions.append(
                    {
                        "id": submission.id,
                        "user_id": submission.user_id,
                        "assignment_id": assignment_obj.id,
                        "submitted_at": getattr(submission, "submitted_at", None),
                        "workflow_state": submission.workflow_state,
                        "late": getattr(submission, "late", False),
                        "score": getattr(submission, "score", None),
                    }
                )
        logger.info(
            f"Submissions fetched in {time.time() - submissions_start:.2f}s "
            f"({len(all_submissions)} submissions)"
        )
```

**Step 3: Move peer review fetching before the transaction**

Find this block (currently inside the transaction, around lines 394–461):

```python
        # Fetch and store peer reviews for assignments that have them
        peer_reviews_start = time.time()
        total_peer_reviews = 0
        total_peer_review_comments = 0

        peer_review_assignments = [
            (obj, data)
            for obj, data in zip(assignment_objects, assignments, strict=True)
            if data.get("has_peer_reviews", False)
        ]

        if peer_review_assignments:
            logger.info(
                f"Found {len(peer_review_assignments)} assignments "
                "with peer reviews"
            )

            for assignment_obj, assignment_data in peer_review_assignments:
                try:
                    # Fetch peer reviews
                    peer_reviews = []
                    for pr in assignment_obj.get_peer_reviews():
                        peer_reviews.append(
                            {
                                "id": pr.id,
                                "assignment_id": assignment_obj.id,
                                "user_id": pr.user_id,
                                "assessor_id": pr.assessor_id,
                                "asset_id": getattr(pr, "asset_id", None),
                                "asset_type": getattr(pr, "asset_type", None),
                                "workflow_state": getattr(
                                    pr, "workflow_state", None
                                ),
                            }
                        )

                    if peer_reviews:
                        db.upsert_peer_reviews(course_id, peer_reviews, conn)
                        total_peer_reviews += len(peer_reviews)

                    # Fetch submission comments for peer reviews
                    comments = []
                    for submission in assignment_obj.get_submissions(
                        include=["submission_comments"]
                    ):
                        submission_comments = getattr(
                            submission, "submission_comments", []
                        )
                        for comment in submission_comments:
                            comments.append(
                                {
                                    "id": comment.get("id"),
                                    "submission_id": submission.id,
                                    "author_id": comment.get("author_id"),
                                    "comment": comment.get("comment"),
                                    "created_at": comment.get("created_at"),
                                }
                            )

                    if comments:
                        db.upsert_peer_review_comments(course_id, comments, conn)
                        total_peer_review_comments += len(comments)

                except Exception as e:
                    logger.warning(
                        f"Failed to fetch peer reviews for assignment {assignment_data['name']}: {e}"  # noqa: E501
                    )
                    continue

            logger.info(
                f"Peer reviews fetched in {time.time() - peer_reviews_start:.2f}s "
                f"({total_peer_reviews} reviews, {total_peer_review_comments} comments)"  # noqa: E501
            )
```

Delete this block from inside the transaction. Replace it **before** the `with db.get_db_transaction() as conn:` line (after the submissions fetch you added in Step 2):

```python
        # PHASE 1c: Fetch peer reviews (outside transaction — no DB lock during network I/O)
        peer_reviews_start = time.time()
        all_peer_reviews: list[dict[str, Any]] = []
        all_peer_review_comments: list[dict[str, Any]] = []

        peer_review_assignments = [
            (obj, data)
            for obj, data in zip(assignment_objects, assignments, strict=True)
            if data.get("has_peer_reviews", False)
        ]

        if peer_review_assignments:
            logger.info(
                f"Found {len(peer_review_assignments)} assignments with peer reviews"
            )
            for assignment_obj, assignment_data in peer_review_assignments:
                try:
                    for pr in assignment_obj.get_peer_reviews():
                        all_peer_reviews.append(
                            {
                                "id": pr.id,
                                "assignment_id": assignment_obj.id,
                                "user_id": pr.user_id,
                                "assessor_id": pr.assessor_id,
                                "asset_id": getattr(pr, "asset_id", None),
                                "asset_type": getattr(pr, "asset_type", None),
                                "workflow_state": getattr(pr, "workflow_state", None),
                            }
                        )
                    for submission in assignment_obj.get_submissions(
                        include=["submission_comments"]
                    ):
                        for comment in getattr(submission, "submission_comments", []):
                            all_peer_review_comments.append(
                                {
                                    "id": comment.get("id"),
                                    "submission_id": submission.id,
                                    "author_id": comment.get("author_id"),
                                    "comment": comment.get("comment"),
                                    "created_at": comment.get("created_at"),
                                }
                            )
                except Exception as e:
                    logger.warning(
                        f"Failed to fetch peer reviews for assignment {assignment_data['name']}: {e}"  # noqa: E501
                    )
                    continue

        logger.info(
            f"Peer reviews fetched in {time.time() - peer_reviews_start:.2f}s "
            f"({len(all_peer_reviews)} reviews, {len(all_peer_review_comments)} comments)"
        )
```

**Step 4: Update the write transaction to use pre-fetched data**

Inside `with db.get_db_transaction() as conn:`, in the position where the old submission loop was, add the write calls using the pre-fetched lists:

```python
            # Write pre-fetched submissions (all Canvas API calls already done above)
            if all_submissions:
                db.upsert_submissions(course_id, all_submissions, conn)
            total_submissions = len(all_submissions)
            logger.info(f"Wrote {total_submissions} submissions to DB")

            # Write pre-fetched peer reviews
            total_peer_reviews = 0
            total_peer_review_comments = 0
            if all_peer_reviews:
                db.upsert_peer_reviews(course_id, all_peer_reviews, conn)
                total_peer_reviews = len(all_peer_reviews)
            if all_peer_review_comments:
                db.upsert_peer_review_comments(course_id, all_peer_review_comments, conn)
                total_peer_review_comments = len(all_peer_review_comments)
            if all_peer_reviews:
                logger.info(
                    f"Wrote {total_peer_reviews} peer reviews, "
                    f"{total_peer_review_comments} comments to DB"
                )
```

Also remove the `total_submissions = 0` and `dropped_count = 0` initializers from just before the `with db.get_db_transaction()` line (they'll be set inside the transaction now). Keep `dropped_count = 0` since it's set by `mark_dropped_users` inside the transaction.

**Step 5: Add a comment marking the phase boundary**

Just before `with db.get_db_transaction() as conn:`, add:

```python
        # PHASE 2: Write all fetched data atomically (DB lock held ~5–10 seconds)
        dropped_count = 0
```

**Step 6: Verify with ruff**

```bash
uv run ruff check canvas_sync.py && uv run ruff format canvas_sync.py
```
Expected: no errors (or only fixable whitespace).

**Step 7: Run backend tests**

```bash
uv run pytest tests/ -x -q 2>&1 | tail -20
```
Expected: all tests pass.

**Step 8: Commit**

```bash
git add canvas_sync.py
git commit -m "fix: move Canvas API fetch calls before DB transaction to eliminate 5-min write lock"
```

---

### Task 3: Stop auto-dismissing error messages in Settings.jsx

**Files:**
- Modify: `canvas-react/src/Settings.jsx:209-231`

The three `useEffect` hooks that clear messages after 5 seconds dismiss both success AND error messages. Error messages should persist until the user acknowledges them — otherwise a failed save appears to silently succeed.

**Step 1: Read the current auto-dismiss effects**

Read `canvas_sync.py` lines 209–232. You'll see three effects like:

```javascript
useEffect(() => {
    if (message) {
        const timer = setTimeout(() => setMessage(null), 5000);
        return () => clearTimeout(timer);
    }
}, [message]);
```

**Step 2: Update all three effects to only auto-dismiss success messages**

Change each of the three effects (for `message`, `templateMessage`, `policyMessage`) to:

```javascript
// Auto-dismiss success messages after 5 seconds; errors persist until user acts
useEffect(() => {
    if (message?.type === 'success') {
        const timer = setTimeout(() => setMessage(null), 5000);
        return () => clearTimeout(timer);
    }
}, [message]);

// ... same pattern for templateMessage and policyMessage
useEffect(() => {
    if (templateMessage?.type === 'success') {
        const timer = setTimeout(() => setTemplateMessage(null), 5000);
        return () => clearTimeout(timer);
    }
}, [templateMessage]);

useEffect(() => {
    if (policyMessage?.type === 'success') {
        const timer = setTimeout(() => setPolicyMessage(null), 5000);
        return () => clearTimeout(timer);
    }
}, [policyMessage]);
```

**Step 3: Verify linting**

```bash
cd canvas-react && npm run lint 2>&1 | tail -10
```
Expected: no errors.

**Step 4: Commit**

```bash
git add canvas-react/src/Settings.jsx
git commit -m "fix: persist error messages in Settings — only auto-dismiss success toasts"
```

---

### Task 4: Rebuild and smoke-test

**Step 1: Rebuild backend container**

```bash
docker-compose up -d --build backend
```

**Step 2: Verify backend logs show phase separation**

```bash
docker-compose logs backend --tail=30 2>&1 | grep -E "fetch|Submissions|Peer|transaction|lock"
```
Expected: logs show "Submissions fetched in X.Xs" BEFORE "Wrote N submissions to DB", confirming fetch-first ordering.

**Step 3: Rebuild frontend container**

```bash
docker-compose up -d --build frontend
```

**Step 4: Manual smoke test**

1. Trigger a sync (Settings → Sync Now)
2. Immediately navigate to Settings → Late Day Policy section
3. Uncheck a group and click "Save Policy Settings"
4. Expected: green success banner appears — no "database is locked" in docker logs
5. If a save fails: a **persistent** red error banner appears (does not auto-dismiss)

**Step 5: Commit smoke test confirmation**

No code changes — this step is verification only.
