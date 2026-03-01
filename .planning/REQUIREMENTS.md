# Requirements: Canvas TA Dashboard - Unified Data Refresh

**Defined:** 2026-02-28
**Core Value:** Safely and efficiently post accurate late day feedback to student submissions, preventing manual errors and saving TA time while ensuring students receive timely, consistent communication about their late day status.

## v1.1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Sync

- [ ] **SYNC-01**: Header "Refresh Data" button triggers Canvas data sync and shows loading state while running
- [ ] **SYNC-02**: Header displays last synced timestamp after any sync completes, visible from all pages
- [ ] **SYNC-03**: After sync completes, all dashboard pages automatically reload their data without requiring a manual page refresh

### Cleanup

- [x] **CLEAN-01**: Settings "Sync Now" button removed (sync triggered only from header)
- [x] **CLEAN-02**: Settings "Save & Sync Now" button replaced with "Save Settings" only (saves config without triggering sync)
- [ ] **CLEAN-03**: EnhancedTADashboard "Refresh" button and page-level "Last Updated" timestamp removed
- [ ] **CLEAN-04**: EnrollmentTracking "Refresh" button and page-level "Last updated" / "Load time" display removed
- [ ] **CLEAN-05**: LateDaysTracking page-level load indicator (⚡ Loaded in Xs) and cached timestamp (🕒 Cached: time) removed

## Future Requirements

None identified at this time.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Auto-refresh on a timer | Manual trigger only — sync is user-initiated by design |
| Per-page refresh buttons | Replacing all with global header button is the goal |
| PeerReview "Refresh" button removal | Peer review analysis is parameterized and independent of Canvas sync — kept intentionally |
| Backend sync scheduling | No background jobs per existing constraints |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SYNC-01 | Phase 4 | Pending |
| SYNC-02 | Phase 4 | Pending |
| SYNC-03 | Phase 4 | Pending |
| CLEAN-01 | Phase 4 | Complete |
| CLEAN-02 | Phase 4 | Complete |
| CLEAN-03 | Phase 4 | Pending |
| CLEAN-04 | Phase 4 | Pending |
| CLEAN-05 | Phase 4 | Pending |

**Coverage:**
- v1.1 requirements: 8 total
- Mapped to phases: 8
- Unmapped: 0

---
*Requirements defined: 2026-02-28*
*Last updated: 2026-02-28 after roadmap creation*
