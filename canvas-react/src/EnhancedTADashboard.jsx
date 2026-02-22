import React, { useState, useEffect, useMemo } from 'react';
import { RefreshCw } from 'lucide-react';
import AssignmentStatusBreakdown from './components/AssignmentStatusBreakdown';
import { apiFetch } from './api';

const EnhancedTADashboard = ({ courses = [], onLoadCourses, activeCourseId }) => {
  // Use courses from props, but keep local state for selection
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState(null);

  // Expandable assignments state (for nested TA breakdown)
  const [expandedAssignments, setExpandedAssignments] = useState(new Set());

  // Build TA assignments from Canvas groups
  const buildTAAssignments = React.useCallback((groupList) => {
    const taAssignments = {};

    groupList.forEach(group => {
      // Filter out non-TA groups (like "Term Project" groups)
      if (group.name && !group.name.toLowerCase().includes('project') && group.members && group.members.length > 0) {
        taAssignments[group.name] = new Set(group.members.map(m => String(m.user_id || m)));
      }
    });

    return taAssignments;
  }, []);

  const loadCourseData = React.useCallback(async (courseId) => {
    if (!courseId) return;

    setLoading(true);
    setError('');
    try {
      // Fetch all data from local API
      const [assignmentsData, submissionsData, groupsData] = await Promise.all([
        apiFetch(`/api/canvas/assignments/${courseId}`),
        apiFetch(`/api/canvas/submissions/${courseId}`),
        apiFetch(`/api/canvas/groups/${courseId}`)
      ]);

      setAssignments(assignmentsData.assignments || []);
      setSubmissions(submissionsData.submissions || []);
      setGroups(groupsData.groups || []);

      // Fetch the actual last sync time from the backend (best-effort)
      try {
        const syncData = await apiFetch(`/api/canvas/sync/status?course_id=${courseId}`);
        const completedAt = syncData?.last_sync?.completed_at;
        setLastUpdated(completedAt ? new Date(completedAt) : new Date());
      } catch (syncErr) {
        console.warn('Could not fetch sync status, falling back to current time:', syncErr);
        setLastUpdated(new Date());
      }
    } catch (err) {
      console.error('Error loading course data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initialize or reset selected course when courses or activeCourseId changes.
  // selectedCourse is intentionally excluded from deps — it is only used as a
  // comparison guard to avoid redundant resets, not as a reactive input.
  useEffect(() => {
    if (courses && courses.length > 0) {
      const target = courses.find(c => String(c.id) === String(activeCourseId)) || courses[0];
      if (!selectedCourse || String(selectedCourse.id) !== String(target.id)) {
        setSelectedCourse(target);
        loadCourseData(target.id);
      }
    }
  }, [courses, activeCourseId, loadCourseData]); // eslint-disable-line react-hooks/exhaustive-deps

  // Trigger parent to load courses if empty
  useEffect(() => {
    if ((!courses || courses.length === 0) && onLoadCourses) {
      onLoadCourses();
    }
  }, [courses, onLoadCourses]);


  // Compute assignment statistics with TA breakdown from loaded data
  const assignmentStats = useMemo(() => {
    if (!assignments.length || !submissions.length || !groups.length) {
      return [];
    }

    // Build TA assignments from Canvas groups
    const taAssignments = buildTAAssignments(groups);

    // Compute statistics for each assignment
    return assignments.map(assignment => {
      const assignmentId = assignment.id;

      // Get all submissions for this assignment
      const assignmentSubmissions = submissions.filter(
        s => s.assignment_id === assignmentId
      );

      // Calculate submission status FIRST (needed for progress calculation)
      const submittedOnTime = assignmentSubmissions.filter(s => {
        if (!s.submitted_at || !assignment.due_at) return false;
        return new Date(s.submitted_at) <= new Date(assignment.due_at);
      }).length;

      const submittedLate = assignmentSubmissions.filter(s => {
        if (!s.submitted_at || !assignment.due_at) return false;
        return new Date(s.submitted_at) > new Date(assignment.due_at);
      }).length;

      const notSubmitted = assignmentSubmissions.filter(s =>
        !s.submitted_at || s.workflow_state === 'unsubmitted'
      ).length;

      // Calculate grading progress based on SUBMITTED assignments only
      const totalSubmissions = assignmentSubmissions.length;
      const actuallySubmitted = submittedOnTime + submittedLate;
      // Only count as graded if actually submitted AND graded (excludes missing submissions graded as 0)
      const gradedSubmissions = assignmentSubmissions.filter(
        s => s.workflow_state === 'graded' && s.submitted_at
      ).length;
      const pendingSubmissions = actuallySubmitted - gradedSubmissions;
      const percentageGraded = actuallySubmitted > 0
        ? Math.round((gradedSubmissions / actuallySubmitted) * 100)
        : 0;

      // Calculate TA breakdown for this assignment
      const taGradingBreakdown = Object.entries(taAssignments).map(([taName, studentIds]) => {
        // Get submissions for this TA's students on this assignment
        const taSubmissions = assignmentSubmissions.filter(s =>
          studentIds.has(String(s.user_id))
        );

        const totalAssigned = taSubmissions.length;
        // Only count as graded if actually submitted AND graded (excludes missing submissions graded as 0)
        const graded = taSubmissions.filter(s => s.workflow_state === 'graded' && s.submitted_at).length;

        // Count submission statuses for this TA
        const taSubmittedOnTime = taSubmissions.filter(s => {
          if (!s.submitted_at || !assignment.due_at) return false;
          return new Date(s.submitted_at) <= new Date(assignment.due_at);
        }).length;

        const taSubmittedLate = taSubmissions.filter(s => {
          if (!s.submitted_at || !assignment.due_at) return false;
          return new Date(s.submitted_at) > new Date(assignment.due_at);
        }).length;

        const taNotSubmitted = taSubmissions.filter(s =>
          !s.submitted_at || s.workflow_state === 'unsubmitted'
        ).length;

        // Calculate progress based on SUBMITTED assignments only
        const taActuallySubmitted = taSubmittedOnTime + taSubmittedLate;
        const taPending = taActuallySubmitted - graded;
        const percentageComplete = taActuallySubmitted > 0
          ? Math.round((graded / taActuallySubmitted) * 100)
          : 0;

        return {
          ta_name: taName,
          total_assigned: totalAssigned,
          actually_submitted: taActuallySubmitted,
          graded: graded,
          pending: taPending,
          percentage_complete: percentageComplete,
          submitted_on_time: taSubmittedOnTime,
          submitted_late: taSubmittedLate,
          not_submitted: taNotSubmitted
        };
      }).filter(ta => ta.total_assigned > 0); // Only include TAs with assignments

      return {
        assignment_id: assignmentId,
        assignment_name: assignment.name,
        due_at: assignment.due_at,
        html_url: assignment.html_url,
        total_submissions: totalSubmissions,
        actually_submitted: actuallySubmitted,
        graded_submissions: gradedSubmissions,
        pending_submissions: pendingSubmissions,
        percentage_graded: percentageGraded,
        submitted_on_time: submittedOnTime,
        submitted_late: submittedLate,
        not_submitted: notSubmitted,
        ta_grading_breakdown: taGradingBreakdown
      };
    });
  }, [assignments, submissions, groups, buildTAAssignments]);

  // Toggle assignment expanded state
  const toggleAssignmentExpanded = (assignmentId) => {
    const newExpanded = new Set(expandedAssignments);
    if (newExpanded.has(assignmentId)) {
      newExpanded.delete(assignmentId);
    } else {
      newExpanded.add(assignmentId);
    }
    setExpandedAssignments(newExpanded);
  };

  const refreshData = async () => {
    setLoading(true);
    setError('');

    try {
      // First, trigger Canvas data sync
      const syncResult = await apiFetch('/api/canvas/sync', { method: 'POST' });
      console.log('Sync completed:', syncResult);

      // Reload data immediately since sync is synchronous now
      if (selectedCourse) {
        await loadCourseData(selectedCourse.id);
      } else if (onLoadCourses) {
        onLoadCourses();
      }

    } catch (err) {
      console.error('Refresh error:', err);
      setError(`Failed to refresh: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Format last updated time in EST
  const formatLastUpdated = (date) => {
    if (!date) return 'Never';

    const options = {
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZone: 'America/New_York',
      hour12: false
    };

    return new Intl.DateTimeFormat('en-US', options).format(date) + ' EST';
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white shadow-sm rounded-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-3xl font-bold text-gray-900">TA Grading Dashboard</h1>
            <div className="flex flex-col items-end space-y-2">
              {lastUpdated && (
                <div className="text-sm text-gray-500">
                  Last Updated: {formatLastUpdated(lastUpdated)}
                </div>
              )}
              <button
                onClick={refreshData}
                disabled={loading}
                className="inline-flex items-center space-x-2 px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                <span>Refresh</span>
              </button>
            </div>
          </div>


          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}
        </div>

        {selectedCourse && (
          <>
            {/* Assignment Status Breakdown */}
            {assignmentStats.length > 0 && (
              <AssignmentStatusBreakdown
                assignmentStats={assignmentStats}
                expandedAssignments={expandedAssignments}
                onToggleExpanded={toggleAssignmentExpanded}
              />
            )}
          </>
        )}

        {!selectedCourse && courses.length === 0 && !loading && (
          <div className="text-center py-12">
            <h3 className="mt-2 text-sm font-medium text-gray-900">No courses found</h3>
            <p className="mt-1 text-sm text-gray-500">
              No course data is available. Configure a course in Settings and sync data from Canvas.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default EnhancedTADashboard;
