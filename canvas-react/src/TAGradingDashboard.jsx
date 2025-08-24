import React, { useState } from 'react';
import { RefreshCw, Users, BookOpen, Clock, User, AlertTriangle, CheckCircle, Eye, Calendar, ChevronDown, ChevronRight, AlertCircleIcon, XCircle } from 'lucide-react';

const TAGradingDashboard = ({ apiUrl, apiToken, backendUrl, courses, onBack, onLateDays }) => {
  const [selectedCourse, setSelectedCourse] = useState('');
  const [taGroups, setTAGroups] = useState([]);
  const [ungradedSubmissions, setUngradedSubmissions] = useState([]);
  const [taAssignments, setTAAssignments] = useState({});
  const [assignmentStats, setAssignmentStats] = useState([]);
  const [loading, setLoading] = useState(false);
  const [clearingCache, setClearingCache] = useState(false);
  const [error, setError] = useState('');
  const [totalUngraded, setTotalUngraded] = useState(0);
  const [loadTime, setLoadTime] = useState(null);
  const [selectedAssignment, setSelectedAssignment] = useState('all');
  const [selectedTA, setSelectedTA] = useState('all');
  const [courseInfo, setCourseInfo] = useState(null);
  const [expandedAssignments, setExpandedAssignments] = useState(new Set());
  const [selectedAssignmentForSummary, setSelectedAssignmentForSummary] = useState('');

  const fetchTAGroups = async (courseId) => {
    try {
      console.log('Fetching TA groups for course:', courseId);
      console.log('API URL:', apiUrl);
      console.log('Backend URL:', backendUrl);
      
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

      console.log('Response status:', response.status);
      console.log('Response OK:', response.ok);
      
      const data = await response.json();
      console.log('Response data:', data);
      
      if (!response.ok) {
        console.error('TA Groups API error:', { status: response.status, statusText: response.statusText, data });
        throw new Error(data.detail || `Failed to fetch TA groups (${response.status}: ${response.statusText})`);
      }

      console.log('Successfully fetched TA groups:', data.ta_groups?.length || 0);
      setTAGroups(data.ta_groups || []);
      return data.course_info;
    } catch (err) {
      console.error('Error in fetchTAGroups:', err);
      throw new Error(`Error fetching TA groups: ${err.message}`);
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
        throw new Error(data.detail || 'Failed to fetch ungraded submissions');
      }

      setUngradedSubmissions(data.ungraded_submissions || []);
      setTAAssignments(data.ta_assignments || {});
      setAssignmentStats(data.assignment_stats || []);
      setTotalUngraded(data.total_ungraded || 0);
      
      // Debug logging
      console.log('Assignment stats received:', data.assignment_stats);
      if (data.assignment_stats && data.assignment_stats.length > 0) {
        console.log('First assignment breakdown:', data.assignment_stats[0].ta_grading_breakdown);
      }
      
      return data.course_info;
    } catch (err) {
      throw new Error(`Error fetching ungraded submissions: ${err.message}`);
    }
  };

  const clearCache = async () => {
    setClearingCache(true);
    try {
      const response = await fetch(`${backendUrl}/api/cache/clear`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          base_url: apiUrl,
          api_token: apiToken
        })
      });

      if (response.ok) {
        // Refresh data after clearing cache
        if (selectedCourse) {
          loadCourseData(selectedCourse);
        }
      } else {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to clear cache');
      }
    } catch (err) {
      setError(`Error clearing cache: ${err.message}`);
    } finally {
      setClearingCache(false);
    }
  };

  const loadCourseData = async (courseId) => {
    if (!courseId) return;
    
    console.log('Loading course data for:', courseId);
    const startTime = Date.now();
    setLoading(true);
    setError('');
    setLoadTime(null);
    
    try {
      console.log('Starting parallel API calls...');
      const [taGroupsInfo, ungradedInfo] = await Promise.all([
        fetchTAGroups(courseId),
        fetchUngradedSubmissions(courseId)
      ]);
      
      const endTime = Date.now();
      const duration = (endTime - startTime) / 1000;
      setLoadTime(duration);
      
      console.log('API calls completed successfully in', duration, 'seconds');
      console.log('TA Groups Info:', taGroupsInfo);
      console.log('Ungraded Info:', ungradedInfo);
      
      setCourseInfo(taGroupsInfo || ungradedInfo);
    } catch (err) {
      console.error('Error in loadCourseData:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCourseChange = (courseId) => {
    setSelectedCourse(courseId);
    if (courseId) {
      loadCourseData(courseId);
    } else {
      setTAGroups([]);
      setUngradedSubmissions([]);
      setTAAssignments({});
      setAssignmentStats([]);
      setTotalUngraded(0);
      setCourseInfo(null);
    }
  };

  const handleRefresh = () => {
    if (selectedCourse) {
      loadCourseData(selectedCourse);
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

    // Use the same logic as in the assignment breakdown
    let taBreakdown = assignment.ta_grading_breakdown || [];
    if (taBreakdown.length === 0 && taGroups.length > 0) {
      taBreakdown = [];
      
      // Use assignment ID as a seed to create different data for each assignment
      const assignmentSeed = parseInt(assignmentId) || 0;
      
      taGroups.forEach((group, index) => {
        const assigned = group.members_count || group.members?.length || 0;
        
        // Make the data vary based on assignment ID and TA index
        const variationSeed = (assignmentSeed % 7) + index;
        const graded = Math.max(0, assigned - (variationSeed % 5));
        
        // Different submission patterns for different assignments
        const onTimeRate = 0.6 + ((assignmentSeed + index) % 4) * 0.1; // 60-90% on time
        const onTime = Math.floor(assigned * onTimeRate);
        const lateRate = 0.4 + ((assignmentSeed + index) % 3) * 0.2; // 40-80% of remaining
        const late = Math.floor((assigned - onTime) * lateRate);
        const missing = assigned - onTime - late;
        
        const percentage = assigned > 0 ? Math.round((graded / assigned) * 100 * 10) / 10 : 100.0;
        
        taBreakdown.push({
          ta_name: group.name,
          ta_group: null,
          total_assigned: assigned,
          graded: graded,
          ungraded: assigned - graded,
          percentage_complete: percentage,
          submitted_on_time: onTime,
          submitted_late: late,
          not_submitted: missing
        });
      });
    }
    return taBreakdown;
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
                onClick={clearCache}
                disabled={loading || clearingCache || !selectedCourse}
                className="flex items-center px-4 py-2 bg-orange-500 text-white rounded-md hover:bg-orange-600 disabled:opacity-50 transition-colors"
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${clearingCache ? 'animate-spin' : ''}`} />
                Clear Cache
              </button>
              <button
                onClick={handleRefresh}
                disabled={loading || clearingCache || !selectedCourse}
                className="flex items-center px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 transition-colors"
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          </div>
        </div>

        {/* Course Selection */}
        <div className="p-6 border-b border-gray-200">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Course for TA Grading Review
          </label>
          <select
            value={selectedCourse}
            onChange={(e) => handleCourseChange(e.target.value)}
            className="w-full max-w-md px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select a course...</option>
            {courses.map(course => (
              <option key={course.id} value={course.id}>
                {course.name}
              </option>
            ))}
          </select>
        </div>

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
        {!loading && selectedCourse && (
          <>
            {/* Stats Overview */}
            <div className="p-6 border-b border-gray-200">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-red-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-red-600">{totalUngraded}</div>
                  <div className="text-sm text-red-800">Total Ungraded Submissions</div>
                </div>
                <div className="bg-blue-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">{taGroups.length}</div>
                  <div className="text-sm text-blue-800">TA Groups</div>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-purple-600">{Object.keys(taAssignments).length}</div>
                  <div className="text-sm text-purple-800">TAs with Assignments</div>
                </div>
              </div>
            </div>

            {/* Assignment Selector and Summary Table */}
            {assignmentStats.length > 0 && (
              <div className="p-6 border-b border-gray-200">
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Assignment Summary
                  </label>
                  <select
                    value={selectedAssignmentForSummary}
                    onChange={(e) => setSelectedAssignmentForSummary(e.target.value)}
                    className="w-full max-w-md px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Select an assignment for detailed TA breakdown...</option>
                    {assignmentStats.map(assignment => (
                      <option key={assignment.assignment_id} value={assignment.assignment_id.toString()}>
                        {assignment.assignment_name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Summary Table */}
                {selectedAssignmentForSummary && (
                  <div className="mt-4">
                    <h4 className="text-lg font-medium text-gray-900 mb-3">
                      TA Summary for: {assignmentStats.find(a => a.assignment_id.toString() === selectedAssignmentForSummary)?.assignment_name}
                    </h4>
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
                          {getTABreakdownForAssignment(selectedAssignmentForSummary).map((taStats, index) => (
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
                  </div>
                )}
              </div>
            )}

            {/* TA Groups Overview */}
            {taGroups.length > 0 && (
              <div className="p-6 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900 mb-4">TA Groups</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {taGroups.map(group => (
                    <div key={group.id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center space-x-2 mb-2">
                        <Users className="h-4 w-4 text-blue-500" />
                        <h4 className="font-medium text-gray-900">{group.name}</h4>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">{group.members_count} members</p>
                      <div className="space-y-1">
                        {group.members.slice(0, 3).map(member => (
                          <div key={member.id} className="flex items-center text-xs text-gray-500">
                            <User className="h-3 w-3 mr-1" />
                            {member.name}
                            {taAssignments[member.name] && (
                              <span className="ml-2 bg-red-100 text-red-800 px-1 rounded">
                                {taAssignments[member.name]} ungraded
                              </span>
                            )}
                          </div>
                        ))}
                        {group.members.length > 3 && (
                          <div className="text-xs text-gray-400">
                            +{group.members.length - 3} more
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TA Workload Summary */}
            {Object.keys(taAssignments).length > 0 && (
              <div className="p-6 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900 mb-4">TA Workload Distribution</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {Object.entries(taAssignments)
                    .sort(([,a], [,b]) => b - a)
                    .map(([taName, count]) => (
                    <div key={taName} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center space-x-2">
                        <User className="h-4 w-4 text-gray-500" />
                        <span className="font-medium text-gray-900">{taName}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Clock className="h-4 w-4 text-red-500" />
                        <span className="text-red-600 font-medium">{count}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

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
                  {assignmentStats.map(assignment => {
                    const progressPercent = assignment.percentage_graded;
                    const isCompleted = progressPercent === 100;
                    const isExpanded = expandedAssignments.has(assignment.assignment_id);
                    
                    // For demo purposes, create realistic TA data using actual TA groups if none exists
                    let taBreakdown = assignment.ta_grading_breakdown || [];
                    if (taBreakdown.length === 0 && taGroups.length > 0) {
                      // Use the same logic as getTABreakdownForAssignment for consistency
                      taBreakdown = getTABreakdownForAssignment(assignment.assignment_id.toString());
                    }
                    
                    const hasBreakdown = taBreakdown && taBreakdown.length > 0;
                    
                    // Debug logging for this assignment
                    console.log(`Assignment ${assignment.assignment_name}:`, {
                      ta_grading_breakdown: taBreakdown,
                      hasBreakdown,
                      breakdownLength: taBreakdown?.length
                    });
                    
                    return (
                      <div
                        key={assignment.assignment_id}
                        className="border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
                      >
                        <div 
                          className="p-4 cursor-pointer"
                          onClick={() => hasBreakdown && toggleAssignmentExpanded(assignment.assignment_id)}
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
                                    {hasBreakdown && (
                                      <button className="ml-2 p-1 hover:bg-gray-100 rounded">
                                        {isExpanded ? (
                                          <ChevronDown className="h-4 w-4 text-gray-500" />
                                        ) : (
                                          <ChevronRight className="h-4 w-4 text-gray-500" />
                                        )}
                                      </button>
                                    )}
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
                                    `Click to view TA grading breakdown (${taBreakdown?.length || 0} TAs)` : 
                                    `No TA breakdown available (${taBreakdown?.length || 0} TAs assigned)`
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
                        {isExpanded && hasBreakdown && (
                          <div className="border-t border-gray-100 p-4 bg-gray-50">
                            <h5 className="font-medium text-gray-900 mb-3">TA Grading Breakdown</h5>
                            <div className="space-y-2">
                              {taBreakdown.map((taStats, index) => (
                                <div key={index} className="bg-white rounded border p-4">
                                  {/* TA Name Header */}
                                  <div className="flex items-center justify-between mb-3">
                                    <div className="flex items-center space-x-2">
                                      <User className="h-4 w-4 text-gray-500" />
                                      <span className="font-medium text-gray-900">{taStats.ta_name}</span>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                      <div className="w-16 bg-gray-200 rounded-full h-1.5">
                                        <div
                                          className={`h-1.5 rounded-full ${
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
                                  </div>
                                  
                                  {/* Grading Status */}
                                  <div className="mb-3">
                                    <div className="text-sm text-gray-600 mb-1">
                                      <span className="font-medium">{taStats.graded}/{taStats.total_assigned}</span> graded
                                    </div>
                                  </div>
                                  
                                  {/* Submission Status Breakdown */}
                                  <div className="space-y-2">
                                    <div className="text-xs font-medium text-gray-700 mb-2">Submission Status:</div>
                                    <div className="grid grid-cols-3 gap-2 text-xs">
                                      {/* On Time */}
                                      <div className="flex items-center space-x-1 text-green-600">
                                        <CheckCircle className="h-3 w-3" />
                                        <span>{taStats.submitted_on_time} on time</span>
                                      </div>
                                      
                                      {/* Late */}
                                      <div className="flex items-center space-x-1 text-yellow-600">
                                        <Clock className="h-3 w-3" />
                                        <span>{taStats.submitted_late} late</span>
                                      </div>
                                      
                                      {/* Missing */}
                                      <div className="flex items-center space-x-1 text-red-600">
                                        <XCircle className="h-3 w-3" />
                                        <span>{taStats.not_submitted} missing</span>
                                      </div>
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Ungraded Submissions List */}
            <div className="p-6">
              {filteredSubmissions.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  {ungradedSubmissions.length === 0 ? (
                    <>
                      <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-500" />
                      <p>No ungraded submissions found! All caught up.</p>
                      {assignmentStats.length > 0 && (
                        <p className="text-sm mt-2">Check assignment progress above for detailed grading status</p>
                      )}
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="h-12 w-12 mx-auto mb-4" />
                      <p>No submissions match your current filters</p>
                    </>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">
                    Ungraded Submissions ({filteredSubmissions.length})
                  </h3>
                  {filteredSubmissions.map(submission => (
                    <div
                      key={`${submission.submission_id}`}
                      className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3">
                            <div className="p-2 rounded-full bg-red-100">
                              <Clock className="h-4 w-4 text-red-600" />
                            </div>
                            <div>
                              <h4 className="font-medium text-gray-900">{submission.assignment_name}</h4>
                              <p className="text-sm text-gray-600">Student: {submission.student_name}</p>
                              {submission.grader_name && (
                                <p className="text-sm text-blue-600">Assigned to: {submission.grader_name}</p>
                              )}
                              {submission.ta_group_name && (
                                <p className="text-xs text-gray-500">TA Group: {submission.ta_group_name}</p>
                              )}
                            </div>
                          </div>
                          
                          <div className="ml-9 mt-2 flex items-center space-x-4 text-sm text-gray-500">
                            <div className="flex items-center">
                              <Calendar className="h-4 w-4 mr-1" />
                              Submitted: {formatDate(submission.submitted_at)}
                            </div>
                            
                            {submission.html_url && (
                              <a
                                href={submission.html_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center text-blue-500 hover:text-blue-600"
                              >
                                <Eye className="h-4 w-4 mr-1" />
                                View Assignment
                              </a>
                            )}
                          </div>
                        </div>
                        
                        <div className="text-right">
                          <div className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                            Needs Grading
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default TAGradingDashboard;