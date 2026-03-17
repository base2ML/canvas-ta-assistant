import { useState, useEffect } from 'react';
import { AlertTriangle } from 'lucide-react';
import GradeHistogram from './components/GradeHistogram';
import GradeBoxPlot from './components/GradeBoxPlot';

const COLS = [
  { key: 'grader_name', label: 'TA Name',  naturalDir: 'asc'  },
  { key: 'n',           label: 'Graded',   naturalDir: 'desc' },
  { key: 'mean',        label: 'Mean',     naturalDir: 'desc' },
  { key: 'median',      label: 'Median',   naturalDir: 'desc' },
  { key: 'stdev',       label: 'Std Dev',  naturalDir: 'desc' },
];

export default function GradeAnalysis({ activeCourseId, refreshTrigger, _testData }) {
  const [assignments, setAssignments] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(_testData !== undefined ? _testData : null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);

  // If _testData prop is provided, skip fetching and use it directly (for unit tests)
  const usingTestData = _testData !== undefined;

  // Effect 1: fetch assignment index when activeCourseId or refreshTrigger changes
  useEffect(() => {
    if (usingTestData) return;
    if (!activeCourseId) return;
    setLoading(true);
    fetch(`/api/dashboard/grade-distribution/${activeCourseId}`)
      .then(r => r.json())
      .then(d => {
        const list = d.assignments ?? [];
        setAssignments(list);
        if (list.length > 0) {
          setSelectedId(list[0].assignment_id);
        } else {
          setSelectedId(null);
          setDetail(null);
        }
      })
      .catch(err => console.error('Error loading grade distribution:', err))
      .finally(() => setLoading(false));
  }, [activeCourseId, refreshTrigger, usingTestData]);

  // Effect 2: fetch detail when selectedId changes
  useEffect(() => {
    if (usingTestData) return;
    if (!activeCourseId || selectedId === null) return;
    setDetailLoading(true);
    fetch(`/api/dashboard/grade-distribution/${activeCourseId}/${selectedId}`)
      .then(r => r.json())
      .then(d => setDetail(d))
      .catch(err => console.error('Error loading assignment detail:', err))
      .finally(() => setDetailLoading(false));
  }, [activeCourseId, selectedId, usingTestData]);

  // --- per-TA sort state ---
  const [sort, setSort] = useState({ col: 'n', dir: 'desc' });

  function handleSort(col, naturalDir) {
    setSort(prev =>
      prev.col === col
        ? { col, dir: prev.dir === 'asc' ? 'desc' : 'asc' }
        : { col, dir: naturalDir }
    );
  }

  function sortedTa(rows) {
    if (!rows) return [];
    return [...rows].sort((a, b) => {
      const av = a[sort.col], bv = b[sort.col];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      const cmp = typeof av === 'string' ? av.localeCompare(bv) : av - bv;
      return sort.dir === 'asc' ? cmp : -cmp;
    });
  }

  const fmt = (val) => (val == null ? '—' : typeof val === 'number' ? val.toFixed(1) : val);

  const MUTED_NAMES = new Set(['Unattributed', 'Dropped Student']);

  if (!usingTestData && !activeCourseId) {
    return (
      <div className="p-8 text-center text-gray-500">
        Select a course to view grade analysis.
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Grade Analysis</h1>
        {activeCourseId && (
          <p className="text-sm text-gray-500 mt-1">Course: {activeCourseId}</p>
        )}
      </div>

      {/* Assignment selector — always rendered when we have a course */}
      {!usingTestData && (
        <div className="mb-6">
          <label htmlFor="assignment-select" className="block text-sm font-medium text-gray-700 mb-1">
            Assignment
          </label>
          <select
            id="assignment-select"
            value={selectedId ?? ''}
            onChange={e => setSelectedId(Number(e.target.value))}
            disabled={loading || assignments.length === 0}
            className="border border-gray-300 rounded px-3 py-2 text-sm w-full max-w-md"
          >
            {loading ? (
              <option value="">Loading grade analysis...</option>
            ) : assignments.length === 0 ? (
              <option value="">No assignments with graded submissions found.</option>
            ) : (
              assignments.map(a => (
                <option key={a.assignment_id} value={a.assignment_id}>
                  {a.assignment_name} ({a.graded_count} graded)
                </option>
              ))
            )}
          </select>
        </div>
      )}

      {/* When using test data — show a placeholder select */}
      {usingTestData && (
        <div className="mb-6">
          <select
            id="assignment-select"
            defaultValue={_testData?.assignment_id ?? ''}
            className="border border-gray-300 rounded px-3 py-2 text-sm w-full max-w-md"
            readOnly
          >
            {_testData && (
              <option value={_testData.assignment_id}>
                {_testData.assignment_name}
              </option>
            )}
          </select>
        </div>
      )}

      {/* Detail view */}
      {detailLoading && (
        <div className="text-center text-gray-500 py-8">Loading assignment details...</div>
      )}

      {!detailLoading && detail === null && !usingTestData && (
        <div className="text-center text-gray-500 py-8">
          Select an assignment above to view distribution.
        </div>
      )}

      {!detailLoading && detail && (
        <>
          {/* Summary stat cards */}
          <div className="flex flex-wrap gap-4 mb-4">
            <div className="bg-white rounded border px-4 py-3 min-w-[100px]">
              <p className="text-xs text-gray-500">Graded</p>
              <p className="text-xl font-semibold">{detail.stats?.n ?? '—'}</p>
            </div>
            <div className="bg-white rounded border px-4 py-3 min-w-[100px]">
              <p className="text-xs text-gray-500">Mean</p>
              <p className="text-xl font-semibold">{fmt(detail.stats?.mean)}</p>
            </div>
            <div className="bg-white rounded border px-4 py-3 min-w-[100px]">
              <p className="text-xs text-gray-500">Median</p>
              <p className="text-xl font-semibold">{fmt(detail.stats?.median)}</p>
            </div>
            <div className="bg-white rounded border px-4 py-3 min-w-[100px]">
              <p className="text-xs text-gray-500">Std Dev</p>
              <p className="text-xl font-semibold">{fmt(detail.stats?.stdev)}</p>
            </div>
          </div>

          {/* Small-sample warning */}
          {detail.stats?.small_sample && (
            <div className="flex items-center gap-1 px-2 py-1 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-700 mb-4 w-fit">
              <AlertTriangle className="h-3 w-3" />
              Small sample (n={detail.stats.n}) — statistics may not be reliable
            </div>
          )}

          {/* Charts: two-column grid on lg */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <div>
              <h2 className="text-sm font-medium text-gray-700 mb-2">Score Distribution</h2>
              <GradeHistogram
                bins={detail.histogram ?? []}
                pointsPossible={detail.points_possible}
              />
            </div>
            <div>
              <h2 className="text-sm font-medium text-gray-700 mb-2">Box Plot</h2>
              <GradeBoxPlot
                stats={detail.stats}
                pointsPossible={detail.points_possible}
              />
            </div>
          </div>

          {/* Per-TA table */}
          {detail.per_ta && detail.per_ta.length > 0 && (
            <div>
              <h2 className="text-sm font-medium text-gray-700 mb-2">Per-TA Breakdown</h2>
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      {COLS.map(col => (
                        <th key={col.key} className="px-3 py-2 text-left font-medium text-gray-700">
                          <button
                            onClick={() => handleSort(col.key, col.naturalDir)}
                            className="flex items-center gap-1 hover:text-blue-600"
                          >
                            {col.label}
                            <span className="text-gray-400 text-xs">
                              {sort.col === col.key ? (sort.dir === 'asc' ? '↑' : '↓') : '↕'}
                            </span>
                          </button>
                        </th>
                      ))}
                      <th className="px-3 py-2 text-left font-medium text-gray-700" style={{ minWidth: '200px' }}>
                        <svg
                          viewBox="0 0 400 14"
                          preserveAspectRatio="none"
                          style={{ display: 'block', width: '100%', height: '14px' }}
                        >
                          <text x="0"   y="11" textAnchor="start"  fontSize="10" fill="#9ca3af">0</text>
                          <text x="100" y="11" textAnchor="middle" fontSize="10" fill="#9ca3af">25</text>
                          <text x="200" y="11" textAnchor="middle" fontSize="10" fill="#9ca3af">50</text>
                          <text x="300" y="11" textAnchor="middle" fontSize="10" fill="#9ca3af">75</text>
                          <text x="400" y="11" textAnchor="end"    fontSize="10" fill="#9ca3af">100</text>
                        </svg>
                        <span className="text-xs font-normal text-gray-500">Distribution (% of max)</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {(() => {
                      const bpX = (v) => Math.min(400, Math.max(0, (v / detail.points_possible) * 400));
                      return sortedTa(detail.per_ta).map((ta) => {
                        const isMuted = MUTED_NAMES.has(ta.grader_name);
                        const showBox = ta.n >= 2
                          && ta.q1 != null && ta.q3 != null
                          && ta.min != null && ta.max != null
                          && detail.points_possible != null;
                        return (
                          <tr key={ta.grader_name} className="hover:bg-gray-50">
                            <td className={`px-3 py-2 ${isMuted ? 'text-gray-400 italic' : 'text-gray-900 font-medium'}`}>
                              {ta.grader_name}
                              {ta.small_sample && (
                                <span className="ml-1 text-xs bg-yellow-50 text-yellow-700 border border-yellow-200 rounded px-1">
                                  ⚠ n={ta.n}
                                </span>
                              )}
                            </td>
                            <td className="px-3 py-2 text-gray-700">{ta.n}</td>
                            <td className="px-3 py-2 text-gray-700">{fmt(ta.mean)}</td>
                            <td className="px-3 py-2 text-gray-700">{fmt(ta.median)}</td>
                            <td className="px-3 py-2 text-gray-700">{fmt(ta.stdev)}</td>
                            <td className="px-3 py-2">
                              {showBox && (
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
                                  <rect
                                    x={bpX(ta.q1)} y="6"
                                    width={Math.max(1, bpX(ta.q3) - bpX(ta.q1))} height="18"
                                    fill="#1e3a5f" stroke="#3b82f6" strokeWidth="1.5"
                                  />
                                  {/* Median line */}
                                  <line x1={bpX(ta.median)} y1="6" x2={bpX(ta.median)} y2="24"
                                        stroke="#60a5fa" strokeWidth="3"/>
                                  {/* Right whisker: q3 → max */}
                                  <line x1={bpX(ta.q3)} y1="15" x2={bpX(ta.max)} y2="15" stroke="#6b7280" strokeWidth="2"/>
                                  <line x1={bpX(ta.max)} y1="7"  x2={bpX(ta.max)} y2="23" stroke="#6b7280" strokeWidth="2"/>
                                </svg>
                              )}
                            </td>
                          </tr>
                        );
                      });
                    })()}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
