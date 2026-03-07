# Quick Task 8: Review late day comment template variable calculations - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Task Boundary

Fix overlapping and incorrect variable calculations in late day comment templates. Establish a clean, non-redundant variable set and fix `bank_days_used` to be cumulative.

</domain>

<decisions>
## Implementation Decisions

### bank_days_used semantics
- Change `bank_days_used` to mean **cumulative** bank days used across ALL assignments so far including this one
- Calculation: `total_bank - bank_remaining` (not the per-assignment draw)
- This applies to both variable_data construction sites in main.py (single-post and bulk-post flows)

### Redundant aliases
- Remove `days_remaining` (alias for `bank_remaining`) from ALLOWED_TEMPLATE_VARIABLES
- Remove `max_late_days` (alias for `per_assignment_cap`) from ALLOWED_TEMPLATE_VARIABLES
- No backward compatibility needed — templates should be updated to use canonical names

### Final clean variable set
- `days_late` — days late for this specific assignment
- `bank_days_used` — cumulative bank days used across all assignments so far (including this one)
- `penalty_days` — penalty days on the current assignment
- `penalty_percent` — penalty percentage on the current assignment
- `bank_remaining` — bank days remaining after this assignment
- `total_bank` — total configured bank size

### Default templates
- Update default templates in database.py to use canonical variables only
- Penalty template: use `bank_days_used` (cumulative) and `bank_remaining` instead of `days_remaining`/`max_late_days`
- Non-penalty template: use `bank_remaining` instead of `days_remaining`, remove `max_late_days`

### Settings.jsx
- Update the displayed Available Variables list to show only the 6 canonical variables

### Claude's Discretion
- How to handle existing saved templates in the DB that reference removed variables (days_remaining, max_late_days): since backward compat is not required, the render will fail gracefully with an error for templates using removed variables — no migration needed at DB level, but the default templates are rewritten
- populate_default_templates only runs when the table is empty, so existing deployments will keep old default templates — acceptable, user can reset

</decisions>

<specifics>
## Specific Ideas

- Two `variable_data` construction sites in main.py to update (around line 1029-1040 and 1265-1276)
- `ALLOWED_TEMPLATE_VARIABLES` set around line 287-298
- Default templates in `database.py` `populate_default_templates()` around line 358-416
- Settings.jsx available variables display around line 646

</specifics>
