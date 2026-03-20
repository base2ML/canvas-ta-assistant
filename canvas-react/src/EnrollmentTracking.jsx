import React, { useState, useCallback, useEffect } from 'react';
import { RefreshCw, UserCheck, UserMinus, UserPlus, TrendingUp } from 'lucide-react';
import { apiFetch } from './api.js';
import { formatDate as formatDateUtil, formatDateOnly } from './utils/dates';

const EnrollmentTracking = ({ courses, onLoadCourses, activeCourseId, refreshTrigger }) => {
  const [enrollmentData, setEnrollmentData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

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

    setLoading(true);
    setError('');

    try {
      const data = await fetchEnrollmentData(currentCourse.id);
      setEnrollmentData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [currentCourse, fetchEnrollmentData]);

  // Load data automatically when component mounts and currentCourse is available.
  // refreshTrigger is incremented by the global header on each successful sync, causing a reload.
  useEffect(() => {
    if (currentCourse) {
      loadCourseData();
    } else if ((!courses || courses.length === 0) && onLoadCourses) {
      // If no courses are available, try to load them from the parent
      onLoadCourses();
    }
  }, [currentCourse, loadCourseData, courses, onLoadCourses, refreshTrigger]);

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
        </div>
        <div className="flex items-center gap-4 text-sm text-gray-600">
          <span className="font-medium">{currentCourse.name || `Course ${currentCourse.id}`}</span>
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

          {/* Enrollment Over Time - SVG Step Chart */}
          {(() => {
            const chronologicalSnapshots = [...(enrollmentData.snapshots || [])].reverse();
            const deduplicated = chronologicalSnapshots.filter((s, i) =>
              i === 0 || s.active_count !== chronologicalSnapshots[i - 1].active_count
            );
            if (deduplicated.length === 0) return null;

            const padL = 50, padR = 20, padT = 30, padB = 55;
            const width = 600, height = 185;
            const plotW = width - padL - padR;
            const plotH = height - padT - padB;

            const counts = deduplicated.map(s => s.active_count);
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

            const getDate = (s) => new Date(s.sync_completed_at || s.recorded_at);
            const today = new Date();
            const semesterStart = getDate(deduplicated[0]);
            const timeRange = today - semesterStart;
            const toX = (date) => padL + ((date - semesterStart) / timeRange) * plotW;
            const toY = (val) => padT + plotH - ((val - yMin) / (yMax - yMin)) * plotH;

            const stepPoints = [];
            deduplicated.forEach((s, i) => {
              const x = toX(getDate(s));
              const y = toY(s.active_count);
              if (i > 0) {
                stepPoints.push(`${x},${toY(deduplicated[i - 1].active_count)}`);
              }
              stepPoints.push(`${x},${y}`);
            });
            stepPoints.push(`${toX(today)},${toY(deduplicated[deduplicated.length - 1].active_count)}`);

            const labelBaseY = padT + plotH + 8;

            return (
              <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Enrollment Over Time</h2>
                <svg viewBox={`0 0 ${width} ${height}`} className="w-full" style={{height: '185px'}}>
                  {/* Y-axis labels */}
                  <text x={padL - 6} y={toY(maxCount)} fontSize="10" fill="#6b7280" textAnchor="end" dominantBaseline="middle">{Math.round(maxCount)}</text>
                  <text x={padL - 6} y={toY(minCount)} fontSize="10" fill="#6b7280" textAnchor="end" dominantBaseline="middle">{Math.round(minCount)}</text>
                  {/* Step line */}
                  <polyline
                    points={stepPoints.join(' ')}
                    stroke="#2563eb"
                    strokeWidth="2"
                    fill="none"
                  />
                  {/* Dots, callout labels, and date labels at each change point */}
                  {deduplicated.map((s, i) => {
                    const cx = toX(getDate(s));
                    const cy = toY(s.active_count);
                    const label = String(s.active_count);
                    const labelW = label.length * 6 + 10;
                    const labelH = 15;
                    const labelX = cx - labelW / 2;
                    // flip callout below the dot if it would go above the top padding
                    const calloutAbove = cy - 22 >= padT;
                    const calloutY = calloutAbove ? cy - 22 : cy + 8;
                    const dateStr = formatDateOnly(s.sync_completed_at || s.recorded_at);
                    return (
                      <g key={i}>
                        {/* Callout box */}
                        <rect x={labelX} y={calloutY} width={labelW} height={labelH} rx="3" fill="white" stroke="#2563eb" strokeWidth="1" />
                        <text x={cx} y={calloutY + 10} fontSize="9" fill="#2563eb" textAnchor="middle" fontWeight="bold">{label}</text>
                        {/* Dot */}
                        <circle cx={cx} cy={cy} r="3" fill="#2563eb" />
                        {/* Date label rotated -45° */}
                        <text
                          x={cx}
                          y={labelBaseY}
                          fontSize="9"
                          fill="#6b7280"
                          textAnchor="end"
                          transform={`rotate(-45, ${cx}, ${labelBaseY})`}
                        >{dateStr}</text>
                      </g>
                    );
                  })}
                  {/* Today label */}
                  <text x={toX(today)} y={labelBaseY} fontSize="9" fill="#6b7280" textAnchor="end" transform={`rotate(-45, ${toX(today)}, ${labelBaseY})`}>Today</text>
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
