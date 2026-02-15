import React, { useState, useCallback, useEffect } from 'react';
import { RefreshCw, UserCheck, UserMinus, UserPlus, TrendingUp } from 'lucide-react';
import { apiFetch } from './api.js';

const EnrollmentTracking = ({ courses, onLoadCourses }) => {
  const [enrollmentData, setEnrollmentData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [loadTime, setLoadTime] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Use the first available course (since this tool is for single course use)
  const currentCourse = courses && courses.length > 0 ? courses[0] : null;

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

  const formatDateTime = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString();
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
            <span>Last updated: {lastUpdated.toLocaleString()}</span>
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

          {/* Enrollment Timeline */}
          {enrollmentData.snapshots && enrollmentData.snapshots.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Enrollment Timeline</h2>
              <div className="space-y-3">
                {enrollmentData.snapshots.map((snapshot, index) => (
                  <div
                    key={snapshot.id || index}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-md"
                  >
                    <div className="flex items-center gap-3">
                      <div>
                        <p className="text-sm font-medium">
                          {formatDate(snapshot.sync_completed_at || snapshot.recorded_at)}
                        </p>
                        <p className="text-xs text-gray-500">
                          {formatDateTime(snapshot.sync_completed_at || snapshot.recorded_at)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-sm text-gray-700">
                        <span className="font-medium text-green-600">{snapshot.active_count}</span> active,{' '}
                        <span className="font-medium text-orange-600">{snapshot.dropped_count}</span> dropped
                      </span>
                      {(snapshot.newly_dropped_count > 0 || snapshot.newly_enrolled_count > 0) && (
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
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

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
                      {formatDateTime(event.occurred_at)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Empty State */}
          {(!enrollmentData.snapshots || enrollmentData.snapshots.length === 0) &&
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
