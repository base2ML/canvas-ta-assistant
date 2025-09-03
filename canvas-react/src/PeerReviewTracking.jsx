import React, { useState, useEffect, useCallback } from 'react';
import { ArrowLeft, RefreshCw, Users, Calendar, AlertCircle, CheckCircle, Clock, XCircle } from 'lucide-react';

const PeerReviewTracking = ({ 
  apiUrl, 
  apiToken, 
  backendUrl, 
  courses, 
  onBack
}) => {
  const [selectedCourse, setSelectedCourse] = useState('');
  const [assignments, setAssignments] = useState([]);
  const [selectedAssignment, setSelectedAssignment] = useState('');
  const [deadline, setDeadline] = useState('');
  const [penaltyPerReview, setPenaltyPerReview] = useState(4);
  const [peerReviewData, setPeerReviewData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [loadingAssignments, setLoadingAssignments] = useState(false);

  const fetchCourseAssignments = useCallback(async () => {
    setLoadingAssignments(true);
    setError('');
    setAssignments([]);
    
    try {
      const response = await fetch(`${backendUrl}/api/assignments`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          base_url: apiUrl,
          api_token: apiToken,
          course_ids: [selectedCourse]
        })
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to fetch assignments');
      }


      // Filter for assignments that might have peer reviews (Proposal, Final Project, etc.)
      // If no filtered assignments found, show all assignments for debugging
      const peerReviewAssignments = data.assignments.filter(assignment => 
        assignment.name.toLowerCase().includes('proposal') || 
        assignment.name.toLowerCase().includes('final project') ||
        assignment.name.toLowerCase().includes('peer review') ||
        assignment.name.toLowerCase().includes('peer-review') ||
        assignment.name.toLowerCase().includes('project') ||
        assignment.name.toLowerCase().includes('report') ||
        assignment.name.toLowerCase().includes('assignment')
      );

      // If still no matches, show all assignments (for debugging)
      const finalAssignments = peerReviewAssignments.length > 0 ? peerReviewAssignments : data.assignments;

      setAssignments(finalAssignments);

    } catch (err) {
      setError(`Error loading assignments: ${err.message}`);
    } finally {
      setLoadingAssignments(false);
    }
  }, [apiUrl, apiToken, backendUrl, selectedCourse]);

  // Load course assignments when course is selected
  useEffect(() => {
    if (selectedCourse && apiUrl && apiToken && backendUrl) {
      fetchCourseAssignments();
    }
  }, [selectedCourse, apiUrl, apiToken, backendUrl, fetchCourseAssignments]);

  const fetchPeerReviewData = async () => {
    if (!selectedCourse || !selectedAssignment || !deadline) {
      setError('Please select course, assignment, and deadline');
      return;
    }

    setLoading(true);
    setError('');
    setPeerReviewData(null);

    try {

      const response = await fetch(`${backendUrl}/api/peer-reviews`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          base_url: apiUrl,
          api_token: apiToken,
          course_id: selectedCourse,
          assignment_id: parseInt(selectedAssignment),
          deadline: new Date(deadline).toISOString(), // Ensure proper ISO 8601 format
          penalty_per_review: penaltyPerReview
        })
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to fetch peer review data');
      }

      setPeerReviewData(data);

    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    if (peerReviewData) {
      fetchPeerReviewData();
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'on_time':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'late':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'missing':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'on_time':
        return 'text-green-700 bg-green-100';
      case 'late':
        return 'text-yellow-700 bg-yellow-100';
      case 'missing':
        return 'text-red-700 bg-red-100';
      default:
        return 'text-gray-700 bg-gray-100';
    }
  };

  const formatDateTime = (dateTimeStr) => {
    if (!dateTimeStr) return 'Not submitted';
    try {
      return new Date(dateTimeStr).toLocaleString();
    } catch {
      return dateTimeStr;
    }
  };

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg">
        {/* Header */}
        <div className="border-b border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <button
                onClick={onBack}
                className="mr-4 p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
              >
                <ArrowLeft className="h-5 w-5" />
              </button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Peer Review Lateness Tracker</h1>
                <p className="text-gray-600 mt-1">Track peer review submissions and calculate penalties for late or missing reviews</p>
              </div>
            </div>
            <div className="flex space-x-2">
              <button
                onClick={handleRefresh}
                disabled={loading}
                className="flex items-center px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 transition-colors"
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          </div>
        </div>

        {/* Configuration Form */}
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Configure Peer Review Tracking</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Course
              </label>
              <select
                value={selectedCourse}
                onChange={(e) => setSelectedCourse(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                <option value="">Select Course</option>
                {courses.map(course => (
                  <option key={course.id} value={course.id}>
                    {course.name} ({course.course_code})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Assignment
              </label>
              <select
                value={selectedAssignment}
                onChange={(e) => setSelectedAssignment(e.target.value)}
                disabled={loadingAssignments || !selectedCourse}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50"
              >
                <option value="">
                  {loadingAssignments ? 'Loading...' : 'Select Assignment'}
                </option>
                {assignments.map(assignment => (
                  <option key={assignment.id} value={assignment.id}>
                    {assignment.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Peer Review Deadline
              </label>
              <input
                type="datetime-local"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Penalty per Review
              </label>
              <input
                type="number"
                min="1"
                max="50"
                value={penaltyPerReview}
                onChange={(e) => setPenaltyPerReview(parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
          </div>

          <div className="mt-4">
            <button
              onClick={fetchPeerReviewData}
              disabled={loading || !selectedCourse || !selectedAssignment || !deadline}
              className="bg-purple-500 text-white px-6 py-2 rounded-md hover:bg-purple-600 disabled:opacity-50 transition-colors flex items-center"
            >
              {loading ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Users className="h-4 w-4 mr-2" />
                  Analyze Peer Reviews
                </>
              )}
            </button>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="m-6 p-4 bg-red-100 border border-red-300 rounded-md text-red-700">
            {error}
          </div>
        )}

        {/* Results */}
        {peerReviewData && (
          <div className="p-6">
            {/* Summary Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="flex items-center">
                  <Users className="h-8 w-8 text-blue-600 mr-3" />
                  <div>
                    <p className="text-sm text-blue-600 font-medium">Total Reviews</p>
                    <p className="text-2xl font-bold text-blue-900">{peerReviewData.total_reviews}</p>
                  </div>
                </div>
              </div>

              <div className="bg-green-50 p-4 rounded-lg">
                <div className="flex items-center">
                  <CheckCircle className="h-8 w-8 text-green-600 mr-3" />
                  <div>
                    <p className="text-sm text-green-600 font-medium">On Time</p>
                    <p className="text-2xl font-bold text-green-900">
                      {peerReviewData.total_reviews - peerReviewData.late_or_missing_reviews}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-red-50 p-4 rounded-lg">
                <div className="flex items-center">
                  <AlertCircle className="h-8 w-8 text-red-600 mr-3" />
                  <div>
                    <p className="text-sm text-red-600 font-medium">Late/Missing</p>
                    <p className="text-2xl font-bold text-red-900">{peerReviewData.late_or_missing_reviews}</p>
                  </div>
                </div>
              </div>

              <div className="bg-yellow-50 p-4 rounded-lg">
                <div className="flex items-center">
                  <Calendar className="h-8 w-8 text-yellow-600 mr-3" />
                  <div>
                    <p className="text-sm text-yellow-600 font-medium">Total Penalties</p>
                    <p className="text-2xl font-bold text-yellow-900">
                      {peerReviewData.peer_review_summary.reduce((sum, summary) => sum + summary.total_penalty_points, 0)} pts
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Penalty Summary by Student */}
            {peerReviewData.peer_review_summary.length > 0 && (
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Students with Penalties</h3>
                <div className="bg-gray-50 rounded-lg overflow-hidden">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Student
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Total Penalty
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Canvas Comment
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {peerReviewData.peer_review_summary.map((summary, index) => (
                        <tr key={index} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm font-medium text-gray-900">
                              {summary.reviewer_name || `Student ID: ${summary.reviewer_id}`}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className="px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">
                              -{summary.total_penalty_points} points
                            </span>
                          </td>
                          <td className="px-6 py-4">
                            <div className="text-sm text-gray-900 whitespace-pre-line">
                              {summary.canvas_comment}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Detailed Review Status */}
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">All Peer Review Details</h3>
              <div className="bg-gray-50 rounded-lg overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-100">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Reviewer
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Assessed Student
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Comment Time
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Penalty
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {peerReviewData.peer_review_events.map((event, index) => (
                      <tr key={index} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">
                            {event.reviewer_name || `Student ID: ${event.reviewer_id}`}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {event.assessed_name || `Student ID: ${event.assessed_user_id}`}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(event.status)}`}>
                            {getStatusIcon(event.status)}
                            <span className="ml-1 capitalize">{event.status.replace('_', ' ')}</span>
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {formatDateTime(event.comment_time)}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {event.penalty_points > 0 ? (
                            <span className="px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">
                              -{event.penalty_points} points
                            </span>
                          ) : (
                            <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                              No penalty
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Empty state when no data */}
        {!peerReviewData && !loading && !error && (
          <div className="p-12 text-center">
            <Users className="h-16 w-16 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Peer Review Analysis</h3>
            <p className="text-gray-500 mb-6">
              Select a course, assignment, and deadline to analyze peer review completion and calculate penalties for late or missing reviews.
            </p>
            {assignments.length === 0 && selectedCourse && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mt-4">
                <div className="flex items-center">
                  <AlertCircle className="h-5 w-5 text-yellow-600 mr-2" />
                  <p className="text-sm text-yellow-800">
                    <strong>No peer review assignments found.</strong> The system looks for assignments with names containing: 
                    "proposal", "final project", "peer review", "project", "report", or "assignment".
                  </p>
                </div>
                <p className="text-sm text-yellow-700 mt-2">
                  Check the browser console (F12) for debugging information about loaded assignments.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default PeerReviewTracking;