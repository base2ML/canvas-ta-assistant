import React, { useState, useCallback, useEffect } from 'react';
import { RefreshCw, UserCheck, UserMinus, UserPlus, TrendingUp } from 'lucide-react';
import { apiFetch } from './api.js';
import { formatDate as formatDateUtil, formatDateOnly } from './utils/dates';

const EnrollmentTracking = ({ courses, onLoadCourses, activeCourseId }) => {
  const [enrollmentData, setEnrollmentData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [loadTime, setLoadTime] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Use the configured active course, falling back to courses[0]
  const currentCourse = courses && courses.length > 0
    ? (activeCourseId ? (courses.find(c => String(c.id) === String(activeCourseId)) || courses[0]) : courses[0])
    : null;

  const fetchEnrollmentData = useCallback(async (courseId) => {
    try {
      const data = await apiFetch(`/api/dashboard/enrollment-history/${courseId}`);
      return data;
    } catch (err) {
      throw new Error(`Error fetching enrollment data: ${err.message}`);
    }
  }, []);

  const loadCourseData = useCallback(async () => {
    if (!currentCourse) return;

    const startTime = Date.now();
    setLoading(true);
    setError('');
    setLoadTime(null);

    try {
      const data = await fetchEnrollmentData(currentCourse.id);
      setEnrollmentData(data);
      setLastUpdated(new Date());

      const endTime = Date.now();
      const duration = (endTime - startTime) / 1000;
      setLoadTime(duration);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [currentCourse, fetchEnrollmentData]);

  // Load data automatically when component mounts and currentCourse is available
  useEffect(() => {
    if (currentCourse) {
      loadCourseData();
    } else if ((!courses || courses.length === 0) && onLoadCourses) {
      // If no courses are available, try to load them from the parent
      onLoadCourses();
    }
  }, [currentCourse, loadCourseData, courses, onLoadCourses]);

  const getEventIcon = (previousStatus, newStatus) => {
    if (previousStatus === 'new' && newStatus === 'active') {
      return <UserPlus className="w-4 h-4 text-green-600" />;
    } else if (newStatus === 'dropped') {
      return <UserMinus className="w-4 h-4 text-red-600" />;
    } else if (previousStatus === 'dropped' && newStatus === 'active') {
      return <UserCheck className="w-4 h-4 text-blue-600" />;
    }
    return <UserCheck className="w-4 h-4 text-gray-600" />;
  };

  const getEventDescription = (previousStatus, newStatus) => {
    if (previousStatus === 'new' && newStatus === 'active') {
      return 'Newly enrolled';
    } else if (newStatus === 'dropped') {
      return 'Dropped';
    } else if (previousStatus === 'dropped' && newStatus === 'active') {
      return 'Re-enrolled';
    }
    return `${previousStatus} → ${newStatus}`;
  };

  // Show "no course configured" message
  if (!currentCourse) {
    return (
      <div className="p-8 text-center">
        <p className="text-gray-500">No course configured. Please configure a course in Settings.</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-2xl font-bold text-gray-900">Enrollment Tracking</h1>
          <button
            onClick={loadCourseData}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
        <div className="flex items-center gap-4 text-sm text-gray-600">
          <span className="font-medium">{currentCourse.name || `Course ${currentCourse.id}`}</span>
          {lastUpdated && (
            <span>Last updated: {formatDateUtil(lastUpdated)}</span>
          )}
          {loadTime && (
            <span className="text-gray-500">Load time: {loadTime.toFixed(2)}s</span>
          )}
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Content */}
      {!loading && !error && enrollmentData && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            {/* Active Students */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Active Students</p>
                  <p className="text-3xl font-bold text-green-600 mt-2">
                    {enrollmentData.current_counts.active}
                  </p>
                </div>
                <UserCheck className="w-8 h-8 text-green-600" />
              </div>
            </div>

            {/* Dropped Students */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Dropped Students</p>
                  <p className="text-3xl font-bold text-orange-600 mt-2">
                    {enrollmentData.current_counts.dropped}
                  </p>
                </div>
                <UserMinus className="w-8 h-8 text-orange-600" />
              </div>
            </div>

            {/* Total Students */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Students</p>
                  <p className="text-3xl font-bold text-blue-600 mt-2">
                    {enrollmentData.current_counts.active + enrollmentData.current_counts.dropped}
                  </p>
                </div>
                <TrendingUp className="w-8 h-8 text-blue-600" />
              </div>
            </div>
          </div>

          {/* Enrollment Over Time - SVG Line Chart */}
          {(() => {
            const chronologicalSnapshots = [...(enrollmentData.snapshots || [])].reverse();
            if (chronologicalSnapshots.length < 2) return null;

            const padL = 50, padR = 20, padT = 16, padB = 32;
            const width = 600, height = 160;
            const plotW = width - padL - padR;
            const plotH = height - padT - padB;

            const counts = chronologicalSnapshots.map(s => s.active_count);
            let minCount = Math.min(...counts);
            let maxCount = Math.max(...counts);
            if (minCount === maxCount) {
              minCount = minCount - 1;
              maxCount = maxCount + 1;
            }
            const range = maxCount - minCount;
            const padding = range * 0.05;
            const yMin = minCount - padding;
            const yMax = maxCount + padding;

            const toX = (i) => padL + (i / (chronologicalSnapshots.length - 1)) * plotW;
            const toY = (val) => padT + plotH - ((val - yMin) / (yMax - yMin)) * plotH;

            const points = chronologicalSnapshots.map((s, i) => `${toX(i)},${toY(s.active_count)}`).join(' ');

            const firstDate = formatDateOnly(chronologicalSnapshots[0].sync_completed_at || chronologicalSnapshots[0].recorded_at);
            const lastDate = formatDateOnly(chronologicalSnapshots[chronologicalSnapshots.length - 1].sync_completed_at || chronologicalSnapshots[chronologicalSnapshots.length - 1].recorded_at);

            return (
              <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Enrollment Over Time</h2>
                <svg viewBox="0 0 600 160" className="w-full h-40">
                  {/* Y-axis labels */}
                  <text x={padL - 6} y={toY(maxCount)} fontSize="10" fill="#6b7280" textAnchor="end" dominantBaseline="middle">{Math.round(maxCount)}</text>
                  <text x={padL - 6} y={toY(minCount)} fontSize="10" fill="#6b7280" textAnchor="end" dominantBaseline="middle">{Math.round(minCount)}</text>
                  {/* Line */}
                  <polyline
                    points={points}
                    stroke="#2563eb"
                    strokeWidth="2"
                    fill="none"
                  />
                  {/* Dots */}
                  {chronologicalSnapshots.map((s, i) => (
                    <circle key={i} cx={toX(i)} cy={toY(s.active_count)} r="3" fill="#2563eb" />
                  ))}
                  {/* X-axis labels */}
                  <text x={toX(0)} y={height - 4} fontSize="10" fill="#6b7280" textAnchor="middle">{firstDate}</text>
                  <text x={toX(chronologicalSnapshots.length - 1)} y={height - 4} fontSize="10" fill="#6b7280" textAnchor="middle">{lastDate}</text>
                </svg>
              </div>
            );
          })()}

          {/* Enrollment Changes */}
          {(() => {
            const allSnapshots = enrollmentData.snapshots || [];
            const firstSnapshot = allSnapshots.length > 0
              ? allSnapshots[allSnapshots.length - 1]
              : null;
            const changedSnapshots = allSnapshots.filter(
              s => s.newly_enrolled_count > 0 || s.newly_dropped_count > 0 || s === firstSnapshot
            );
            if (changedSnapshots.length === 0) return null;
            return (
              <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Enrollment Changes</h2>
                <div className="space-y-3">
                  {changedSnapshots.map((snapshot, index) => (
                    <div
                      key={snapshot.id || index}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-md"
                    >
                      <div className="flex items-center gap-3">
                        <div>
                          <p className="text-sm font-medium">
                            {formatDateOnly(snapshot.sync_completed_at || snapshot.recorded_at)}
                          </p>
                          <p className="text-xs text-gray-500">
                            {formatDateUtil(snapshot.sync_completed_at || snapshot.recorded_at)}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="text-sm text-gray-700">
                          <span className="font-medium text-green-600">{snapshot.active_count}</span> active,{' '}
                          <span className="font-medium text-orange-600">{snapshot.dropped_count}</span> dropped
                        </span>
                        <span className="text-xs text-gray-500">
                          {snapshot.newly_enrolled_count > 0 && (
                            <span className="text-green-600">
                              +{snapshot.newly_enrolled_count} new
                            </span>
                          )}
                          {snapshot.newly_enrolled_count > 0 && snapshot.newly_dropped_count > 0 && ', '}
                          {snapshot.newly_dropped_count > 0 && (
                            <span className="text-orange-600">
                              -{snapshot.newly_dropped_count} dropped
                            </span>
                          )}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}

          {/* Recent Events */}
          {enrollmentData.events && enrollmentData.events.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Events</h2>
              <div className="space-y-2">
                {enrollmentData.events.map((event, index) => (
                  <div
                    key={event.id || index}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-md"
                  >
                    <div className="flex items-center gap-3">
                      {getEventIcon(event.previous_status, event.new_status)}
                      <div>
                        <p className="text-sm font-medium text-gray-900">{event.user_name}</p>
                        <p className="text-xs text-gray-500">
                          {getEventDescription(event.previous_status, event.new_status)}
                        </p>
                      </div>
                    </div>
                    <span className="text-xs text-gray-500">
                      {formatDateUtil(event.occurred_at)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Empty State */}
          {((enrollmentData.snapshots || []).length === 0) &&
           (!enrollmentData.events || enrollmentData.events.length === 0) && (
            <div className="bg-white rounded-lg shadow-sm border p-6 text-center">
              <p className="text-gray-500">No enrollment history available yet. Sync data to begin tracking enrollment changes.</p>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default EnrollmentTracking;
