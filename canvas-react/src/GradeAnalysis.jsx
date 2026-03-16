import { useState, useEffect } from 'react';
import { AlertTriangle } from 'lucide-react';
import GradeHistogram from './components/GradeHistogram';
import GradeBoxPlot from './components/GradeBoxPlot';

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

  if (!usingTestData && !activeCourseId) {
    return (
      <div className="p-8 text-center text-gray-500">
        Select a course to view grade analysis.
      </div>
    );
  }

  const fmt = (val) => (val == null ? '—' : typeof val === 'number' ? val.toFixed(1) : val);

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
                      <th className="text-left px-4 py-3 font-medium text-gray-700">TA Name</th>
                      <th className="text-right px-4 py-3 font-medium text-gray-700">Graded</th>
                      <th className="text-right px-4 py-3 font-medium text-gray-700">Avg Score</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {detail.per_ta.map((ta, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-gray-900">{ta.grader_name}</td>
                        <td className="px-4 py-3 text-right text-gray-700">{ta.n}</td>
                        <td className="px-4 py-3 text-right text-gray-700">
                          {ta.mean == null ? '—' : ta.mean.toFixed(1)}
                        </td>
                      </tr>
                    ))}
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
