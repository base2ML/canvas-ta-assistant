import React, { useState, useEffect } from 'react';
import { RefreshCw, Users, Calendar, MessageCircle, AlertCircle, CheckCircle } from 'lucide-react';

const SimpleDashboard = ({ backendUrl, getAuthHeaders }) => {
  const [courses, setCourses] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [taGradingData, setTAGradingData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadCourses();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadCourses = async () => {
    setLoading(true);
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${backendUrl}/api/canvas/courses`, { headers });

      if (!response.ok) {
        throw new Error(`Failed to load courses: ${response.statusText}`);
      }

      const data = await response.json();
      setCourses(data.courses || []);

      // Auto-select first course
      if (data.courses && data.courses.length > 0) {
        setSelectedCourse(data.courses[0]);
        await loadCourseData(data.courses[0].id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadCourseData = async (courseId) => {
    if (!courseId) return;

    setLoading(true);
    try {
      const headers = await getAuthHeaders();

      // Load assignments and TA grading data
      const [assignmentsRes, gradingRes] = await Promise.all([
        fetch(`${backendUrl}/api/canvas/assignments/${courseId}`, { headers }),
        fetch(`${backendUrl}/api/dashboard/ta-grading/${courseId}`, { headers })
      ]);

      if (assignmentsRes.ok) {
        const assignmentsData = await assignmentsRes.json();
        setAssignments(assignmentsData.assignments || []);
      }

      if (gradingRes.ok) {
        const gradingData = await gradingRes.json();
        setTAGradingData(gradingData);
      }
    } catch (err) {
      console.error('Error loading course data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCourseSelect = async (course) => {
    setSelectedCourse(course);
    setAssignments([]);
    setTAGradingData(null);
    await loadCourseData(course.id);
  };

  const refreshData = () => {
    if (selectedCourse) {
      loadCourseData(selectedCourse.id);
    } else {
      loadCourses();
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white shadow-sm rounded-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-3xl font-bold text-gray-900">Canvas TA Dashboard</h1>
            <button
              onClick={refreshData}
              disabled={loading}
              className="inline-flex items-center space-x-2 px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <div className="flex items-center">
                <AlertCircle className="h-4 w-4 text-red-600 mr-2" />
                <p className="text-sm text-red-600">{error}</p>
              </div>
            </div>
          )}

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
                <option value="">Select a course...</option>
                {courses.map((course) => (
                  <option key={course.id} value={course.id}>
                    {course.name} ({course.course_code})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Course Data */}
        {selectedCourse && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Assignments */}
            <div className="bg-white shadow-sm rounded-lg p-6">
              <div className="flex items-center space-x-2 mb-4">
                <Calendar className="h-5 w-5 text-blue-600" />
                <h2 className="text-xl font-semibold text-gray-900">
                  Assignments ({assignments.length})
                </h2>
              </div>

              <div className="space-y-3 max-h-96 overflow-y-auto">
                {assignments.map((assignment) => (
                  <div key={assignment.id} className="border border-gray-200 rounded-lg p-3">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-medium text-gray-900">{assignment.name}</h3>
                        <p className="text-sm text-gray-600 mt-1">
                          Due: {new Date(assignment.due_at).toLocaleDateString()}
                        </p>
                        <p className="text-sm text-gray-500">
                          Points: {assignment.points_possible}
                        </p>
                      </div>
                      <div className="flex items-center space-x-2">
                        {assignment.published ? (
                          <CheckCircle className="h-4 w-4 text-green-600" />
                        ) : (
                          <AlertCircle className="h-4 w-4 text-yellow-600" />
                        )}
                      </div>
                    </div>
                  </div>
                ))}

                {assignments.length === 0 && (
                  <p className="text-gray-500 text-center py-4">
                    No assignments found for this course.
                  </p>
                )}
              </div>
            </div>

            {/* TA Grading Summary */}
            <div className="bg-white shadow-sm rounded-lg p-6">
              <div className="flex items-center space-x-2 mb-4">
                <Users className="h-5 w-5 text-green-600" />
                <h2 className="text-xl font-semibold text-gray-900">TA Grading Status</h2>
              </div>

              {taGradingData ? (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                      <div className="text-2xl font-bold text-blue-600">
                        {taGradingData.total_ungraded || 0}
                      </div>
                      <div className="text-sm text-gray-600">Ungraded</div>
                    </div>
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                      <div className="text-2xl font-bold text-green-600">
                        {taGradingData.total_graded || 0}
                      </div>
                      <div className="text-sm text-gray-600">Graded</div>
                    </div>
                  </div>

                  {taGradingData.ta_workload && Object.keys(taGradingData.ta_workload).length > 0 && (
                    <div className="mt-4">
                      <h3 className="text-sm font-medium text-gray-700 mb-2">TA Workload</h3>
                      <div className="space-y-2">
                        {Object.entries(taGradingData.ta_workload).map(([taName, count]) => (
                          <div key={taName} className="flex justify-between items-center py-1">
                            <span className="text-sm text-gray-600">{taName}</span>
                            <span className="text-sm font-medium">{count} assignments</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-4">
                  Loading TA grading data...
                </p>
              )}
            </div>
          </div>
        )}

        {!selectedCourse && courses.length === 0 && !loading && (
          <div className="text-center py-12">
            <MessageCircle className="mx-auto h-12 w-12 text-gray-400" />
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

export default SimpleDashboard;