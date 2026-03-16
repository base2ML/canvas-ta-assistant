# Phase 8: Add Grade Distribution Visualizations - Research

**Researched:** 2026-03-15
**Domain:** Data visualization (histograms, box plots), statistical computation (Python stdlib), React charting
**Confidence:** HIGH

## Summary

Phase 8 adds a Grade Analysis page that surfaces grade distribution data for instructors and TAs. The backend needs a new `/api/dashboard/grade-distribution/{course_id}` endpoint that computes per-assignment stats (mean, median, stdev, quartiles, histogram bins) and per-TA stats (grader_id join via ta_users) from the existing `submissions` table — no new Canvas sync or schema migration required.

The frontend needs a new `GradeAnalysis.jsx` page component with: an assignment selector dropdown, summary stats cards, a histogram (bar chart), a box-plot visualization, and small-sample warnings (n < 5 graded submissions triggers a caution badge). All of this uses data already in SQLite from phases 5 and 6.

The critical charting decision is whether to add `recharts` as a dependency or build pure SVG components. Given the project's zero external charting dependencies and the straightforward nature of the required charts, **hand-rolled SVG components are the right call** — they avoid a ~400 KB dependency, stay consistent with the Tailwind v4 + Lucide stack, and the histogram and box plot are structurally simple enough that custom SVG is not prohibitively complex.

**Primary recommendation:** Pure SVG histogram and box plot components in React; Python `statistics` stdlib for all backend computations; no new npm packages; no new DB migrations.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `statistics` (stdlib) | 3.11+ | mean, median, stdev, quantiles | Zero deps, ships with Python, `quantiles(data, n=4)` gives Q1/Q2/Q3 directly |
| FastAPI | existing | `/api/dashboard/grade-distribution/{course_id}` endpoint | Already in project |
| React + SVG | 19.1.1 | Histogram bars and box plot rendered as inline SVG | No new dependency |
| Tailwind CSS v4 | existing | Card layout, summary stats, badges | Already in project |
| Lucide React | existing | AlertTriangle icon for small-sample warning | Already in project |
| Vitest + Testing Library | existing | Frontend component tests | Already in project |
| pytest | existing | Backend endpoint tests | Already in project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `math` (stdlib) | 3.11+ | `math.isfinite()` guard on score before statistical computation | Already imported in main.py |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pure SVG histogram | recharts BarChart | recharts 3.8.0 is ~400 KB gzipped; React 19 support is present but required an alpha fix (issue #4558, merged in 2.13.0+). Since histograms are structurally simple (bars with known heights), recharts is overkill here. Use recharts only if the project later needs many chart types. |
| Python `statistics.quantiles` | numpy/scipy | numpy is not in pyproject.toml and is ~20 MB; stdlib is sufficient for this domain (20–300 submissions per assignment) |
| Custom SVG box plot | `react-boxplot` npm | Tiny package but another dependency; the box plot is 5 SVG elements (whiskers, box, median line), well within DIY scope |

**Installation:** No new packages needed for the recommended approach. If recharts is chosen instead:
```bash
# Frontend only — only if recharts approach is taken
cd canvas-react && npm install recharts
```

## Architecture Patterns

### Recommended Project Structure
```
main.py                                  # Add grade-distribution endpoint
canvas-react/src/
├── GradeAnalysis.jsx                    # New top-level page (matches LateDaysTracking.jsx pattern)
├── GradeAnalysis.test.jsx               # Vitest tests
└── components/
    ├── GradeHistogram.jsx               # Pure SVG histogram component
    ├── GradeHistogram.test.jsx
    ├── GradeBoxPlot.jsx                 # Pure SVG box plot component
    └── GradeBoxPlot.test.jsx
tests/
└── test_08_01_grade_distribution.py    # pytest: endpoint + stats computation
```

No new files needed in `database.py` — `get_submissions(course_id)` and `get_assignments(course_id)` already return the needed data. No DB schema changes — `score` and `grader_id` are already columns in `submissions`.

### Pattern 1: Backend Grade Distribution Endpoint

**What:** GET endpoint that reads graded submissions for a course+assignment, computes stats, returns JSON.

**When to use:** Single endpoint handles both "all assignments" summary and "per-assignment detail" via query param.

**Example:**
```python
# Source: follows /api/dashboard/grading-deadlines/{course_id} pattern in main.py
from statistics import mean, median, stdev, quantiles

@app.get("/api/dashboard/grade-distribution/{course_id}")
async def get_grade_distribution(
    course_id: str, assignment_id: int | None = None
) -> dict[str, Any]:
    assignments = db.get_assignments(course_id)
    submissions = db.get_submissions(course_id, assignment_id=assignment_id)

    # Filter to graded submissions with a score
    graded = [s for s in submissions if s.get("workflow_state") == "graded"
              and s.get("score") is not None
              and math.isfinite(float(s["score"]))]

    scores = [float(s["score"]) for s in graded]
    n = len(scores)

    stats: dict[str, Any] = {"n": n, "small_sample": n < 5}
    if n >= 2:
        stats["mean"] = round(mean(scores), 2)
        stats["median"] = round(median(scores), 2)
        stats["stdev"] = round(stdev(scores), 2)
        qs = quantiles(scores, n=4)   # [Q1, Q2, Q3]
        stats["q1"] = round(qs[0], 2)
        stats["q3"] = round(qs[2], 2)
        stats["min"] = round(min(scores), 2)
        stats["max"] = round(max(scores), 2)
    if n == 1:
        stats["mean"] = round(scores[0], 2)
        stats["median"] = round(scores[0], 2)

    # Histogram bins (10 equal-width bins between 0 and points_possible)
    # ...

    # Per-TA stats: group graded submissions by grader_name from JOIN
    # submissions already carry grader_name from get_submissions() LEFT JOIN ta_users
    # ...

    return {"assignment_id": assignment_id, "stats": stats, "histogram": [...], "per_ta": [...]}
```

### Pattern 2: Histogram Binning (Backend)

**What:** Compute fixed-width bins from 0 to `points_possible`; count graded scores per bin.

**When to use:** When `points_possible` is non-null and n >= 2.

```python
# Source: pure Python, no library needed
def compute_histogram_bins(
    scores: list[float], points_possible: float, num_bins: int = 10
) -> list[dict[str, Any]]:
    """Return list of {bin_start, bin_end, count, label} dicts."""
    if not scores or points_possible <= 0:
        return []
    bin_width = points_possible / num_bins
    bins: list[dict[str, Any]] = []
    for i in range(num_bins):
        lo = i * bin_width
        hi = (i + 1) * bin_width
        count = sum(1 for s in scores if lo <= s < hi)
        # Last bin includes the max (closed right)
        if i == num_bins - 1:
            count += sum(1 for s in scores if s == points_possible)
        bins.append({
            "bin_start": round(lo, 1),
            "bin_end": round(hi, 1),
            "count": count,
            "label": f"{lo:.0f}–{hi:.0f}",
        })
    return bins
```

### Pattern 3: Frontend SVG Histogram Component

**What:** Pure SVG bar chart rendered from `histogram` array from the API.

**When to use:** Always — no recharts dependency.

```jsx
// Source: inline SVG React pattern, consistent with project's no-external-chart-library stance
const SVG_W = 480;
const SVG_H = 200;
const PAD = { top: 10, right: 10, bottom: 30, left: 36 };

export default function GradeHistogram({ bins, pointsPossible }) {
  if (!bins || bins.length === 0) return null;
  const maxCount = Math.max(...bins.map(b => b.count), 1);
  const innerW = SVG_W - PAD.left - PAD.right;
  const innerH = SVG_H - PAD.top - PAD.bottom;
  const barW = innerW / bins.length;

  return (
    <svg viewBox={`0 0 ${SVG_W} ${SVG_H}`} className="w-full">
      {bins.map((bin, i) => {
        const barH = (bin.count / maxCount) * innerH;
        const x = PAD.left + i * barW;
        const y = PAD.top + innerH - barH;
        return (
          <g key={i}>
            <rect x={x + 1} y={y} width={barW - 2} height={barH}
              className="fill-blue-400 hover:fill-blue-600" />
            {/* label on x-axis */}
            <text x={x + barW / 2} y={SVG_H - 6} textAnchor="middle"
              fontSize="9" className="fill-gray-500">
              {bin.bin_start}
            </text>
          </g>
        );
      })}
      {/* Y-axis label */}
      <text x={12} y={SVG_H / 2} textAnchor="middle" fontSize="10"
        transform={`rotate(-90, 12, ${SVG_H / 2})`} className="fill-gray-500">
        Count
      </text>
    </svg>
  );
}
```

### Pattern 4: Frontend SVG Box Plot Component

**What:** Horizontal box plot rendered from `stats.min`, `stats.q1`, `stats.median`, `stats.q3`, `stats.max`.

```jsx
// Source: standard Tukey box plot layout in SVG
export default function GradeBoxPlot({ stats, pointsPossible }) {
  if (!stats || stats.n < 2) return null;
  const W = 480, H = 80, PAD_X = 40, Y_MID = 40, BOX_H = 24;
  const scale = (v) => PAD_X + ((v / pointsPossible) * (W - 2 * PAD_X));
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
      {/* Whisker lines */}
      <line x1={scale(stats.min)} y1={Y_MID} x2={scale(stats.q1)} y2={Y_MID}
        stroke="#6b7280" strokeWidth={2} />
      <line x1={scale(stats.q3)} y1={Y_MID} x2={scale(stats.max)} y2={Y_MID}
        stroke="#6b7280" strokeWidth={2} />
      {/* IQR box */}
      <rect x={scale(stats.q1)} y={Y_MID - BOX_H / 2}
        width={scale(stats.q3) - scale(stats.q1)} height={BOX_H}
        className="fill-blue-200 stroke-blue-500" strokeWidth={2} />
      {/* Median line */}
      <line x1={scale(stats.median)} y1={Y_MID - BOX_H / 2}
        x2={scale(stats.median)} y2={Y_MID + BOX_H / 2}
        stroke="#1d4ed8" strokeWidth={3} />
      {/* Whisker caps */}
      <line x1={scale(stats.min)} y1={Y_MID - 8} x2={scale(stats.min)} y2={Y_MID + 8}
        stroke="#6b7280" strokeWidth={2} />
      <line x1={scale(stats.max)} y1={Y_MID - 8} x2={scale(stats.max)} y2={Y_MID + 8}
        stroke="#6b7280" strokeWidth={2} />
    </svg>
  );
}
```

### Pattern 5: Small-Sample Warning

**What:** Backend sets `small_sample: true` when n < 5; frontend renders an `AlertTriangle` badge.

**Threshold rationale:** n < 5 graded submissions is insufficient for meaningful statistical inference (box plot quartiles degenerate with fewer than 4 data points; `statistics.quantiles` requires at least 2 data points). Standard practice in education analytics treats n < 5 as a disclosure risk threshold under FERPA (individual identification possible).

```jsx
// Source: follows existing pattern in GradingScheduleSummary.jsx overdue badge
{data.stats.small_sample && (
  <div className="flex items-center gap-1 px-2 py-1 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-700">
    <AlertTriangle className="h-3 w-3" />
    Small sample (n={data.stats.n}) — statistics may not be reliable
  </div>
)}
```

### Pattern 6: Route and Navigation Integration

**What:** New `/grade-analysis` route in App.jsx and Navigation.jsx link — follows exact same pattern as `/grading-schedule`.

```jsx
// App.jsx addition — follows GradingScheduleSummary route pattern
import GradeAnalysis from './GradeAnalysis';

<Route
  path="/grade-analysis"
  element={
    <GradeAnalysis
      activeCourseId={activeCourseId}
      refreshTrigger={refreshTrigger}
    />
  }
/>
```

```jsx
// Navigation.jsx addition — import BarChart2 from lucide-react
<Link to="/grade-analysis" className={navClass('/grade-analysis')}>
  <BarChart2 className="w-4 h-4 mr-2" />
  Grade Analysis
</Link>
```

### Anti-Patterns to Avoid
- **Adding recharts for a single page:** recharts adds ~400 KB. The histogram and box plot are 5–15 SVG elements each. Custom SVG components are simpler and maintain zero external charting dependencies.
- **Computing stats in the frontend:** All statistical computation (mean, median, stdev, quartiles, bins) must happen in the backend endpoint. The frontend is purely rendering JSON.
- **Fetching all submissions then filtering on frontend:** The endpoint filters to `workflow_state = 'graded'` and non-null `score` server-side. Do not send raw submissions to the frontend.
- **Calling `statistics.stdev()` on n=1:** `stdev()` raises `StatisticsError` on fewer than 2 data points. Guard with `if n >= 2`.
- **Using numpy/scipy:** Not in pyproject.toml. The Python `statistics` stdlib is sufficient for this domain.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Mean, median, stdev | Custom math | `statistics.mean/median/stdev` | Handles edge cases (ties, even-n median), stdlib, no dep |
| Quartiles / IQR | Custom percentile logic | `statistics.quantiles(data, n=4)` | Returns `[Q1, Q2, Q3]` directly, added in Python 3.8 |
| Score validation | Custom float check | `math.isfinite(float(score))` | Guards against `inf`/`nan` from Canvas API |
| Responsive SVG | viewBox + CSS | `viewBox="0 0 W H"` + `className="w-full"` | Native browser scaling, zero JS |

**Key insight:** For this domain (single-course grade distributions, 20–300 scores per assignment), the Python stdlib and inline SVG cover 100% of the requirements without any new dependencies.

## Common Pitfalls

### Pitfall 1: `statistics.stdev()` with n < 2
**What goes wrong:** `StatisticsError: stdev requires at least two data points` raised on assignments graded by only one TA.
**Why it happens:** `stdev` computes sample standard deviation — undefined for a single observation.
**How to avoid:** Guard with `if n >= 2` before calling `stdev`. Return `null` for stdev/quartiles when `n < 2`. Backend sets `small_sample: true` when `n < 5`.
**Warning signs:** 500 errors on assignments early in the semester before most grading is complete.

### Pitfall 2: Box plot renders outside SVG bounds
**What goes wrong:** Score equal to `points_possible` maps beyond the SVG width due to floating point.
**Why it happens:** `scale(max) > W - PAD_X` when max score has floating point imprecision.
**How to avoid:** Clamp: `const scale = (v) => PAD_X + Math.min(1, v / pointsPossible) * (W - 2 * PAD_X)`.

### Pitfall 3: Histogram bins miss the maximum score
**What goes wrong:** A score exactly equal to `points_possible` falls in the half-open `[lo, hi)` interval and misses the last bin.
**Why it happens:** Standard `lo <= s < hi` half-open interval semantics.
**How to avoid:** The last bin uses closed right: `lo <= s <= hi`. Shown in `compute_histogram_bins()` above.

### Pitfall 4: Per-TA stats when `grader_id` is NULL
**What goes wrong:** Submissions graded before Phase 6 sync (or from Canvas courses where grader_id is not exposed) have `grader_id = NULL`. `grader_name` from the LEFT JOIN is also NULL.
**Why it happens:** Phase 6 added `grader_id` via migration — submissions synced before Phase 6 have NULL.
**How to avoid:** Group NULL grader_name submissions under `"Unknown / Pre-Phase 6"` in per-TA stats. Do not exclude them.
**Warning signs:** Per-TA section shows no data despite graded submissions existing.

### Pitfall 5: Assignment selector shows assignments with 0 graded submissions
**What goes wrong:** Frontend assignment dropdown shows every assignment, many with n=0, producing confusing "no data" states.
**Why it happens:** `get_assignments()` returns all assignments regardless of grading state.
**How to avoid:** The endpoint response for each assignment in the "summary" mode should include `graded_count` so the frontend can sort by `graded_count DESC` and visually mark assignments with 0 graded.

### Pitfall 6: `statistics.quantiles` requires n >= 2 (changed in Python 3.13)
**What goes wrong:** On Python 3.11/3.12, `statistics.quantiles([x])` raises `StatisticsError`.
**Why it happens:** Single-element list has no spread. Fixed in Python 3.13 but project targets >= 3.11.
**How to avoid:** Guard with `if n >= 2` before calling `quantiles`. Return `None` for quartiles when n < 2.

## Code Examples

Verified patterns from official sources:

### Python statistics.quantiles (stdlib, Python 3.11+)
```python
# Source: https://docs.python.org/3/library/statistics.html
from statistics import mean, median, stdev, quantiles

scores = [72.0, 85.5, 91.0, 68.0, 77.5, 88.0, 95.0, 60.0]
q1, q2, q3 = quantiles(scores, n=4)   # returns [Q1, Q2, Q3]
iqr = q3 - q1
# stdev requires n >= 2
if len(scores) >= 2:
    sd = stdev(scores)
```

### Pydantic response model for the endpoint
```python
# Source: follows existing Pydantic patterns in main.py (GradingDeadlinesResponse, etc.)
from pydantic import BaseModel

class HistogramBin(BaseModel):
    bin_start: float
    bin_end: float
    count: int
    label: str

class GradeStats(BaseModel):
    n: int
    small_sample: bool
    mean: float | None = None
    median: float | None = None
    stdev: float | None = None
    q1: float | None = None
    q3: float | None = None
    min: float | None = None
    max: float | None = None

class TaGradeStats(BaseModel):
    grader_name: str
    n: int
    mean: float | None = None

class GradeDistributionResponse(BaseModel):
    assignment_id: int | None
    assignment_name: str | None
    points_possible: float | None
    stats: GradeStats
    histogram: list[HistogramBin]
    per_ta: list[TaGradeStats]

class AssignmentGradeSummary(BaseModel):
    assignment_id: int
    assignment_name: str
    points_possible: float | None
    graded_count: int

class GradeDistributionIndexResponse(BaseModel):
    assignments: list[AssignmentGradeSummary]
```

### Navigation pattern (from Navigation.jsx)
```jsx
// Source: existing Navigation.jsx — BarChart2 is available in lucide-react ^0.539.0
import { BarChart2 } from 'lucide-react';
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| numpy for simple stats | Python `statistics` stdlib | Python 3.8+ | No numpy dep needed for basic descriptive stats |
| D3.js for all charts | Inline SVG React components | 2023–present | Simpler for single-page, small chart count use cases |
| recharts 2.x peer dep issues with React 19 | recharts 3.x (3.8.0) | March 2025 | React 19 now supported, but not needed for this phase |

**Deprecated/outdated:**
- `statistics.variance` / `statistics.pstdev`: We want *sample* stdev, so use `stdev()` not `pstdev()`.
- Fetching histogram data from Canvas API: Canvas does not expose grade distribution endpoints. Must compute from raw scores in SQLite.

## Open Questions

1. **Should the endpoint support "all assignments" summary mode?**
   - What we know: The phase description says "assignment selector" — implies single-assignment drill-down is the primary flow.
   - What's unclear: Whether an "overview" mode (list all assignments with summary stats in one call) is needed for the initial page load before the user selects an assignment.
   - Recommendation: Implement two endpoint patterns: `GET /api/dashboard/grade-distribution/{course_id}` returns `AssignmentGradeSummary[]` (index); `GET /api/dashboard/grade-distribution/{course_id}/{assignment_id}` returns full `GradeDistributionResponse`. This avoids one massive payload on page load.

2. **What is the exact small-sample threshold?**
   - What we know: n < 5 aligns with FERPA individual identification concerns and statistical convention (box plot quartiles are meaningless with fewer than 4 points).
   - What's unclear: Whether the product owner wants a different threshold (e.g., n < 10).
   - Recommendation: Use n < 5 as the backend `small_sample` flag. Frontend can display the exact n so TAs can judge.

3. **Per-TA stats: use `grader_id` (actual mode) or `group_members` (group mode)?**
   - What we know: Phase 6 added `ta_breakdown_mode` (group vs actual). Grade distributions should use actual grader data since we care about grading quality per TA.
   - What's unclear: Whether per-TA grade stats should respect the global `ta_breakdown_mode` setting.
   - Recommendation: Grade distribution per-TA stats should always use actual grader data (`grader_id` → `ta_users` join). The distribution question is "did TAs grade differently?" which requires actual grader attribution.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend) + Vitest with React Testing Library (frontend) |
| Config file | `pyproject.toml` (pytest), `canvas-react/vite.config.js` (vitest) |
| Quick run command | `uv run pytest tests/test_08_01_grade_distribution.py -x -q` |
| Full suite command | `uv run pytest -q && cd canvas-react && npm test -- --run` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GRADE-DB-01 | No new DB schema needed — submissions.score already exists | N/A | existing suite | ✅ (existing) |
| GRADE-API-01 | `GET /api/dashboard/grade-distribution/{course_id}` returns assignment list with graded_count | unit | `uv run pytest tests/test_08_01_grade_distribution.py::TestGradeDistributionIndex -x` | ❌ Wave 0 |
| GRADE-API-02 | `GET /api/dashboard/grade-distribution/{course_id}/{assignment_id}` returns stats + histogram + per_ta | unit | `uv run pytest tests/test_08_01_grade_distribution.py::TestGradeDistributionDetail -x` | ❌ Wave 0 |
| GRADE-STATS-01 | Backend computes mean/median/stdev/Q1/Q3/min/max correctly | unit | `uv run pytest tests/test_08_01_grade_distribution.py::TestGradeStats -x` | ❌ Wave 0 |
| GRADE-STATS-02 | `small_sample=True` when n < 5; stdev/quartiles are None when n < 2 | unit | `uv run pytest tests/test_08_01_grade_distribution.py::TestSmallSample -x` | ❌ Wave 0 |
| GRADE-HIST-01 | Histogram bins cover 0 to points_possible; last bin catches max score | unit | `uv run pytest tests/test_08_01_grade_distribution.py::TestHistogramBins -x` | ❌ Wave 0 |
| GRADE-TA-01 | Per-TA stats group by grader_name, NULL grouped as "Unknown / Pre-Phase 6" | unit | `uv run pytest tests/test_08_01_grade_distribution.py::TestPerTaStats -x` | ❌ Wave 0 |
| GRADE-UI-01 | GradeAnalysis page renders assignment selector and loading state | unit | `cd canvas-react && npm test -- --run GradeAnalysis` | ❌ Wave 0 |
| GRADE-UI-02 | GradeHistogram renders correct number of bars from bins prop | unit | `cd canvas-react && npm test -- --run GradeHistogram` | ❌ Wave 0 |
| GRADE-UI-03 | GradeBoxPlot renders box and whisker elements | unit | `cd canvas-react && npm test -- --run GradeBoxPlot` | ❌ Wave 0 |
| GRADE-UI-04 | Small-sample warning badge renders when `small_sample=true` | unit | `cd canvas-react && npm test -- --run GradeAnalysis` | ❌ Wave 0 |
| GRADE-NAV-01 | `/grade-analysis` route exists in App.jsx; Navigation.jsx shows Grade Analysis link | unit | `cd canvas-react && npm test -- --run App` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_08_01_grade_distribution.py -x -q`
- **Per wave merge:** `uv run pytest -q && cd canvas-react && npm test -- --run`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_08_01_grade_distribution.py` — covers GRADE-API-01, GRADE-API-02, GRADE-STATS-01, GRADE-STATS-02, GRADE-HIST-01, GRADE-TA-01
- [ ] `canvas-react/src/GradeAnalysis.test.jsx` — covers GRADE-UI-01, GRADE-UI-04, GRADE-NAV-01
- [ ] `canvas-react/src/components/GradeHistogram.test.jsx` — covers GRADE-UI-02
- [ ] `canvas-react/src/components/GradeBoxPlot.test.jsx` — covers GRADE-UI-03

## Sources

### Primary (HIGH confidence)
- Python docs: https://docs.python.org/3/library/statistics.html — `quantiles`, `stdev`, `median`, version constraints
- Existing codebase patterns: `database.py` `get_submissions()`, `main.py` `get_grading_deadlines()`, `Navigation.jsx`, `GradingScheduleSummary.jsx`
- `canvas-react/package.json` — confirmed zero charting libraries currently installed

### Secondary (MEDIUM confidence)
- GitHub recharts/recharts issue #4558 — React 19 support confirmed in recharts 2.13.0+ / 3.x
- recharts releases (March 2025) — confirmed latest is v3.8.0
- recharts BarChart API docs — confirmed BarChart is composable but no native histogram binning

### Tertiary (LOW confidence)
- WebSearch: small-sample warning thresholds — n=5 is a commonly cited FERPA and statistical convention threshold but no single authoritative source; recommendation is defensible

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all recommended libraries are either stdlib or already in project; recharts peer dep situation verified
- Architecture: HIGH — patterns directly mirror existing pages (GradingScheduleSummary, LateDaysTracking) and existing endpoint structure
- Pitfalls: HIGH — `statistics.stdev` edge case is documented behavior; box plot SVG clamping is verified geometry; NULL grader_id is confirmed by Phase 6 migration pattern

**Research date:** 2026-03-15
**Valid until:** 2026-06-15 (stable — Python stdlib and SVG patterns don't change; recharts version may update but is not used)

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GRADE-DB-01 | No new DB schema — submissions.score and grader_id/graded_at columns exist from Phases 5-6 | Confirmed: `database.py` `get_submissions()` already returns score, grader_id, grader_name |
| GRADE-API-01 | Grade distribution index endpoint — list assignments with graded_count | Research identifies two-endpoint pattern (index + detail) as optimal |
| GRADE-API-02 | Grade distribution detail endpoint — per-assignment stats, histogram, per-TA | Python stdlib `statistics.quantiles` + custom binning function covers all needs |
| GRADE-STATS-01 | Summary stats: mean, median, stdev, Q1, Q3, min, max | `statistics` stdlib covers all; stdev guard for n < 2 documented |
| GRADE-STATS-02 | small_sample flag when n < 5; graceful handling of n < 2 | Edge cases identified and guarded in code examples |
| GRADE-HIST-01 | Histogram bins from 0 to points_possible | Custom `compute_histogram_bins()` function documented; last-bin closed-right pitfall identified |
| GRADE-TA-01 | Per-TA grade stats using actual grader attribution | grader_name already in `get_submissions()` LEFT JOIN; NULL grouping strategy documented |
| GRADE-UI-01 | GradeAnalysis page with assignment selector | Route + component pattern matches GradingScheduleSummary exactly |
| GRADE-UI-02 | Histogram visualization | Pure SVG GradeHistogram component — no recharts needed |
| GRADE-UI-03 | Box plot visualization | Pure SVG GradeBoxPlot component with Tukey layout |
| GRADE-UI-04 | Small-sample warning badge | AlertTriangle from lucide-react, same pattern as overdue badge in GradingScheduleSummary |
| GRADE-NAV-01 | Navigation link + route registration | BarChart2 icon available in lucide-react ^0.539.0 |
</phase_requirements>
