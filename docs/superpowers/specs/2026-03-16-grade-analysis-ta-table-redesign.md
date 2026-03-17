# Grade Analysis — Per-TA Table Redesign

**Date:** 2026-03-16
**Status:** Approved

---

## Summary

Redesign the per-TA breakdown section of the Grade Analysis page to surface richer statistics and enable visual comparison across TAs. The table gains full-row sort, median and std dev columns, and an inline box-and-whisker plot where all rows share a common 0–100% of max axis.

---

## Requirements

1. **Sortable table** — every stat column header is a clickable button; clicking the active column toggles asc/desc; clicking a new column sorts by that column's natural default direction. An arrow indicator (↑/↓) shows the active sort column and direction; inactive columns show ↕. The Distribution column is not sortable.
2. **Per-TA stats columns**: TA Name · Graded · Mean · Median · Std Dev. All stat values are **raw points** (same units as the assignment score).
3. **Inline box plot** — rightmost "Distribution" column. The x-axis maps `[0, points_possible]` raw points to `[0, 400]` SVG units. All rows share this scale so boxes are visually comparable.
4. **Shared axis labels** — tick labels "0", "25", "50", "75", "100" appear in the column header and represent **percent of max** (i.e. "25" means 25% of `points_possible`, not 25 raw points). They align with the box plots via identical SVG coordinate systems in both the header tick row and the data rows.
5. **Small-sample badge** — rendered when `ta.small_sample === true` (backend field). Badge text: `⚠ n={ta.n}` (uses `ta.n` for the count).
6. **Unattributed / Dropped Student rows** — rendered in muted italic text (e.g., gray, italic).
7. **Null display** — stat cells with null/undefined values render `—`.
8. **Box plot suppression** — SVG omitted when `ta.n < 2` (or any required field is null). The `<td>` always renders to preserve column count. Note: n=2,3,4 rows will show both a box plot AND the small-sample badge — this is intentional (the box is valid but statistically unreliable).

---

## Architecture

### Backend — `TaGradeStats` model (`main.py`)

Extend the existing `TaGradeStats` model:

```python
class TaGradeStats(BaseModel):
    grader_name: str
    n: int
    mean: float | None = None
    median: float | None = None
    stdev: float | None = None
    min: float | None = None
    q1: float | None = None
    q3: float | None = None
    max: float | None = None
    small_sample: bool = False
```

All float fields are **raw points**. Computation in the existing `GET /api/dashboard/grade-distribution/{course_id}/{assignment_id}` endpoint, for each TA's `scores` list:

```python
ta_n = len(scores)
ta_mean   = _stats.mean(scores) if ta_n >= 1 else None
ta_median = _stats.median(scores) if ta_n >= 1 else None   # canonical median; qs[1] not used
ta_stdev  = _stats.stdev(scores) if ta_n >= 2 else None
ta_min    = min(scores) if ta_n >= 1 else None
ta_max    = max(scores) if ta_n >= 1 else None
try:
    qs = _stats.quantiles(scores, n=4) if ta_n >= 2 else None
    ta_q1 = qs[0] if qs else None   # qs[1] (Q2) discarded — ta_median is canonical
    ta_q3 = qs[2] if qs else None
except _stats.StatisticsError:
    ta_q1 = ta_q3 = None
small_sample = ta_n < 5
```

`statistics.median` is the canonical median for both the display column and the box plot median line. `qs[1]` (from `statistics.quantiles`) may differ slightly for small n due to different interpolation methods — it is intentionally discarded.

`GradeDistributionResponse` already includes `per_ta: list[TaGradeStats]` and `points_possible: float | None`. No new endpoint or response schema restructuring needed.

### Frontend — `GradeAnalysis.jsx`

Replace the existing per-TA `<table>` block with a sortable table. `points_possible` is already in scope as `detail.points_possible`.

**Sort state:**
```js
const [sort, setSort] = useState({ col: 'n', dir: 'desc' });
```

**Column definitions** (implement as a `COLS` constant to pass `naturalDir` to the handler):

```js
const COLS = [
  { key: 'grader_name', label: 'TA Name',  naturalDir: 'asc'  },
  { key: 'n',           label: 'Graded',   naturalDir: 'desc' },
  { key: 'mean',        label: 'Mean',     naturalDir: 'desc' },
  { key: 'median',      label: 'Median',   naturalDir: 'desc' },
  { key: 'stdev',       label: 'Std Dev',  naturalDir: 'desc' },
];
```

**Sort click handler:**
```js
function handleSort(col, naturalDir) {
  setSort(prev =>
    prev.col === col
      ? { col, dir: prev.dir === 'asc' ? 'desc' : 'asc' }
      : { col, dir: naturalDir }
  );
}
```

**Sort comparator** (nulls last, direction-independent):
```js
const sorted = [...(detail.per_ta ?? [])].sort((a, b) => {
  const av = a[sort.col], bv = b[sort.col];
  if (av == null && bv == null) return 0;
  if (av == null) return 1;
  if (bv == null) return -1;
  const cmp = typeof av === 'string' ? av.localeCompare(bv) : av - bv;
  return sort.dir === 'asc' ? cmp : -cmp;
});
```

**Null cell display:** `val == null ? '—' : val.toFixed(1)` for float columns; `ta.n` rendered directly (always an integer).

**Small-sample badge:** `{ta.small_sample && <span className="...">⚠ n={ta.n}</span>}`

**Unattributed/Dropped rows:** check if `ta.grader_name === 'Unattributed' || ta.grader_name === 'Dropped Student'` — apply muted italic styling to the name cell.

### Frontend — Inline box plot SVG

`detail.points_possible` is the scale reference. The scale function:
```js
const bpX = (v) => Math.min(400, Math.max(0, (v / detail.points_possible) * 400));
```

SVG is `width: 100%` with `height` fixed at `30px`. The viewBox is `0 0 400 30`. Because the rendered height (30px CSS) equals the viewBox height (30), the vertical scale is always 1:1. Only the horizontal dimension stretches with column width. `preserveAspectRatio="none"` is safe here for this reason.

```jsx
{ta.n >= 2 && ta.q1 != null && ta.q3 != null && ta.min != null && ta.max != null && detail.points_possible != null && (
  <svg
    viewBox="0 0 400 30"
    preserveAspectRatio="none"
    style={{ display: 'block', width: '100%', height: '30px' }}
  >
    {/* Quarter guide lines */}
    <line x1="100" y1="0" x2="100" y2="30" stroke="#374151" strokeWidth="1"/>
    <line x1="200" y1="0" x2="200" y2="30" stroke="#374151" strokeWidth="1"/>
    <line x1="300" y1="0" x2="300" y2="30" stroke="#374151" strokeWidth="1"/>
    {/* Left whisker: min → q1 */}
    <line x1={bpX(ta.min)} y1="15" x2={bpX(ta.q1)} y2="15" stroke="#6b7280" strokeWidth="2"/>
    <line x1={bpX(ta.min)} y1="7"  x2={bpX(ta.min)} y2="23" stroke="#6b7280" strokeWidth="2"/>
    {/* IQR box: q1 → q3 */}
    <rect x={bpX(ta.q1)} y="6" width={bpX(ta.q3) - bpX(ta.q1)} height="18"
          fill="#1e3a5f" stroke="#3b82f6" strokeWidth="1.5"/>
    {/* Median line */}
    <line x1={bpX(ta.median)} y1="6" x2={bpX(ta.median)} y2="24"
          stroke="#60a5fa" strokeWidth="3"/>
    {/* Right whisker: q3 → max */}
    <line x1={bpX(ta.q3)} y1="15" x2={bpX(ta.max)} y2="15" stroke="#6b7280" strokeWidth="2"/>
    <line x1={bpX(ta.max)} y1="7"  x2={bpX(ta.max)} y2="23" stroke="#6b7280" strokeWidth="2"/>
  </svg>
)}
```

### Axis alignment — guaranteed via matching SVG coordinate systems

The tick labels in the `<th>` use a **matching SVG** so coordinates are identical to the data row SVGs:

```jsx
<svg
  viewBox="0 0 400 14"
  preserveAspectRatio="none"
  style={{ display: 'block', width: '100%', height: '14px' }}
>
  <text x="0"   y="11" textAnchor="start"  fontSize="10" fill="#6b7280">0</text>
  <text x="100" y="11" textAnchor="middle" fontSize="10" fill="#6b7280">25</text>
  <text x="200" y="11" textAnchor="middle" fontSize="10" fill="#6b7280">50</text>
  <text x="300" y="11" textAnchor="middle" fontSize="10" fill="#6b7280">75</text>
  <text x="400" y="11" textAnchor="end"    fontSize="10" fill="#6b7280">100</text>
</svg>
```

Both the tick SVG and the data SVGs use `width: 100%` + `preserveAspectRatio="none"` + `viewBox="0 0 400 ..."`, so the horizontal scaling is identical and alignment is guaranteed regardless of column width. The `<th>` and `<td>` use the same horizontal padding.

---

## Files Changed

| File | Change |
|------|--------|
| `main.py` | Extend `TaGradeStats`; compute median/stdev/min/q1/q3/max/small_sample in detail endpoint |
| `canvas-react/src/GradeAnalysis.jsx` | Replace per-TA table with sortable table + inline SVG |
| `canvas-react/src/components/GradeBoxPlot.jsx` | No change |

---

## Out of Scope

- Histogram per TA
- Persistent sort preference across page refreshes
- Exporting the table
- Backward-compatibility shim (backend and frontend deploy together)
