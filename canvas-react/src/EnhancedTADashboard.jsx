import React, { useState, useEffect, useMemo } from 'react';
import AssignmentStatusBreakdown from './components/AssignmentStatusBreakdown';
import { apiFetch } from './api';

const EnhancedTADashboard = ({ courses = [], onLoadCourses, activeCourseId, refreshTrigger, taBreakdownMode = 'group' }) => {
  // Use courses from props, but keep local state for selection
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [groups, setGroups] = useState([]);
  const [taUsers, setTaUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

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
      const [assignmentsData, submissionsData, groupsData, taUsersData] = await Promise.all([
        apiFetch(`/api/canvas/assignments/${courseId}`),
        apiFetch(`/api/canvas/submissions/${courseId}`),
        apiFetch(`/api/canvas/groups/${courseId}`),
        apiFetch(`/api/canvas/ta-users/${courseId}`).catch(() => ({ ta_users: [] })),
      ]);

      setAssignments(assignmentsData.assignments || []);
      setSubmissions(submissionsData.submissions || []);
      setGroups(groupsData.groups || []);
      setTaUsers(taUsersData.ta_users || []);
    } catch (err) {
      console.error('Error loading course data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initialize or reset selected course when courses, activeCourseId, or refreshTrigger changes.
  // refreshTrigger is incremented by the global header on each successful sync, causing a reload.
  useEffect(() => {
    if (courses && courses.length > 0) {
      const target = courses.find(c => String(c.id) === String(activeCourseId)) || courses[0];
      setSelectedCourse(target);
      loadCourseData(target.id);
    }
  }, [courses, activeCourseId, loadCourseData, refreshTrigger]);

  // Trigger parent to load courses if empty
  useEffect(() => {
    if ((!courses || courses.length === 0) && onLoadCourses) {
      onLoadCourses();
    }
  }, [courses, onLoadCourses]);


  // Build a map from group name → TA user ID for actual-grader mode.
  // Canvas groups are named after the TA (e.g. "Smith, Jane"). We find the
  // ta_users entry whose name matches the group name (exact, then case-insensitive)
  // and store their Canvas user id so we can match against grader_id on submissions.
  const groupNameToTaUserId = useMemo(() => {
    const map = {};
    groups.forEach(group => {
      const groupName = group.name;
      // Exact match first
      let match = taUsers.find(u => u.name === groupName);
      // Case-insensitive fallback
      if (!match) {
        match = taUsers.find(u => u.name.toLowerCase() === groupName.toLowerCase());
      }
      if (match) {
        map[groupName] = match.id;
      }
    });
    return map;
  }, [groups, taUsers]);

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
        // Branch graded count based on taBreakdownMode
        let graded;
        if (taBreakdownMode === 'actual') {
          // Count submissions graded by this TA using grader_id (most reliable).
          // groupNameToTaUserId maps group name → ta_users.id (Canvas user id).
          // Fall back to grader_name match if no id mapping exists for this group.
          const taUserId = groupNameToTaUserId[taName];
          if (taUserId !== undefined) {
            graded = assignmentSubmissions.filter(
              s => s.grader_id === taUserId && s.submitted_at
            ).length;
          } else {
            // Fallback: try name match (works when group name equals TA's Canvas name)
            graded = assignmentSubmissions.filter(
              s => s.grader_name === taName && s.submitted_at
            ).length;
          }
        } else {
          // Group assignment mode (default): only count as graded if actually submitted AND graded
          graded = taSubmissions.filter(s => s.workflow_state === 'graded' && s.submitted_at).length;
        }

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
  }, [assignments, submissions, groups, buildTAAssignments, taBreakdownMode, groupNameToTaUserId]);

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

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white shadow-sm rounded-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-3xl font-bold text-gray-900">TA Grading Dashboard</h1>
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
