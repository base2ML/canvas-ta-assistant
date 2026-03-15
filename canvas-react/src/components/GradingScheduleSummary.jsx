import { useState, useEffect } from 'react';
import { AlertTriangle, Clock, Copy, CheckCircle } from 'lucide-react';

export default function GradingScheduleSummary({ activeCourseId, refreshTrigger, data: dataProp }) {
  const [fetchedData, setFetchedData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (dataProp !== undefined) return; // data passed directly — skip fetch
    if (!activeCourseId) return;
    setLoading(true);
    fetch(`/api/dashboard/grading-deadlines/${activeCourseId}`)
      .then(r => r.json())
      .then(d => setFetchedData(d))
      .catch(err => console.error('Error loading grading schedule:', err))
      .finally(() => setLoading(false));
  }, [activeCourseId, refreshTrigger, dataProp]);

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  // Use prop data if provided, otherwise use fetched data
  const data = dataProp !== undefined ? dataProp : fetchedData;

  if (dataProp === undefined && !activeCourseId) {
    return (
      <div className="p-8 text-center text-gray-500">
        Select a course to view the grading schedule.
      </div>
    );
  }

  if (loading) {
    return <div className="p-8 text-center text-gray-500">Loading grading schedule...</div>;
  }

  const assignments = data?.assignments ?? [];

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Grading Schedule</h1>
          <p className="text-sm text-gray-500 mt-1">
            Read-only view — share this URL with your grading team.
          </p>
        </div>
        <button
          onClick={handleCopyLink}
          className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded text-sm hover:bg-gray-50"
        >
          {copied ? (
            <>
              <CheckCircle className="h-4 w-4 text-green-600" />
              Copied!
            </>
          ) : (
            <>
              <Copy className="h-4 w-4" />
              Copy Link
            </>
          )}
        </button>
      </div>

      {/* Summary stats */}
      {data && (
        <div className="flex gap-4 mb-6">
          <div className="bg-white rounded border px-4 py-3">
            <p className="text-xs text-gray-500">Assignments</p>
            <p className="text-xl font-semibold">{assignments.length}</p>
          </div>
          <div className="bg-red-50 rounded border border-red-200 px-4 py-3">
            <p className="text-xs text-red-600">Past Deadline</p>
            <p className="text-xl font-semibold text-red-700">
              {assignments.filter(a => a.is_overdue && a.pending_submissions > 0).length}
            </p>
          </div>
          <div className="bg-white rounded border px-4 py-3">
            <p className="text-xs text-gray-500">Total Pending</p>
            <p className="text-xl font-semibold">
              {assignments.reduce((sum, a) => sum + (a.pending_submissions || 0), 0)}
            </p>
          </div>
        </div>
      )}

      {/* Assignment table */}
      {assignments.length === 0 ? (
        <div className="text-center text-gray-500 py-12">
          No assignments with grading deadlines found. Use Settings to propagate default deadlines.
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-700">Assignment</th>
                <th className="text-left px-4 py-3 font-medium text-gray-700">Due Date</th>
                <th className="text-left px-4 py-3 font-medium text-gray-700">Grading Deadline</th>
                <th className="text-left px-4 py-3 font-medium text-gray-700">Status</th>
                <th className="text-right px-4 py-3 font-medium text-gray-700">Pending</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {assignments.map(a => (
                <tr key={a.assignment_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{a.assignment_name}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {a.due_at ? new Date(a.due_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' }) : '—'}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {a.grading_deadline
                      ? new Date(a.grading_deadline).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' })
                      : <span className="text-gray-400">No deadline</span>}
                    {a.is_override && (
                      <span className="ml-1 text-xs text-purple-600">(override)</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {a.is_overdue && a.pending_submissions > 0 ? (
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        <AlertTriangle className="h-3 w-3" />
                        Overdue
                      </span>
                    ) : a.pending_submissions === 0 ? (
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        <CheckCircle className="h-3 w-3" />
                        Complete
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                        <Clock className="h-3 w-3" />
                        Pending
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-700">
                    {a.pending_submissions}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
