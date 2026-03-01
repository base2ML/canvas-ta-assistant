# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

---

## Milestone: v1.1 — Unified Data Refresh

**Shipped:** 2026-03-01
**Phases:** 1 (Phase 4) | **Plans:** 3 | **Quick Tasks:** 5

### What Was Built
- App-level `refreshTrigger` integer counter and `lastSyncedAt` timestamp state — global sync signal pattern
- Persistent "Synced: [time]" display in sticky header, visible from all pages
- `refreshTrigger` prop threaded to EnhancedTADashboard, LateDaysTracking, EnrollmentTracking — each re-fetches on increment
- Settings sync buttons (Sync Now, Save & Sync Now) removed — Settings is now pure config + read-only history
- Per-page Refresh buttons and local timestamps removed from all three dashboard pages
- Quick task cleanup: course propagation, term info in dropdowns, sync timestamp accuracy, enrollment line chart, duplicate subtitle removal

### What Worked
- **Wave-based parallel execution** — Plans 04-01 and 04-02 ran concurrently since they target different files (App.jsx vs Settings.jsx). Clean separation made parallelization safe and fast.
- **Integer counter pattern for refresh signal** — Using `setRefreshTrigger(prev => prev + 1)` instead of a boolean flag correctly handles every sync event, including consecutive syncs to the same state.
- **Prop threading instead of context** — Passing `refreshTrigger` and `activeCourseId` as route element props keeps data flow explicit and avoids unnecessary Context complexity for a small component tree.
- **Best-effort inner try/catch** — Silent failure on `GET /api/canvas/sync/status` pre-population means the page renders fine even if the backend is temporarily unavailable.
- **Phase 4 as clean integration layer** — All v1.1 requirements were self-contained in Phase 4 because they reorganized existing infrastructure without adding new backend endpoints. Verification was straightforward.

### What Was Inefficient
- **Background agent Bash permissions** — The 04-03 executor failed in background mode because it couldn't get Bash access for commits. Re-spawning in foreground fixed it but added a round-trip. Consider running executors in foreground when the task requires interactive permission grants.
- **CLI archived but didn't delete REQUIREMENTS.md** — The `milestone complete` CLI archived requirements but left the original; manual deletion was required. The workflow should make this explicit.
- **ROADMAP.md not auto-reorganized by CLI** — The `milestone complete` CLI archived but didn't collapse the completed milestone section into `<details>`. Manual rewrite was needed.

### Patterns Established
- **Global state as props, not context** — For a 3-4 page app, pass `activeCourseId`, `refreshTrigger`, `lastSyncedAt` as route element props. Clean, traceable, no Provider boilerplate.
- **Integer counter as event signal** — `refreshTrigger: number` in useEffect deps fires on every increment, not just value changes. More reliable than boolean toggle or timestamp comparison.
- **Course-comparison guard removal** — If a useEffect already has `refreshTrigger` in deps, removing the `prevCourse !== course` early-return guard is correct — the whole point is unconditional reload.
- **Settings as read-only display** — After v1.1, Settings page: saves config, displays sync history. No sync triggers. All sync goes through global header.

### Key Lessons
1. **Parallelize plans that touch different files** — Wave 1 (App.jsx + Settings.jsx) ran clean in parallel because there was zero file overlap. Always check `files_modified` in plan frontmatter before deciding wave grouping.
2. **Background executor needs Bash pre-authorized** — For CI-style automation, either run executors in foreground or pre-authorize Bash in settings. The permission prompt can't appear in background mode.
3. **Audit before complete-milestone saves time** — Running `/gsd:audit-milestone` first confirmed all 8 requirements satisfied before the ceremony, making `complete-milestone` a fast archive operation rather than a debugging session.

### Cost Observations
- Model mix: ~100% sonnet (balanced profile)
- Sessions: 1
- Notable: All 3 phase plans executed in ~30 minutes total; quick tasks averaged under 2 minutes each

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | multiple | 3 | Initial build — foundation, posting logic, UI integration |
| v1.1 | 1 | 1 | Cleanup/integration milestone — wave parallelization, audit-first ceremony |

### Top Lessons (Verified Across Milestones)

1. **Prop threading scales well for small apps** — Both v1.0 and v1.1 passed course/refresh state as props without needing Context. Pattern holds up to ~5 pages.
2. **Safety gates pay off** — The multi-layer safety system (test mode + confirmation + dry run) from v1.0 prevented any accidental Canvas API posts during v1.1 development.
