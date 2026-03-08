# Design: Fix SQLite Lock During Canvas Sync

**Date:** 2026-03-03
**Status:** Approved

## Problem

The Canvas sync (`sync_course_data()`) holds a single write transaction open for the entire duration of the sync — up to 5 minutes. During this time, Canvas API network calls (one per assignment for submissions) happen *inside* the transaction, keeping the write lock held for the full sync duration.

Any concurrent write to the database — such as saving settings on the Settings page — times out after 5 seconds (SQLite default) and fails. The failure is currently silent: the UI shows a success banner while the backend logs `database is locked`.

## Root Cause

```python
# canvas_sync.py — current (broken)
with db.get_db_transaction() as conn:          # write lock acquired here
    db.clear_refreshable_data(course_id, conn)
    db.upsert_assignments(...)
    for assignment_obj in assignment_objects:
        for submission in assignment_obj.get_submissions():  # ← network I/O inside lock
            ...
        db.upsert_submissions(...)             # ← write inside lock
# lock released here — 5 minutes later
```

WAL mode is already enabled (concurrent reads work), but SQLite still serializes writes. Settings saves (`PUT /api/settings`) are writes, so they block until the sync transaction commits or the 5-second timeout fires.

## Solution: Fetch-First, Write-Atomic

Separate the sync into two phases:

1. **Phase 1 — Fetch** (~4:50 of 5 min): Collect all Canvas API data into memory. No database connection open. Settings writes are completely unblocked.
2. **Phase 2 — Write** (~5–10 seconds): Open a single short write transaction. Write all in-memory data atomically. Full rollback on any error.

### Proposed Flow

```
sync_course_data()
  ├─ PHASE 1: Fetch (no DB connection)  ── 0 seconds of lock time
  │    ├─ fetch assignment_groups → memory
  │    ├─ fetch assignments → memory
  │    ├─ fetch users → memory
  │    ├─ fetch groups → memory
  │    └─ for each assignment:
  │         └─ fetch submissions → all_submissions list (memory)
  │
  └─ PHASE 2: Write (short transaction) ── ~5–10 seconds of lock time
       ├─ snapshot enrollment state
       ├─ mark users pending
       ├─ clear refreshable data
       ├─ upsert assignment_groups, assignments, users, groups
       ├─ upsert all_submissions (bulk)
       └─ commit (rollback on any error — atomicity preserved)
```

### Memory Impact

A large course (50 assignments × 400 students) = ~20,000 submission dicts × ~200 bytes ≈ **~4 MB**. Acceptable for a local deployment.

## Concurrency Behavior After Fix

| Timing | Settings save behavior |
|--------|----------------------|
| During Phase 1 (fetch, ~5 min) | ✅ Instant success — no DB lock held |
| During Phase 2 (write, ~10 sec) | ⏳ Brief wait, then succeeds |
| Rare worst case | ❌ Visible error shown in UI (not silent) |

## Files Changed

| File | Change |
|------|--------|
| `canvas_sync.py` | Restructure `sync_course_data()`: collect all submissions into memory list before opening `get_db_transaction()` |
| `database.py` | Add `timeout=30` to `sqlite3.connect()` in `get_db_connection()` |
| `canvas-react/src/Settings.jsx` | Check HTTP response status on all save calls; show error banner on non-2xx |

## Constraints

- Atomicity preserved: write transaction is all-or-nothing, same as today
- No schema changes
- No new dependencies
- Sync duration unchanged (~5 min) — only the lock window shrinks
