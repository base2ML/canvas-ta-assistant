import React, { useState, useCallback, useEffect } from 'react';
import { RefreshCw, Calendar, User, Clock, ArrowLeft, FileText, ChevronUp, ChevronDown, MessageCircle } from 'lucide-react';

const LateDaysTracking = ({ apiUrl, apiToken, backendUrl, courses, onBack, onTAGrading, onPeerReviews, onLoadCourses }) => {
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [courseInfo, setCourseInfo] = useState(null);
  const [loadTime, setLoadTime] = useState(null);
  const [lateDaysData, setLateDaysData] = useState([]);
  const [selectedTAGroup, setSelectedTAGroup] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: 'student_name', direction: 'asc' });
  const [lastUpdated, setLastUpdated] = useState(null);

  // Cache configuration
  const CACHE_DURATION = 2 * 60 * 60 * 1000; // 2 hours in milliseconds

  // Use the first available course (since this tool is for single course use)
  const currentCourse = courses && courses.length > 0 ? courses[0] : null;

  // Generate cache key based on course and API credentials
  const generateCacheKey = useCallback((courseId) => {
    return `late_days_${courseId}_${apiUrl}_${apiToken.substring(0, 8)}`;
  }, [apiUrl, apiToken]);

  // Load data from cache
  const loadFromCache = useCallback((courseId) => {
    try {
      const key = generateCacheKey(courseId);
      const cached = localStorage.getItem(key);
      const timestampKey = `${key}_timestamp`;
      const timestamp = localStorage.getItem(timestampKey);
      
      if (cached && timestamp) {
        const age = Date.now() - parseInt(timestamp);
        if (age < CACHE_DURATION) {
          const data = JSON.parse(cached);
          setLateDaysData(data.lateDaysData || []);
          setAssignments(data.assignments || []);
          setCourseInfo(data.courseInfo);
          setLastUpdated(new Date(parseInt(timestamp)));
          return true;
        }
      }
    } catch (err) {
    }
    return false;
  }, [generateCacheKey, CACHE_DURATION]);

  // Save data to cache
  const saveToCache = useCallback((courseId, data) => {
    try {
      const key = generateCacheKey(courseId);
      const timestamp = Date.now();
      localStorage.setItem(key, JSON.stringify(data));
      localStorage.setItem(`${key}_timestamp`, timestamp.toString());
      setLastUpdated(new Date(timestamp));
    } catch (err) {
    }
  }, [generateCacheKey]);

  // Clear cache for current course
  const clearCache = useCallback(() => {
    if (currentCourse) {
      const key = generateCacheKey(currentCourse.id);
      localStorage.removeItem(key);
      localStorage.removeItem(`${key}_timestamp`);
      setLastUpdated(null);
    }
  }, [currentCourse, generateCacheKey]);

  const fetchLateDaysData = useCallback(async (courseId) => {
    try {
      // Use the new late-days endpoint that fetches all students' data
      const response = await fetch(`${backendUrl}/api/late-days`, {
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
        throw new Error(data.detail || 'Failed to fetch late days data');
      }

      return data;
    } catch (err) {
      throw new Error(`Error fetching late days data: ${err.message}`);
    }
  }, [backendUrl, apiUrl, apiToken]);

  const loadCourseData = useCallback(async (forceRefresh = false) => {
    if (!currentCourse) return;
    
    const courseId = currentCourse.id;
    setCacheKey(generateCacheKey(courseId));
    
    // Try to load from cache first (unless force refresh)
    if (!forceRefresh && loadFromCache(courseId)) {
      setLoading(false);
      return;
    }
    
    const startTime = Date.now();
    setLoading(true);
    setError('');
    setLoadTime(null);
    setLateDaysData([]);
    
    try {
      const data = await fetchLateDaysData(currentCourse.id);
      setLateDaysData(data.students || []);
      setAssignments(data.assignments || []);
      setCourseInfo(data.course_info);
      
      // Save to cache
      const cacheData = {
        lateDaysData: data.students || [],
        assignments: data.assignments || [],
        courseInfo: data.course_info
      };
      saveToCache(courseId, cacheData);
      
      const endTime = Date.now();
      const duration = (endTime - startTime) / 1000;
      setLoadTime(duration);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [currentCourse, fetchLateDaysData, generateCacheKey, loadFromCache, saveToCache]);

  // Load data automatically when component mounts and currentCourse is available
  useEffect(() => {
    if (currentCourse) {
      loadCourseData();
    } else if ((!courses || courses.length === 0) && onLoadCourses) {
      // If no courses are available, try to load them from the parent
      setLoading(true);
      onLoadCourses();
    }
  }, [currentCourse, loadCourseData, courses, onLoadCourses]);

  const handleTAGroupChange = (taGroup) => {
    setSelectedTAGroup(taGroup);
  };

  // Filter students by TA group if a filter is selected
  const filteredLateDaysData = selectedTAGroup
    ? lateDaysData.filter(student => student.ta_group_name === selectedTAGroup)
    : lateDaysData;

  // Get unique TA groups for the filter dropdown
  const availableTAGroups = [...new Set(lateDaysData
    .map(student => student.ta_group_name)
    .filter(group => group) // Remove null/undefined values
  )].sort();

  // Sorting function with three states: asc -> desc -> default (student name asc)
  const handleSort = (key) => {
    let newConfig;
    
    if (sortConfig.key === key) {
      if (sortConfig.direction === 'asc') {
        // First click was asc, now go to desc
        newConfig = { key, direction: 'desc' };
      } else if (sortConfig.direction === 'desc') {
        // Second click was desc, now go to default (student name asc)
        newConfig = { key: 'student_name', direction: 'asc' };
      } else {
        // Should not happen, but fallback to asc
        newConfig = { key, direction: 'asc' };
      }
    } else {
      // Clicking a different column, start with asc
      newConfig = { key, direction: 'asc' };
    }
    
    setSortConfig(newConfig);
  };

  // Sort the filtered data
  const sortedData = React.useMemo(() => {
    if (!sortConfig.key) return filteredLateDaysData;

    return [...filteredLateDaysData].sort((a, b) => {
      let aValue, bValue;

      if (sortConfig.key === 'student_name') {
        aValue = a.student_name || '';
        bValue = b.student_name || '';
      } else if (sortConfig.key === 'ta_group_name') {
        aValue = a.ta_group_name || '';
        bValue = b.ta_group_name || '';
      } else if (sortConfig.key === 'total_late_days') {
        aValue = a.total_late_days || 0;
        bValue = b.total_late_days || 0;
      } else if (sortConfig.key.startsWith('assignment_')) {
        const assignmentId = parseInt(sortConfig.key.replace('assignment_', ''));
        aValue = a.assignments[assignmentId] || 0;
        bValue = b.assignments[assignmentId] || 0;
      } else {
        return 0;
      }

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        aValue = aValue.toLowerCase();
        bValue = bValue.toLowerCase();
      }

      if (aValue < bValue) {
        return sortConfig.direction === 'asc' ? -1 : 1;
      }
      if (aValue > bValue) {
        return sortConfig.direction === 'asc' ? 1 : -1;
      }
      return 0;
    });
  }, [filteredLateDaysData, sortConfig]);

  // Sort indicator component
  const SortIndicator = ({ column }) => {
    if (sortConfig.key !== column) {
      // If we're on default sort and this is the student_name column, show it as active
      if (sortConfig.key === 'student_name' && column === 'student_name') {
        return sortConfig.direction === 'asc' 
          ? <ChevronUp className="h-4 w-4 text-blue-600" />
          : <ChevronDown className="h-4 w-4 text-blue-600" />;
      }
      return <ChevronUp className="h-4 w-4 text-gray-300" />;
    }
    return sortConfig.direction === 'asc' 
      ? <ChevronUp className="h-4 w-4 text-blue-600" />
      : <ChevronDown className="h-4 w-4 text-blue-600" />;
  };

  // Helper functions for displaying late days data

  // Helper function to get color coding for late days
  const getLateDaysColor = (days) => {
    if (days === 0) return 'text-green-700 bg-green-50 border-green-200';
    if (days === 1) return 'text-yellow-700 bg-yellow-50 border-yellow-200';
    if (days === 2) return 'text-orange-700 bg-orange-50 border-orange-200';
    return 'text-red-700 bg-red-50 border-red-200';
  };

  const getTotalLateDaysColor = (total) => {
    if (total === 0) return 'text-green-700 bg-green-50 border-green-200';
    if (total <= 3) return 'text-yellow-700 bg-yellow-50 border-yellow-200';
    if (total <= 6) return 'text-orange-700 bg-orange-50 border-orange-200';
    return 'text-red-700 bg-red-50 border-red-200';
  };

  return (
    <div className="max-w-full mx-auto p-6">
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
                  <ArrowLeft className="h-4 w-4 mr-1" />
                  Back to Assignment View
                </button>
                {onTAGrading && (
                  <button
                    onClick={onTAGrading}
                    className="text-purple-500 hover:text-purple-600 flex items-center"
                  >
                    <User className="h-4 w-4 mr-1" />
                    TA Grading
                  </button>
                )}
                {onPeerReviews && (
                  <button
                    onClick={onPeerReviews}
                    className="text-green-500 hover:text-green-600 flex items-center"
                  >
                    <MessageCircle className="h-4 w-4 mr-1" />
                    Peer Reviews
                  </button>
                )}
              </div>
              <h1 className="text-2xl font-bold text-gray-900 mt-2">Late Days Tracking</h1>
              <p className="text-gray-600 mt-1">Monitor student late day usage across assignments</p>
              {courseInfo && (
                <div className="flex items-center mt-2 text-sm text-gray-500">
                  <FileText className="h-4 w-4 mr-1" />
                  {courseInfo ? `${courseInfo.name} (${courseInfo.course_code})` : currentCourse ? `${currentCourse.name}` : 'No Course Selected'}
                </div>
              )}
              {loadTime && (
                <div className="flex items-center mt-1 text-xs text-green-600">
                  ⚡ Loaded in {loadTime.toFixed(1)}s
                </div>
              )}
              {lastUpdated && (
                <div className="flex items-center mt-1 text-xs text-gray-500">
                  🕒 Cached: {lastUpdated.toLocaleTimeString()}
                </div>
              )}
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => currentCourse && loadCourseData(false)}
                disabled={loading || !currentCourse}
                className="flex items-center px-3 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 disabled:opacity-50 transition-colors"
                title="Load from cache if available"
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                {lastUpdated ? 'Cache' : 'Load'}
              </button>
              <button
                onClick={() => {
                  if (currentCourse) {
                    clearCache();
                    loadCourseData(true);
                  }
                }}
                disabled={loading || !currentCourse}
                className="flex items-center px-3 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 transition-colors"
                title="Force refresh from Canvas API"
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          </div>
        </div>

        {/* TA Group Filter */}
        {currentCourse && availableTAGroups.length > 0 && (
          <div className="p-6 border-b border-gray-200">
            <div className="max-w-md">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Filter by TA Group
              </label>
              <select
                value={selectedTAGroup}
                onChange={(e) => handleTAGroupChange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All TA Groups ({lateDaysData.length} students)</option>
                {availableTAGroups.map(group => {
                  const studentCount = lateDaysData.filter(s => s.ta_group_name === group).length;
                  return (
                    <option key={group} value={group}>
                      {group} ({studentCount} students)
                    </option>
                  );
                })}
              </select>
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
            <p className="text-gray-600">Loading late days data...</p>
          </div>
        )}

        {/* Late Days Table */}
        {!loading && currentCourse && sortedData.length > 0 && (
          <div className="p-6">
            <div className="mb-4">
              <h3 className="text-lg font-medium text-gray-900 mb-2">Student Late Days Summary</h3>
              <p className="text-sm text-gray-600">
                Showing real late days data from Canvas submissions{selectedTAGroup ? ` for ${selectedTAGroup}` : ''}. Late days calculated from actual submission dates vs due dates.
                <span className="ml-2">
                  <span className="inline-block w-3 h-3 bg-green-50 border border-green-200 rounded mr-1"></span>0 days
                  <span className="inline-block w-3 h-3 bg-yellow-50 border border-yellow-200 rounded mr-1 ml-3"></span>1 day
                  <span className="inline-block w-3 h-3 bg-orange-50 border border-orange-200 rounded mr-1 ml-3"></span>2 days
                  <span className="inline-block w-3 h-3 bg-red-50 border border-red-200 rounded mr-1 ml-3"></span>3+ days
                </span>
              </p>
            </div>

            {/* Summary Statistics */}
            <div className="mb-6 grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                <div className="text-2xl font-bold text-blue-600">
                  {sortedData.length}
                </div>
                <div className="text-sm text-blue-800">{selectedTAGroup ? 'Filtered' : 'Total'} Students</div>
              </div>
              <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                <div className="text-2xl font-bold text-green-600">
                  {sortedData.filter(s => s.total_late_days === 0).length}
                </div>
                <div className="text-sm text-green-800">No Late Days Used</div>
              </div>
              <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
                <div className="text-2xl font-bold text-yellow-600">
                  {sortedData.filter(s => s.total_late_days > 0 && s.total_late_days <= 3).length}
                </div>
                <div className="text-sm text-yellow-800">1-3 Late Days</div>
              </div>
              <div className="bg-red-50 p-4 rounded-lg border border-red-200">
                <div className="text-2xl font-bold text-red-600">
                  {sortedData.filter(s => s.total_late_days > 3).length}
                </div>
                <div className="text-sm text-red-800">4+ Late Days</div>
              </div>
            </div>

            {/* Additional Metrics */}
            <div className="mb-6 p-4 bg-gray-50 rounded-lg">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Course Statistics</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Avg Late Days:</span>
                  <span className="ml-2 font-semibold">
                    {sortedData.length > 0 
                      ? (sortedData.reduce((sum, s) => sum + s.total_late_days, 0) / sortedData.length).toFixed(1)
                      : '0'
                    }
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Max Late Days:</span>
                  <span className="ml-2 font-semibold">
                    {Math.max(...sortedData.map(s => s.total_late_days), 0)}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Assignments:</span>
                  <span className="ml-2 font-semibold">{assignments.length}</span>
                </div>
                <div>
                  <span className="text-gray-500">On-Time Rate:</span>
                  <span className="ml-2 font-semibold">
                    {sortedData.length > 0 
                      ? Math.round((sortedData.filter(s => s.total_late_days === 0).length / sortedData.length) * 100)
                      : 0
                    }%
                  </span>
                </div>
              </div>
            </div>

            <div className="overflow-x-auto border border-gray-200 rounded-lg">
              <table className="min-w-full bg-white">
                <thead className="bg-gray-50">
                  <tr>
                    <th 
                      onClick={() => handleSort('student_name')}
                      className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider sticky left-0 bg-gray-50 border-r border-gray-200 min-w-[200px] cursor-pointer hover:bg-gray-100 select-none"
                    >
                      <div className="flex items-center justify-between">
                        <span>Student Name</span>
                        <SortIndicator column="student_name" />
                      </div>
                    </th>
                    {assignments.map(assignment => (
                      <th 
                        key={assignment.id}
                        onClick={() => handleSort(`assignment_${assignment.id}`)}
                        className="px-4 py-4 text-center text-xs font-medium text-gray-500 uppercase tracking-wider min-w-[120px] max-w-[120px] cursor-pointer hover:bg-gray-100 select-none"
                      >
                        <div className="flex flex-col items-center space-y-1">
                          <div className="flex items-center justify-center space-x-1">
                            <div className="text-xs font-semibold text-gray-700 leading-tight text-center max-w-full">
                              {assignment.name && assignment.name.length > 16
                                ? assignment.name.substring(0, 16) + '...' 
                                : assignment.name}
                            </div>
                            <SortIndicator column={`assignment_${assignment.id}`} />
                          </div>
                          {assignment.due_at && (
                            <div className="text-xs text-gray-500">
                              Due: {new Date(assignment.due_at).toLocaleDateString('en-US', { 
                                month: 'short', 
                                day: 'numeric' 
                              })}
                            </div>
                          )}
                        </div>
                      </th>
                    ))}
                    <th 
                      onClick={() => handleSort('total_late_days')}
                      className="px-6 py-4 text-center text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-100 border-l-2 border-gray-300 min-w-[120px] cursor-pointer hover:bg-gray-200 select-none"
                    >
                      <div className="flex items-center justify-center space-x-1">
                        <span>Total Late Days</span>
                        <SortIndicator column="total_late_days" />
                      </div>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {sortedData.map((student) => (
                    <tr key={student.student_id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm font-medium text-gray-900 sticky left-0 bg-white border-r border-gray-200">
                        <div className="flex items-center">
                          <User className="h-4 w-4 text-gray-400 mr-2 flex-shrink-0" />
                          <div className="min-w-0">
                            <div className="font-medium text-gray-900 truncate">{student.student_name}</div>
                            <div className="text-xs text-gray-500 truncate">{student.student_email || ''}</div>
                            {student.ta_group_name && (
                              <div className="text-xs text-blue-600 truncate">TA: {student.ta_group_name}</div>
                            )}
                          </div>
                        </div>
                      </td>
                      {assignments.map(assignment => {
                        const lateDays = student.assignments[assignment.id] || 0;
                        return (
                          <td key={assignment.id} className="px-4 py-4 text-center">
                            <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-xs font-bold border ${getLateDaysColor(lateDays)}`}>
                              {lateDays === 0 ? '—' : lateDays}
                            </span>
                          </td>
                        );
                      })}
                      <td className="px-6 py-4 text-center bg-gray-50 border-l-2 border-gray-300">
                        <span className={`inline-flex items-center justify-center px-4 py-2 rounded-full font-bold text-sm border ${getTotalLateDaysColor(student.total_late_days)}`}>
                          {student.total_late_days}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!loading && currentCourse && sortedData.length === 0 && lateDaysData.length === 0 && (
          <div className="p-12 text-center text-gray-500">
            <Calendar className="h-12 w-12 mx-auto mb-4" />
            <p>No assignment data available for this course</p>
            <p className="text-sm mt-2">Make sure assignments have due dates set in Canvas</p>
          </div>
        )}

        {/* No Course Available */}
        {!loading && !currentCourse && (
          <div className="p-12 text-center text-gray-500">
            <Calendar className="h-12 w-12 mx-auto mb-4" />
            <p>No course available</p>
            <p className="text-sm mt-2">Please configure a course in the main dashboard first</p>
            {onLoadCourses && (
              <button
                onClick={() => {
                  setLoading(true);
                  onLoadCourses();
                }}
                className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors"
              >
                Load Course Data
              </button>
            )}
          </div>
        )}

        {/* No Students in Filter */}
        {!loading && currentCourse && sortedData.length === 0 && lateDaysData.length > 0 && (
          <div className="p-12 text-center text-gray-500">
            <User className="h-12 w-12 mx-auto mb-4" />
            <p>No students found for TA group "{selectedTAGroup}"</p>
            <p className="text-sm mt-2">Try selecting a different TA group or clear the filter</p>
            <button
              onClick={() => setSelectedTAGroup('')}
              className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors"
            >
              Clear Filter
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default LateDaysTracking;