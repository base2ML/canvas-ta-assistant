import React, { useState } from 'react';
import { RefreshCw, Users, BookOpen, Clock, User, AlertTriangle, CheckCircle, Eye, Calendar, ChevronDown, ChevronRight, AlertCircleIcon, XCircle } from 'lucide-react';

const TAGradingDashboard = ({ apiUrl, apiToken, backendUrl, courses, onBack, onLateDays }) => {
  const [taGroups, setTAGroups] = useState([]);
  const [ungradedSubmissions, setUngradedSubmissions] = useState([]);
  const [taAssignments, setTAAssignments] = useState({});
  const [assignmentStats, setAssignmentStats] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [totalUngraded, setTotalUngraded] = useState(0);
  const [loadTime, setLoadTime] = useState(null);
  const [selectedAssignment, setSelectedAssignment] = useState('all');
  const [selectedTA, setSelectedTA] = useState('all');
  const [courseInfo, setCourseInfo] = useState(null);
  const [expandedAssignments, setExpandedAssignments] = useState(new Set());

  // Use the first available course (since this tool is for single course use)
  const currentCourse = courses && courses.length > 0 ? courses[0] : null;

  // Utility function to handle API error responses consistently
  const handleApiError = (data, response) => {
    let errorMessage;
    if (data && typeof data === 'object') {
      if (data.detail) {
        errorMessage = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      } else if (data.message) {
        errorMessage = data.message;
      } else {
        errorMessage = JSON.stringify(data);
      }
    } else {
      errorMessage = data || response.statusText;
    }
    return errorMessage;
  };

  const fetchTAGroups = async (courseId) => {
    try {
      
      const response = await fetch(`${backendUrl}/api/ta-groups/${courseId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          base_url: apiUrl,
          api_token: apiToken
        })
      });


      const data = await response.json();

      if (!response.ok) {
        const errorMessage = handleApiError(data, response);
        throw new Error(`Failed to fetch TA groups (${response.status}): ${errorMessage}`);
      }

      setTAGroups(data.ta_groups || []);
      return data.course_info;
    } catch (err) {
      const errorMessage = err.message || (typeof err === 'string' ? err : JSON.stringify(err));
      throw new Error(`Error fetching TA groups: ${errorMessage}`);
    }
  };

  const fetchUngradedSubmissions = async (courseId) => {
    try {
      const response = await fetch(`${backendUrl}/api/ta-grading`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          base_url: apiUrl,
          api_token: apiToken,
          course_id: courseId
        })
      });

      const data = await response.json();

      if (!response.ok) {
        const errorMessage = handleApiError(data, response);
        throw new Error(`Failed to fetch ungraded submissions (${response.status}): ${errorMessage}`);
      }

      setUngradedSubmissions(data.ungraded_submissions || []);
      setTAAssignments(data.grading_distribution || {});
      setTotalUngraded(data.total_ungraded || 0);

      return data.course_info;
    } catch (err) {
      const errorMessage = err.message || (typeof err === 'string' ? err : JSON.stringify(err));
      throw new Error(`Error fetching ungraded submissions: ${errorMessage}`);
    }
  };

  const fetchAssignmentStatistics = async (courseId) => {
    try {
      const response = await fetch(`${backendUrl}/api/statistics/assignments/${courseId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          base_url: apiUrl,
          api_token: apiToken
        })
      });

      const data = await response.json();

      if (!response.ok) {
        const errorMessage = handleApiError(data, response);
        throw new Error(`Failed to fetch assignment statistics (${response.status}): ${errorMessage}`);
      }

      setAssignmentStats(data || []);

    } catch (err) {
      const errorMessage = err.message || (typeof err === 'string' ? err : JSON.stringify(err));
      throw new Error(`Error fetching assignment statistics: ${errorMessage}`);
    }
  };


  const loadCourseData = async (courseId) => {
    if (!courseId) return;

    const startTime = Date.now();
    setLoading(true);
    setError('');
    setLoadTime(null);

    try {
      let taGroupsInfo = null;
      let ungradedInfo = null;

      // Try TA Groups first
      try {
        taGroupsInfo = await fetchTAGroups(courseId);
      } catch (taGroupsError) {
        setError(`TA Groups error: ${taGroupsError.message}`);
      }

      // Try Ungraded Submissions
      try {
        ungradedInfo = await fetchUngradedSubmissions(courseId);
      } catch (ungradedError) {
        setError(prevError => prevError ? `${prevError}; Assignments error: ${ungradedError.message}` : `Assignments error: ${ungradedError.message}`);
      }

      // Fetch Assignment Statistics (this provides complete TA breakdown data)
      try {
        await fetchAssignmentStatistics(courseId);
      } catch (statisticsError) {
        setError(prevError => prevError ? `${prevError}; Statistics error: ${statisticsError.message}` : `Statistics error: ${statisticsError.message}`);
      }

      const endTime = Date.now();
      const duration = (endTime - startTime) / 1000;
      setLoadTime(duration);

      setCourseInfo(taGroupsInfo || ungradedInfo);

      // If neither call succeeded, throw an error
      if (!taGroupsInfo && !ungradedInfo) {
        throw new Error('Both API calls failed');
      }

    } catch (err) {
      const errorMessage = err.message || (typeof err === 'string' ? err : JSON.stringify(err));
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };


  const handleRefresh = () => {
    if (currentCourse) {
      loadCourseData(currentCourse.id);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Not submitted';
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const toggleAssignmentExpanded = (assignmentId) => {
    const newExpanded = new Set(expandedAssignments);
    if (newExpanded.has(assignmentId)) {
      newExpanded.delete(assignmentId);
    } else {
      newExpanded.add(assignmentId);
    }
    setExpandedAssignments(newExpanded);
  };

  const getTABreakdownForAssignment = (assignmentId) => {
    const assignment = assignmentStats.find(a => a.assignment_id.toString() === assignmentId);
    if (!assignment) return [];

    // Always use the backend-provided TA grading breakdown to ensure consistency
    return assignment.ta_grading_breakdown || [];
  };

  // Filter submissions based on selected filters
  const filteredSubmissions = ungradedSubmissions.filter(submission => {
    const matchesAssignment = selectedAssignment === 'all' || submission.assignment_id.toString() === selectedAssignment;
    const matchesTA = selectedTA === 'all' || submission.grader_name === selectedTA;
    return matchesAssignment && matchesTA;
  });

  // Get unique assignments for filter dropdown
  const uniqueAssignments = [...new Set(ungradedSubmissions.map(s => ({
    id: s.assignment_id,
    name: s.assignment_name
  })))];

  // Get unique TAs for filter dropdown
  const uniqueTAs = [...new Set(ungradedSubmissions
    .filter(s => s.grader_name)
    .map(s => s.grader_name))];

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg">
        {/* Header */}
        <div className="border-b border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center space-x-4">
                <button
                  onClick={onBack}
                  className="text-purple-500 hover:text-purple-600 flex items-center"
                >
                  ← Back to Assignment View
                </button>
                {onLateDays && (
                  <button
                    onClick={onLateDays}
                    className="text-orange-500 hover:text-orange-600 flex items-center"
                  >
                    <Calendar className="h-4 w-4 mr-1" />
                    Late Days Tracking
                  </button>
                )}
              </div>
              <h1 className="text-2xl font-bold text-gray-900 mt-2">TA Grading Dashboard</h1>
              <p className="text-gray-600 mt-1">Monitor ungraded assignments across TA groups</p>
              {courseInfo && (
                <div className="flex items-center mt-2 text-sm text-gray-500">
                  <BookOpen className="h-4 w-4 mr-1" />
                  {courseInfo.name} ({courseInfo.course_code})
                </div>
              )}
              {loadTime && (
                <div className="flex items-center mt-1 text-xs text-green-600">
                  ⚡ Loaded in {loadTime.toFixed(1)}s
                  {loadTime < 5 ? ' (Fast)' : loadTime < 15 ? ' (Moderate)' : ' (Slow)'}
                </div>
              )}
            </div>
            <div className="flex space-x-2">
              <button
                onClick={handleRefresh}
                disabled={loading || !currentCourse}
                className="flex items-center px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 transition-colors"
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          </div>
        </div>

        {/* Current Course Display */}
        {currentCourse && (
          <div className="p-6 border-b border-gray-200">
            <div className="flex items-center text-sm text-gray-600">
              <BookOpen className="h-4 w-4 mr-2" />
              Current Course: <span className="font-medium ml-1">{currentCourse.name}</span>
              {courseInfo && (
                <span className="text-gray-500 ml-2">({courseInfo.course_code})</span>
              )}
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="m-6 p-4 bg-red-100 border border-red-300 rounded-md text-red-700">
            {error}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="p-12 text-center">
            <RefreshCw className="h-8 w-8 animate-spin mx-auto text-blue-500 mb-4" />
            <p className="text-gray-600">Loading TA grading data...</p>
          </div>
        )}

        {/* Dashboard Content */}
        {!loading && currentCourse && (
          <>
            {/* Filters */}
            {ungradedSubmissions.length > 0 && (
              <div className="p-6 border-b border-gray-200">
                <div className="flex flex-wrap gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Assignment</label>
                    <select
                      value={selectedAssignment}
                      onChange={(e) => setSelectedAssignment(e.target.value)}
                      className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="all">All Assignments</option>
                      {uniqueAssignments.map(assignment => (
                        <option key={assignment.id} value={assignment.id.toString()}>
                          {assignment.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">TA</label>
                    <select
                      value={selectedTA}
                      onChange={(e) => setSelectedTA(e.target.value)}
                      className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="all">All TAs</option>
                      {uniqueTAs.map(ta => (
                        <option key={ta} value={ta}>
                          {ta}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* Assignment Grading Statistics */}
            {assignmentStats.length > 0 && (
              <div className="p-6 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Assignment Grading Progress</h3>
                <div className="space-y-3">
                  {assignmentStats
                    .sort((a, b) => {
                      // Sort by due date, assignments without due dates appear last
                      if (!a.due_at && !b.due_at) return 0;
                      if (!a.due_at) return 1;
                      if (!b.due_at) return -1;
                      return new Date(a.due_at) - new Date(b.due_at);
                    })
                    .map(assignment => {
                    const progressPercent = assignment.percentage_graded;
                    const isCompleted = progressPercent === 100;
                    const isExpanded = expandedAssignments.has(assignment.assignment_id);
                    
                    // Use the backend-provided TA grading breakdown directly
                    let taBreakdown = assignment.ta_grading_breakdown || [];
                    
                    const hasBreakdown = taBreakdown && taBreakdown.length > 0;
                    
                    
                    return (
                      <div
                        key={assignment.assignment_id}
                        className="border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
                      >
                        <div 
                          className="p-4 cursor-pointer"
                          onClick={() => toggleAssignmentExpanded(assignment.assignment_id)}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center space-x-3">
                                <div className={`p-2 rounded-full ${isCompleted ? 'bg-green-100' : 'bg-yellow-100'}`}>
                                  {isCompleted ? (
                                    <CheckCircle className="h-4 w-4 text-green-600" />
                                  ) : (
                                    <Clock className="h-4 w-4 text-yellow-600" />
                                  )}
                                </div>
                                <div className="flex-1">
                                  <div className="flex items-center justify-between">
                                    <div>
                                      <h4 className="font-medium text-gray-900">{assignment.assignment_name}</h4>
                                      <p className="text-sm text-gray-600">
                                        {assignment.graded_submissions}/{assignment.total_submissions} submissions graded
                                      </p>
                                    </div>
                                    <button className="ml-2 p-1 hover:bg-gray-100 rounded">
                                      {isExpanded ? (
                                        <ChevronDown className="h-4 w-4 text-gray-500" />
                                      ) : (
                                        <ChevronRight className="h-4 w-4 text-gray-500" />
                                      )}
                                    </button>
                                  </div>
                                </div>
                              </div>
                              
                              <div className="ml-9 mt-3">
                                {/* Progress Bar */}
                                <div className="w-full bg-gray-200 rounded-full h-2">
                                  <div
                                    className={`h-2 rounded-full transition-all duration-300 ${
                                      isCompleted ? 'bg-green-500' : 'bg-yellow-500'
                                    }`}
                                    style={{ width: `${progressPercent}%` }}
                                  ></div>
                                </div>
                                <div className="flex justify-between items-center mt-2 text-sm text-gray-500">
                                  <span>{progressPercent}% Complete</span>
                                  {assignment.due_at && (
                                    <div className="flex items-center">
                                      <Calendar className="h-4 w-4 mr-1" />
                                      Due: {formatDate(assignment.due_at)}
                                    </div>
                                  )}
                                </div>
                                <div className="text-xs text-gray-400 mt-1">
                                  {hasBreakdown ? 
                                    `Click to view TA grading breakdown (${taBreakdown?.length || 0} TAs assigned)` : 
                                    `Click to view details (no TA assignments found in Canvas)`
                                  }
                                </div>
                              </div>
                            </div>
                            
                            <div className="text-right ml-4">
                              <div className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                isCompleted 
                                  ? 'bg-green-100 text-green-800' 
                                  : 'bg-yellow-100 text-yellow-800'
                              }`}>
                                {isCompleted ? 'Complete' : `${assignment.ungraded_submissions} Pending`}
                              </div>
                              {assignment.html_url && (
                                <a
                                  href={assignment.html_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="flex items-center text-blue-500 hover:text-blue-600 text-sm mt-2"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  <Eye className="h-4 w-4 mr-1" />
                                  View Assignment
                                </a>
                              )}
                            </div>
                          </div>
                        </div>
                        
                        {/* TA Grading Breakdown - Expandable */}
                        {isExpanded && (
                          <div className="border-t border-gray-100 p-4 bg-gray-50">
                            <h5 className="font-medium text-gray-900 mb-3">TA Grading Breakdown</h5>
                            {hasBreakdown ? (
                              <div className="overflow-x-auto">
                                <table className="min-w-full bg-white border border-gray-200 rounded-lg">
                                  <thead className="bg-gray-50">
                                    <tr>
                                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">TA Name</th>
                                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Students</th>
                                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Graded</th>
                                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Progress</th>
                                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">On Time</th>
                                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Late</th>
                                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Missing</th>
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-gray-200">
                                    {taBreakdown.map((taStats, index) => (
                                      <tr key={index} className="hover:bg-gray-50">
                                        <td className="px-4 py-3 text-sm font-medium text-gray-900">{taStats.ta_name}</td>
                                        <td className="px-4 py-3 text-sm text-gray-600">{taStats.total_assigned}</td>
                                        <td className="px-4 py-3 text-sm text-gray-600">{taStats.graded}/{taStats.total_assigned}</td>
                                        <td className="px-4 py-3 text-sm">
                                          <div className="flex items-center space-x-2">
                                            <div className="w-16 bg-gray-200 rounded-full h-2">
                                              <div
                                                className={`h-2 rounded-full ${
                                                  taStats.percentage_complete === 100 ? 'bg-green-500' : 'bg-yellow-500'
                                                }`}
                                                style={{ width: `${taStats.percentage_complete}%` }}
                                              ></div>
                                            </div>
                                            <span className={`text-xs font-medium ${
                                              taStats.percentage_complete === 100 ? 'text-green-600' : 'text-yellow-600'
                                            }`}>
                                              {taStats.percentage_complete}%
                                            </span>
                                          </div>
                                        </td>
                                        <td className="px-4 py-3 text-sm text-green-600">{taStats.submitted_on_time}</td>
                                        <td className="px-4 py-3 text-sm text-yellow-600">{taStats.submitted_late}</td>
                                        <td className="px-4 py-3 text-sm text-red-600">{taStats.not_submitted}</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            ) : (
                              <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3">
                                <div className="flex items-center">
                                  <AlertTriangle className="h-4 w-4 text-yellow-600 mr-2" />
                                  <span className="text-sm text-yellow-700">
                                    No TA assignments found for this assignment in Canvas.
                                  </span>
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default TAGradingDashboard;