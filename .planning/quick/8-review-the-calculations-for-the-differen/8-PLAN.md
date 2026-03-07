---
phase: quick-8
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - main.py
  - database.py
  - canvas-react/src/Settings.jsx
autonomous: true
requirements: [QUICK-8]
must_haves:
  truths:
    - "bank_days_used in templates reflects cumulative days drawn across all assignments so far, not just the per-assignment draw"
    - "Templates only offer the 6 canonical variables; days_remaining and max_late_days are not surfaced"
    - "Default comment templates use canonical variable names only"
    - "Settings Available Variables list shows exactly the 6 canonical variables"
  artifacts:
    - path: "main.py"
      provides: "Fixed ALLOWED_TEMPLATE_VARIABLES, fixed variable_data dicts at both post sites, fixed bank_days_used stored in calculate_student_late_day_summary"
      contains: "bank_days_used.*total_bank.*bank_remaining"
    - path: "database.py"
      provides: "Updated populate_default_templates with canonical variable names"
    - path: "canvas-react/src/Settings.jsx"
      provides: "Available Variables list with 6 canonical entries only"
  key_links:
    - from: "main.py calculate_student_late_day_summary()"
      to: "variable_data dicts in post endpoints"
      via: "bank_days_used = total_bank - bank_remaining stored in result dict"
---

<objective>
Fix `bank_days_used` to be cumulative (total drawn from bank across all assignments including current), remove the redundant alias variables `days_remaining` and `max_late_days` from the allowed variable set and from both `variable_data` construction sites, update default comment templates in database.py to use canonical names, and trim the Settings.jsx Available Variables list to the 6 canonical variables.

Purpose: Templates currently expose confusing, overlapping variable names. After this fix the variable set is clean, consistent, and cumulative semantics are correct.
Output: Updated main.py, database.py, Settings.jsx.
</objective>

<execution_context>
@/Users/mapajr/.claude/get-shit-done/workflows/execute-plan.md
@/Users/mapajr/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md

<interfaces>
<!-- Key code locations. Executor should edit these directly — no exploration needed. -->

From main.py line 287-298 (ALLOWED_TEMPLATE_VARIABLES):
```python
ALLOWED_TEMPLATE_VARIABLES = {
    # Existing (kept for backward compatibility with saved templates)
    "days_late",
    "days_remaining",  # alias for bank_remaining   <-- REMOVE
    "penalty_days",
    "penalty_percent",
    "max_late_days",  # alias for per_assignment_cap  <-- REMOVE
    # New bank system variables
    "bank_days_used",
    "bank_remaining",
    "total_bank",
}
```

From main.py line 554 — current per-assignment calculation (inside calculate_student_late_day_summary):
```python
bank_days_used = min(applicable_late_days, bank_remaining)
penalty_days = days_late - bank_days_used
penalty_percent = min(penalty_days * penalty_rate_per_day, 100)
bank_remaining -= bank_days_used

result[assignment_id] = {
    "days_late": days_late,
    "bank_days_used": bank_days_used,   # <-- currently per-assignment draw
    ...
}
```
Fix: after `bank_remaining -= bank_days_used`, compute cumulative:
```python
cumulative_bank_used = total_bank - bank_remaining
result[assignment_id] = {
    ...
    "bank_days_used": cumulative_bank_used,   # cumulative
    ...
}
```
Also apply same fix to the not_accepted branch (line ~541) and the zero-late branch (line ~528) — those already set bank_days_used=0 but need to emit the cumulative value at that point in the loop (i.e., `total_bank - bank_remaining` which will equal whatever is accumulated so far before this assignment's draw, since bank is unchanged for these branches).

From main.py lines 1029-1040 (single-post variable_data):
```python
variable_data = {
    "days_late": entry.get("days_late", 0),
    "bank_days_used": entry.get("bank_days_used", 0),
    "bank_remaining": entry.get("bank_remaining", total_bank),
    "penalty_days": entry.get("penalty_days", 0),
    "penalty_percent": entry.get("penalty_percent", 0),
    "not_accepted": entry.get("not_accepted", False),
    "total_bank": total_bank,
    # Backward-compat aliases for existing templates
    "days_remaining": entry.get("bank_remaining", total_bank),   # <-- REMOVE
    "max_late_days": per_cap,                                     # <-- REMOVE
}
```

From main.py lines 1265-1276 (bulk-post SSE variable_data):
```python
late_days_data = {
    "days_late": entry.get("days_late", 0),
    "bank_days_used": entry.get("bank_days_used", 0),
    "bank_remaining": entry.get("bank_remaining", total_bank),
    "penalty_days": entry.get("penalty_days", 0),
    "penalty_percent": entry.get("penalty_percent", 0),
    "not_accepted": entry.get("not_accepted", False),
    "total_bank": total_bank,
    # Backward-compat aliases
    "days_remaining": entry.get("bank_remaining", total_bank),   # <-- REMOVE
    "max_late_days": per_cap,                                     # <-- REMOVE
}
```

From database.py lines 366-401 (populate_default_templates) — replace templates:
- penalty template: replace `days_remaining` → `bank_remaining`, `max_late_days` → remove that line, add `bank_days_used` line showing cumulative used
- non_penalty template: replace `days_remaining` → `bank_remaining`, remove `max_late_days` line
- Update template_variables JSON arrays to use canonical names only

From Settings.jsx line 646:
```jsx
{['{days_late}', '{bank_days_used}', '{bank_remaining}', '{total_bank}', '{penalty_days}', '{penalty_percent}', '{days_remaining}', '{max_late_days}'].map(v => (
```
Fix: remove `'{days_remaining}'` and `'{max_late_days}'` from the array.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix bank_days_used to cumulative and remove alias variables from main.py</name>
  <files>main.py</files>
  <action>
Make three changes in main.py:

**Change 1 — ALLOWED_TEMPLATE_VARIABLES (line ~287):**
Remove `"days_remaining"` and `"max_late_days"` entries (including their comments). The final set should contain exactly: `days_late`, `penalty_days`, `penalty_percent`, `bank_days_used`, `bank_remaining`, `total_bank`.

**Change 2 — calculate_student_late_day_summary() (line ~527-563):**
In ALL three result dict assignments within the loop body, replace the literal `"bank_days_used": ...` value with `total_bank - bank_remaining` (the cumulative amount drawn):

- Zero-late branch (days_late == 0): `"bank_days_used": total_bank - bank_remaining` — bank_remaining is unchanged at this point, so this correctly reflects cumulative drawn before this assignment.
- Not-accepted branch: Same — `"bank_days_used": total_bank - bank_remaining` before any draw.
- Bank-eligible branch: After `bank_remaining -= bank_days_used`, set `"bank_days_used": total_bank - bank_remaining`. Rename the local variable to avoid shadowing: use `draw = min(applicable_late_days, bank_remaining)` then `penalty_days = days_late - draw`, `bank_remaining -= draw`, then store `"bank_days_used": total_bank - bank_remaining`.

**Change 3 — Both variable_data / late_days_data dicts (lines ~1029-1040 and ~1265-1276):**
Remove the `"days_remaining": ...` and `"max_late_days": ...` entries (and their comment lines) from both dicts. Do not change any other keys.
  </action>
  <verify>
    <automated>cd /Users/mapajr/git/cda-ta-dashboard && uv run pytest tests/ -x -q 2>&1 | tail -20</automated>
  </verify>
  <done>All tests pass. ALLOWED_TEMPLATE_VARIABLES has 6 entries. Both variable_data dicts have no days_remaining or max_late_days keys. bank_days_used in calculate_student_late_day_summary stores total_bank - bank_remaining.</done>
</task>

<task type="auto">
  <name>Task 2: Update default templates in database.py and Available Variables in Settings.jsx</name>
  <files>database.py, canvas-react/src/Settings.jsx</files>
  <action>
**database.py — populate_default_templates():**

Replace the penalty template text and variables:
```
template_text:
"Late Day Update for this assignment:\n\n"
"Days late: {days_late}\n"
"Bank days used (cumulative): {bank_days_used}\n"
"Bank days remaining: {bank_remaining}\n"
"Penalty days: {penalty_days}\n"
"Penalty: {penalty_percent}%\n\n"
"Please review the course late day policy if you have questions."

template_variables: ["days_late", "bank_days_used", "bank_remaining", "penalty_days", "penalty_percent"]
```

Replace the non_penalty template text and variables:
```
template_text:
"Late Day Update for this assignment:\n\n"
"Days late: {days_late}\n"
"Bank days used (cumulative): {bank_days_used}\n"
"Bank days remaining: {bank_remaining}\n\n"
"No penalty has been applied.\n\n"
"Please review the course late day policy if you have questions."

template_variables: ["days_late", "bank_days_used", "bank_remaining"]
```

**Settings.jsx — Available Variables list (line ~646):**

Change the array from:
```jsx
['{days_late}', '{bank_days_used}', '{bank_remaining}', '{total_bank}', '{penalty_days}', '{penalty_percent}', '{days_remaining}', '{max_late_days}']
```
to:
```jsx
['{days_late}', '{bank_days_used}', '{bank_remaining}', '{total_bank}', '{penalty_days}', '{penalty_percent}']
```

Remove the two alias entries `'{days_remaining}'` and `'{max_late_days}'` only. Preserve all other JSX unchanged.
  </action>
  <verify>
    <automated>cd /Users/mapajr/git/cda-ta-dashboard && grep -c "days_remaining\|max_late_days" database.py canvas-react/src/Settings.jsx && echo "Count above should be 0"</automated>
  </verify>
  <done>database.py populate_default_templates uses only canonical variables. Settings.jsx shows exactly 6 variables. grep for days_remaining and max_late_days returns 0 matches across both files.</done>
</task>

</tasks>

<verification>
```bash
# 1. All tests pass
cd /Users/mapajr/git/cda-ta-dashboard && uv run pytest tests/ -x -q

# 2. No alias variable names remain in any of the three files
grep -n "days_remaining\|max_late_days" main.py database.py canvas-react/src/Settings.jsx

# 3. ALLOWED_TEMPLATE_VARIABLES has exactly 6 members
grep -A 15 "ALLOWED_TEMPLATE_VARIABLES" main.py

# 4. bank_days_used uses cumulative formula in calculate_student_late_day_summary
grep -n "bank_days_used\|total_bank.*bank_remaining" main.py | head -20

# 5. Frontend builds without errors
cd /Users/mapajr/git/cda-ta-dashboard/canvas-react && npm run build 2>&1 | tail -10
```
</verification>

<success_criteria>
- `bank_days_used` in all three result dict sites within `calculate_student_late_day_summary()` equals `total_bank - bank_remaining` (cumulative drawn, not per-assignment draw)
- `ALLOWED_TEMPLATE_VARIABLES` contains exactly 6 entries: days_late, penalty_days, penalty_percent, bank_days_used, bank_remaining, total_bank
- Both `variable_data` and `late_days_data` dicts in the posting endpoints have no `days_remaining` or `max_late_days` keys
- `populate_default_templates()` uses only canonical variable names in template text and variable lists
- Settings.jsx Available Variables shows exactly the 6 canonical `{variable}` tokens
- All existing backend tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/8-review-the-calculations-for-the-differen/8-SUMMARY.md` with what was changed, files modified, and commit hash.
</output>
