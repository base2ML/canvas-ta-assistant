import React, { useState, useEffect, useMemo } from 'react';
import { RefreshCw, Users, Filter, TrendingUp, CheckCircle, XCircle, Clock } from 'lucide-react';
import SubmissionStatusCards from './components/SubmissionStatusCards';
import AssignmentStatusBreakdown from './components/AssignmentStatusBreakdown';

const EnhancedTADashboard = ({ backendUrl, getAuthHeaders, courses = [], onLoadCourses }) => {
  // Use courses from props, but keep local state for selection
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [users, setUsers] = useState([]);
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState(null);
  const [submissionMetrics, setSubmissionMetrics] = useState(null);

  // Filters
  const [selectedAssignment, setSelectedAssignment] = useState('all');

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
          setUsers(canvasData.users || []);
          setGroups(canvasData.groups || []);
        }
        // Handle direct data mode (local mock data)
        else if (urlData.assignments) {
          setAssignments(urlData.assignments || []);
          // For mock mode, we need to fetch additional data
          const [submissionsRes, usersRes, groupsRes] = await Promise.all([
            fetch(`${backendUrl}/api/canvas/submissions/${selectedCourse.id}`, { headers }),
            fetch(`${backendUrl}/api/canvas/users/${selectedCourse.id}`, { headers }),
            fetch(`${backendUrl}/api/canvas/groups/${selectedCourse.id}`, { headers })
          ]);

          if (submissionsRes.ok) {
            const subData = await submissionsRes.json();
            setSubmissions(subData.submissions || []);
          }
          if (usersRes.ok) {
            const userData = await usersRes.json();
            setUsers(userData.users || []);
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

  const loadSubmissionMetrics = React.useCallback(async (courseId, assignmentId = null) => {
    if (!courseId) return;

    try {
      const headers = await getAuthHeaders();
      const params = new URLSearchParams();
      if (assignmentId && assignmentId !== 'all') {
        params.append('assignment_id', assignmentId);
      }

      const url = `${backendUrl}/api/dashboard/submission-status/${courseId}?${params}`;
      const response = await fetch(url, { headers });

      if (!response.ok) {
        throw new Error(`Failed to load metrics: ${response.statusText}`);
      }

      const data = await response.json();
      setSubmissionMetrics(data);
    } catch (err) {
      console.error('Error loading submission metrics:', err);
      setError(err.message);
    }
  }, [backendUrl, getAuthHeaders]);

  useEffect(() => {
    if (selectedCourse) {
      loadSubmissionMetrics(selectedCourse.id, selectedAssignment);
    }
  }, [selectedCourse, selectedAssignment, loadSubmissionMetrics]);

  // Compute TA statistics with assignment filtering
  const taStats = useMemo(() => {
    if (!submissions.length || !users.length || !groups.length) return [];

    // Build TA assignments from actual Canvas groups
    const taAssignments = buildTAAssignments(groups);

    // Filter submissions by assignment if selected
    const filteredSubmissions = selectedAssignment === 'all'
      ? submissions
      : submissions.filter(s => String(s.assignment_id) === selectedAssignment);

    // Calculate stats for each TA
    const stats = [];
    Object.entries(taAssignments).forEach(([taName, studentIds]) => {
      const taSubmissions = filteredSubmissions.filter(s =>
        studentIds.has(String(s.user_id))
      );

      const graded = taSubmissions.filter(s => s.workflow_state === 'graded').length;
      const ungraded = taSubmissions.filter(s => s.workflow_state !== 'graded' && s.workflow_state === 'submitted').length;
      const total = graded + ungraded;
      const completionRate = total > 0 ? (graded / total) * 100 : 0;

      stats.push({
        taName,
        graded,
        ungraded,
        total,
        completionRate: completionRate.toFixed(1),
        studentCount: studentIds.size
      });
    });

    return stats.sort((a, b) => a.taName.localeCompare(b.taName));
  }, [submissions, users, groups, selectedAssignment, buildTAAssignments]);

  const handleCourseSelect = async (course) => {
    setSelectedCourse(course);
    setAssignments([]);
    setSubmissions([]);
    setUsers([]);
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

  // Overall statistics
  const overallStats = useMemo(() => {
    const filteredSubmissions = selectedAssignment === 'all'
      ? submissions
      : submissions.filter(s => String(s.assignment_id) === selectedAssignment);

    const graded = filteredSubmissions.filter(s => s.workflow_state === 'graded').length;
    const ungraded = filteredSubmissions.filter(s => s.workflow_state !== 'graded' && s.workflow_state === 'submitted').length;
    const total = graded + ungraded;

    return {
      total,
      graded,
      ungraded,
      completionRate: total > 0 ? ((graded / total) * 100).toFixed(1) : 0
    };
  }, [submissions, selectedAssignment]);

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
            {/* Filters */}
            <div className="bg-white shadow-sm rounded-lg p-6 mb-6">
              <div className="flex items-center space-x-2 mb-4">
                <Filter className="h-5 w-5 text-blue-600" />
                <h2 className="text-xl font-semibold text-gray-900">Filters</h2>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Assignment
                  </label>
                  <select
                    value={selectedAssignment}
                    onChange={(e) => setSelectedAssignment(e.target.value)}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="all">All Assignments</option>
                    {assignments.map(assignment => (
                      <option key={assignment.id} value={String(assignment.id)}>
                        {assignment.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* Submission Status Cards */}
            {submissionMetrics && (
              <SubmissionStatusCards metrics={submissionMetrics.overall_metrics} />
            )}

            {/* Assignment Status Breakdown */}
            {submissionMetrics && submissionMetrics.by_assignment && (
              <AssignmentStatusBreakdown assignmentMetrics={submissionMetrics.by_assignment} />
            )}

            {/* Overall Statistics */}
            <div className="bg-white shadow-sm rounded-lg p-6 mb-6">
              <div className="flex items-center space-x-2 mb-4">
                <TrendingUp className="h-5 w-5 text-green-600" />
                <h2 className="text-xl font-semibold text-gray-900">Overall Statistics</h2>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-blue-50 rounded-lg">
                  <div className="text-3xl font-bold text-blue-600">{overallStats.total}</div>
                  <div className="text-sm text-gray-600 mt-1">Total Submissions</div>
                </div>
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <div className="text-3xl font-bold text-green-600">{overallStats.graded}</div>
                  <div className="text-sm text-gray-600 mt-1">Graded</div>
                </div>
                <div className="text-center p-4 bg-orange-50 rounded-lg">
                  <div className="text-3xl font-bold text-orange-600">{overallStats.ungraded}</div>
                  <div className="text-sm text-gray-600 mt-1">Ungraded</div>
                </div>
                <div className="text-center p-4 bg-purple-50 rounded-lg">
                  <div className="text-3xl font-bold text-purple-600">{overallStats.completionRate}%</div>
                  <div className="text-sm text-gray-600 mt-1">Completion Rate</div>
                </div>
              </div>
            </div>

            {/* TA Breakdown Table */}
            <div className="bg-white shadow-sm rounded-lg p-6">
              <div className="flex items-center space-x-2 mb-4">
                <Users className="h-5 w-5 text-indigo-600" />
                <h2 className="text-xl font-semibold text-gray-900">TA Workload Breakdown</h2>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        TA Name
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Students
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Total
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Graded
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Ungraded
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Completion %
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {taStats.map((ta, index) => (
                      <tr key={index} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {ta.taName}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                          {ta.studentCount}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-semibold">
                          {ta.total}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-green-600 font-medium">
                          {ta.graded}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-orange-600 font-medium">
                          {ta.ungraded}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <div className="flex items-center">
                            <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                              <div
                                className="bg-green-600 h-2 rounded-full"
                                style={{ width: `${ta.completionRate}%` }}
                              />
                            </div>
                            <span className="text-gray-900 font-medium">{ta.completionRate}%</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          {parseFloat(ta.completionRate) >= 90 ? (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                              <CheckCircle className="h-3 w-3 mr-1" />
                              On Track
                            </span>
                          ) : parseFloat(ta.completionRate) >= 50 ? (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                              In Progress
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                              <XCircle className="h-3 w-3 mr-1" />
                              Needs Attention
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}

                    {taStats.length === 0 && (
                      <tr>
                        <td colSpan="7" className="px-6 py-8 text-center text-gray-500">
                          No TA data available. Loading...
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
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
