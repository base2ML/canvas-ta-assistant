import React, { useState, useEffect } from 'react';
import { RefreshCw, TrendingUp } from 'lucide-react';
import AssignmentStatusBreakdown from './components/AssignmentStatusBreakdown';

const EnhancedTADashboard = ({ backendUrl, getAuthHeaders, courses = [], onLoadCourses }) => {
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
  const [assignmentStats, setAssignmentStats] = useState([]);

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
    try {
      const headers = await getAuthHeaders();

      // Get S3 pre-signed URLs from API
      const [assignmentsRes] = await Promise.all([
        fetch(`${backendUrl}/api/canvas/assignments/${courseId}`, { headers }),
        fetch(`${backendUrl}/api/canvas/submissions/${courseId}`, { headers }),
        fetch(`${backendUrl}/api/canvas/users/${courseId}`, { headers }),
        fetch(`${backendUrl}/api/canvas/groups/${courseId}`, { headers })
      ]);

      // Fetch full Canvas data from S3 using pre-signed URL
      if (assignmentsRes.ok) {
        const urlData = await assignmentsRes.json();

        // Handle S3 pre-signed URL mode (production)
        if (urlData.data_url) {
          const s3Response = await fetch(urlData.data_url);
          const canvasData = await s3Response.json();
          setAssignments(canvasData.assignments || []);
          setSubmissions(canvasData.submissions || []);
          setGroups(canvasData.groups || []);
        }
        // Handle direct data mode (local mock data)
        else if (urlData.assignments) {
          setAssignments(urlData.assignments || []);
          // For mock mode, we need to fetch additional data
          const [submissionsRes, groupsRes] = await Promise.all([
            fetch(`${backendUrl}/api/canvas/submissions/${selectedCourse.id}`, { headers }),
            fetch(`${backendUrl}/api/canvas/groups/${selectedCourse.id}`, { headers })
          ]);

          if (submissionsRes.ok) {
            const subData = await submissionsRes.json();
            setSubmissions(subData.submissions || []);
          }
          if (groupsRes.ok) {
            const groupData = await groupsRes.json();
            setGroups(groupData.groups || []);
          }
        }
      }

      // Update last updated timestamp after successful data load
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Error loading course data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [backendUrl, getAuthHeaders, selectedCourse]);

  // Initialize selected course when courses are loaded
  useEffect(() => {
    if (courses && courses.length > 0 && !selectedCourse) {
      const firstCourse = courses[0];
      setSelectedCourse(firstCourse);
      loadCourseData(firstCourse.id);
    }
  }, [courses, selectedCourse, loadCourseData]);

  // Trigger parent to load courses if empty
  useEffect(() => {
    if ((!courses || courses.length === 0) && onLoadCourses) {
      onLoadCourses();
    }
  }, [courses, onLoadCourses]);


  // Compute assignment statistics with TA breakdown from loaded data
  useEffect(() => {
    if (!assignments.length || !submissions.length || !groups.length) {
      setAssignmentStats([]);
      return;
    }

    // Build TA assignments from Canvas groups
    const taAssignments = buildTAAssignments(groups);

    // Compute statistics for each assignment
    const stats = assignments.map(assignment => {
      const assignmentId = assignment.id;

      // Get all submissions for this assignment
      const assignmentSubmissions = submissions.filter(
        s => s.assignment_id === assignmentId
      );

      // Calculate overall grading progress
      const gradedSubmissions = assignmentSubmissions.filter(
        s => s.workflow_state === 'graded'
      ).length;
      const totalSubmissions = assignmentSubmissions.length;
      const ungradedSubmissions = totalSubmissions - gradedSubmissions;
      const percentageGraded = totalSubmissions > 0
        ? Math.round((gradedSubmissions / totalSubmissions) * 100)
        : 0;

      // Calculate submission status for this assignment
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

      // Calculate TA breakdown for this assignment
      const taGradingBreakdown = Object.entries(taAssignments).map(([taName, studentIds]) => {
        // Get submissions for this TA's students on this assignment
        const taSubmissions = assignmentSubmissions.filter(s =>
          studentIds.has(String(s.user_id))
        );

        const totalAssigned = taSubmissions.length;
        const graded = taSubmissions.filter(s => s.workflow_state === 'graded').length;
        const percentageComplete = totalAssigned > 0
          ? Math.round((graded / totalAssigned) * 100)
          : 0;

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

        return {
          ta_name: taName,
          total_assigned: totalAssigned,
          graded: graded,
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
        graded_submissions: gradedSubmissions,
        ungraded_submissions: ungradedSubmissions,
        percentage_graded: percentageGraded,
        submitted_on_time: submittedOnTime,
        submitted_late: submittedLate,
        not_submitted: notSubmitted,
        ta_grading_breakdown: taGradingBreakdown
      };
    });

    setAssignmentStats(stats);
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

  const handleCourseSelect = async (course) => {
    setSelectedCourse(course);
    setAssignments([]);
    setSubmissions([]);
    setGroups([]);
    await loadCourseData(course.id);
  };

  const refreshData = async () => {
    setLoading(true);
    setError('');

    try {
      // First, trigger Canvas data sync
      const headers = await getAuthHeaders();
      const syncResponse = await fetch(`${backendUrl}/api/canvas/sync`, {
        method: 'POST',
        headers
      });

      if (!syncResponse.ok) {
        throw new Error(`Sync failed: ${syncResponse.statusText}`);
      }

      const syncResult = await syncResponse.json();
      console.log('Sync triggered:', syncResult);

      // Show success message briefly
      setError('✓ Data sync triggered! Refreshing in 5 seconds...');

      // Wait a few seconds for data to be processed, then reload
      setTimeout(() => {
        if (selectedCourse) {
          loadCourseData(selectedCourse.id);
        } else if (onLoadCourses) {
          onLoadCourses();
        }
      }, 5000);

    } catch (err) {
      console.error('Refresh error:', err);
      setError(`Failed to refresh: ${err.message}`);
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

          {/* Course Selection */}
          {courses.length > 0 && (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Course
              </label>
              <select
                value={selectedCourse?.id || ''}
                onChange={(e) => {
                  const course = courses.find(c => c.id === e.target.value);
                  if (course) handleCourseSelect(course);
                }}
                className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              >
                {courses.map(course => (
                  <option key={course.id} value={course.id}>
                    {course.name}
                  </option>
                ))}
              </select>
            </div>
          )}

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
            <Users className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No courses found</h3>
            <p className="mt-1 text-sm text-gray-500">
              No course data is available. Make sure the Lambda function is running and has populated the S3 bucket.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default EnhancedTADashboard;
