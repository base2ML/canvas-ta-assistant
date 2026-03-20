import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { RefreshCw, Calendar, ChevronUp, ChevronDown, User, Filter, MessageSquare, Eye, AlertTriangle, X, Send } from 'lucide-react';
import { apiFetch } from './api.js';
import { useSSEPost } from './hooks/useSSEPost.js';
import { formatDate, formatDateOnly } from './utils/dates';

const LateDaysTracking = ({ courses, onLoadCourses, activeCourseId, refreshTrigger }) => {
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [courseInfo, setCourseInfo] = useState(null);
  const [lateDaysData, setLateDaysData] = useState([]);
  const [selectedTAGroup, setSelectedTAGroup] = useState('');
  const [penaltyFilterAssignmentId, setPenaltyFilterAssignmentId] = React.useState('');
  const [sortConfig, setSortConfig] = useState({ key: 'student_name', direction: 'asc' });
  const [selectedAssignments, setSelectedAssignments] = useState([]);
  const [showAssignmentFilter, setShowAssignmentFilter] = useState(false);

  // Posting panel state
  const [showPostingPanel, setShowPostingPanel] = useState(false);
  const [postAssignmentId, setPostAssignmentId] = useState('');
  const [selectedStudentIds, setSelectedStudentIds] = useState([]);
  const [overrideComment, setOverrideComment] = useState('');
  const [isDryRun, setIsDryRun] = useState(false);

  // Settings state (for SAFE-04 production warning)
  const [appSettings, setAppSettings] = useState(null);

  // Preview modal state
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState('');

  // Confirmation dialog state
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);

  // Posting history state
  const [postingHistory, setPostingHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Progress state
  const [posting, setPosting] = useState(false);
  const [postProgress, setPostProgress] = useState({ current: 0, total: 0, skipped: 0 });
  const [postResult, setPostResult] = useState(null);
  const [postError, setPostError] = useState('');

  // Use the configured active course, falling back to courses[0]
  const currentCourse = courses && courses.length > 0
    ? (activeCourseId ? (courses.find(c => String(c.id) === String(activeCourseId)) || courses[0]) : courses[0])
    : null;

  const fetchLateDaysData = useCallback(async (courseId) => {
    try {
      const data = await apiFetch(`/api/dashboard/late-days/${courseId}`);
      return data;
    } catch (err) {
      throw new Error(`Error fetching late days data: ${err.message}`);
    }
  }, []);

  const loadPostingHistory = useCallback(async () => {
    if (!currentCourse) return;
    setHistoryLoading(true);
    try {
      const params = new URLSearchParams({ course_id: String(currentCourse.id) });
      if (postAssignmentId) {
        params.append('assignment_id', String(postAssignmentId));
      }
      const data = await apiFetch(`/api/comments/history?${params.toString()}`);
      setPostingHistory(data.history || []);
    } catch (err) {
      console.error('Error loading posting history:', err);
    } finally {
      setHistoryLoading(false);
    }
  }, [currentCourse, postAssignmentId]);

  const loadCourseData = useCallback(async () => {
    if (!currentCourse) return;

    setLoading(true);
    setError('');
    setLateDaysData([]);

    try {
      const data = await fetchLateDaysData(currentCourse.id);
      setLateDaysData(data.students || []);
      const assignmentList = data.assignments || [];
      setAssignments(assignmentList);

      // Initialize selectedAssignments with all assignment IDs
      setSelectedAssignments(assignmentList.map(a => a.id));

      setCourseInfo(data.course_info);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [currentCourse, fetchLateDaysData]);

  // Hook initialization
  const { startPosting, cancel: cancelPosting } = useSSEPost();

  // Load data automatically when component mounts and currentCourse is available.
  // refreshTrigger is incremented by the global header on each successful sync, causing a reload.
  useEffect(() => {
    if (currentCourse) {
      loadCourseData();
    } else if ((!courses || courses.length === 0) && onLoadCourses) {
      // If no courses are available, try to load them from the parent
      onLoadCourses();
    }
  }, [currentCourse, loadCourseData, courses, onLoadCourses, refreshTrigger]);

  // Settings fetch (for SAFE-04 production warning)
  useEffect(() => {
    apiFetch('/api/settings')
      .then(data => setAppSettings({ test_mode: data.test_mode, sandbox_course_id: data.sandbox_course_id }))
      .catch(() => {}); // Silently fail — settings are best-effort for safety warning
  }, []);

  // Load posting history when posting panel is open and assignment or course changes
  useEffect(() => {
    if (showPostingPanel) {
      loadPostingHistory();
    }
  }, [showPostingPanel, loadPostingHistory]);

  // Cleanup: cancel any in-progress posting on unmount
  useEffect(() => {
    return () => cancelPosting();
  }, [cancelPosting]);

  // Auto-show the filtered assignment's column when penalty filter is selected
  useEffect(() => {
    if (penaltyFilterAssignmentId) {
      const id = Number(penaltyFilterAssignmentId);
      if (!selectedAssignments.includes(id)) {
        setSelectedAssignments(prev => [...prev, id]);
      }
    }
  }, [penaltyFilterAssignmentId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-select students with late days when assignment changes
  useEffect(() => {
    if (postAssignmentId) {
      setSelectedStudentIds(sortedData.filter(s => s.total_late_days > 0).map(s => parseInt(s.student_id, 10)));
    }
  }, [postAssignmentId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Preview handler
  const handlePreview = async () => {
    if (!postAssignmentId || selectedStudentIds.length === 0) return;
    setPreviewLoading(true);
    setPreviewError('');
    try {
      const data = await apiFetch(`/api/comments/preview/${postAssignmentId}`, {
        method: 'POST',
        body: JSON.stringify({
          course_id: String(currentCourse.id),
          template_type: 'penalty',
          user_ids: selectedStudentIds,
        }),
      });
      setPreviewData(data);
      setShowPreviewModal(true);
    } catch (err) {
      setPreviewError(err.message);
    } finally {
      setPreviewLoading(false);
    }
  };

  // Post handler
  const handlePost = async () => {
    setShowConfirmDialog(false);
    setShowPreviewModal(false);
    setPosting(true);
    setPostResult(null);
    setPostError('');
    setPostProgress({ current: 0, total: 0, skipped: 0 });
    try {
      await startPosting(postAssignmentId, {
        course_id: String(currentCourse.id),
        template_type: 'penalty',
        user_ids: selectedStudentIds,
        override_comment: overrideComment || null,
        dry_run: isDryRun,
      }, {
        onStarted: ({ total }) => setPostProgress(prev => ({ ...prev, total })),
        onProgress: ({ current, total }) => setPostProgress(prev => ({ ...prev, current, total })),
        onPosted: () => {},
        onSkipped: () => setPostProgress(prev => ({ ...prev, skipped: prev.skipped + 1 })),
        onError: () => {},
        onDry_run: () => setPostProgress(prev => ({ ...prev, current: prev.current + 1 })),
        onComplete: (data) => { setPostResult(data); loadPostingHistory(); },
      });
    } catch (err) {
      if (err.name !== 'AbortError') {
        setPostError(err.message);
      }
    } finally {
      setPosting(false);
    }
  };

  // Student toggle handler for posting panel
  const handlePostStudentToggle = (studentId) => {
    const id = parseInt(studentId, 10);
    setSelectedStudentIds(prev =>
      prev.includes(id) ? prev.filter(sid => sid !== id) : [...prev, id]
    );
  };

  // Compute isProductionCourse for SAFE-04 warning
  const isProductionCourse = appSettings && currentCourse &&
    String(currentCourse.id) !== String(appSettings.sandbox_course_id);

  const handleTAGroupChange = (taGroup) => {
    setSelectedTAGroup(taGroup);
  };

  // Handle assignment selection
  const handleAssignmentToggle = (assignmentId) => {
    setSelectedAssignments(prev => {
      if (prev.includes(assignmentId)) {
        return prev.filter(id => id !== assignmentId);
      } else {
        return [...prev, assignmentId];
      }
    });
  };

  const handleSelectAllAssignments = () => {
    setSelectedAssignments(assignments.map(a => a.id));
  };

  const handleDeselectAllAssignments = () => {
    setSelectedAssignments([]);
  };

  // Sort assignments by due date (earliest to latest)
  // Assignments without due dates appear at the end
  const sortedAssignments = React.useMemo(() => {
    return [...assignments].sort((a, b) => {
      // Handle null/undefined due dates - put them at the end
      if (!a.due_at && !b.due_at) return 0;
      if (!a.due_at) return 1;
      if (!b.due_at) return -1;

      // Sort by due date
      return new Date(a.due_at) - new Date(b.due_at);
    });
  }, [assignments]);

  // Filter assignments based on selection
  const displayedAssignments = sortedAssignments.filter(
    assignment => selectedAssignments.includes(assignment.id)
  );

  // Filter students by TA group if a filter is selected
  const taFilteredData = selectedTAGroup
    ? lateDaysData.filter(student => student.ta_group_name === selectedTAGroup)
    : lateDaysData;

  // Step 2: Penalty days filter — show only students with penalty_days > 0 on the chosen assignment
  const filteredLateDaysData = penaltyFilterAssignmentId
    ? taFilteredData.filter(student => {
        const entry = student.assignments?.[penaltyFilterAssignmentId];
        return entry && entry.penalty_days > 0;
      })
    : taFilteredData;

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
        const aEntry = a.assignments[assignmentId];
        const bEntry = b.assignments[assignmentId];
        aValue = aEntry ? (aEntry.days_late || 0) : 0;
        bValue = bEntry ? (bEntry.days_late || 0) : 0;
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

  // Build set of user IDs that already have posted comments for the selected assignment
  const postedUserIds = useMemo(() => {
    if (!postAssignmentId || !postingHistory.length) return new Set();
    return new Set(
      postingHistory
        .filter(h => String(h.assignment_id) === String(postAssignmentId) && h.status === 'posted')
        .map(h => h.user_id)
    );
  }, [postingHistory, postAssignmentId]);

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

  const getTotalLateDaysColor = (total) => {
    if (total === 0) return 'text-green-700 bg-green-50 border-green-200';
    if (total <= 3) return 'text-yellow-700 bg-yellow-50 border-yellow-200';
    if (total <= 6) return 'text-orange-700 bg-orange-50 border-orange-200';
    return 'text-red-700 bg-red-50 border-red-200';
  };

  return (
    <>
    <div className="max-w-full mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg">
        {/* Header */}
        <div className="border-b border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Late Days Tracking</h1>
              <p className="text-gray-600 mt-1">Monitor student late day usage across assignments</p>
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => setShowPostingPanel(!showPostingPanel)}
                className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 flex items-center gap-2 text-sm"
              >
                <MessageSquare className="w-4 h-4" />
                Post Comments
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

        {/* Penalty Days Filter */}
        {currentCourse && assignments.length > 0 && (
          <div className="p-6 border-b border-gray-200">
            <div className="max-w-md">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Show students with penalty days on
              </label>
              <select
                value={penaltyFilterAssignmentId}
                onChange={(e) => setPenaltyFilterAssignmentId(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All students</option>
                {sortedAssignments.map(assignment => {
                  const count = (selectedTAGroup
                    ? lateDaysData.filter(s => s.ta_group_name === selectedTAGroup)
                    : lateDaysData
                  ).filter(s => {
                    const entry = s.assignments?.[String(assignment.id)];
                    return entry && entry.penalty_days > 0;
                  }).length;
                  return (
                    <option key={assignment.id} value={String(assignment.id)}>
                      {assignment.name} ({count} student{count !== 1 ? 's' : ''})
                    </option>
                  );
                })}
              </select>
              {penaltyFilterAssignmentId && (
                <button
                  onClick={() => setPenaltyFilterAssignmentId("")}
                  className="mt-2 text-sm text-blue-600 hover:text-blue-800 font-medium"
                >
                  Clear filter
                </button>
              )}
            </div>
          </div>
        )}

        {/* Assignment Filter */}
        {currentCourse && assignments.length > 0 && (
          <div className="p-6 border-b border-gray-200">
            <button
              onClick={() => setShowAssignmentFilter(!showAssignmentFilter)}
              className="flex items-center space-x-2 text-sm font-medium text-gray-700 hover:text-blue-600 transition-colors"
            >
              <Filter className="h-4 w-4" />
              <span>
                Select Assignments ({selectedAssignments.length} of {assignments.length} shown)
              </span>
              <ChevronDown className={`h-4 w-4 transition-transform ${showAssignmentFilter ? 'rotate-180' : ''}`} />
            </button>

            {showAssignmentFilter && (
              <div className="mt-4">
                <div className="flex items-center space-x-3 mb-4">
                  <button
                    onClick={handleSelectAllAssignments}
                    className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                  >
                    Select All
                  </button>
                  <span className="text-gray-300">|</span>
                  <button
                    onClick={handleDeselectAllAssignments}
                    className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                  >
                    Deselect All
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-h-96 overflow-y-auto">
                  {sortedAssignments.map(assignment => (
                    <label
                      key={assignment.id}
                      className="flex items-start space-x-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedAssignments.includes(assignment.id)}
                        onChange={() => handleAssignmentToggle(assignment.id)}
                        className="mt-1 h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gray-900 truncate">
                          {assignment.name}
                        </div>
                        {assignment.due_at && (
                          <div className="text-xs text-gray-500 mt-1">
                            Due: {formatDateOnly(assignment.due_at)}
                          </div>
                        )}
                        {!assignment.due_at && (
                          <div className="text-xs text-gray-400 mt-1">
                            No due date
                          </div>
                        )}
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Posting Panel */}
        {showPostingPanel && currentCourse && (
          <div className="p-6 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Post Late Day Comments</h3>

            {/* Production warning (SAFE-04) */}
            {isProductionCourse && (
              <div className="bg-yellow-50 border border-yellow-300 rounded p-3 mb-4 text-yellow-800 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 flex-shrink-0" />
                <span>Warning: You are posting to a live production course. Comments will appear on real student submissions.</span>
              </div>
            )}

            {/* Test mode info */}
            {appSettings?.test_mode && (
              <div className="bg-blue-50 border border-blue-200 rounded p-3 mb-4 text-blue-800 flex items-center gap-2">
                <span className="font-medium">Test mode is active.</span> Comments will be validated but not posted to Canvas.
              </div>
            )}

            {/* Assignment dropdown */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Assignment</label>
              <select
                value={postAssignmentId}
                onChange={(e) => setPostAssignmentId(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Select an assignment...</option>
                {sortedAssignments.map(a => (
                  <option key={a.id} value={String(a.id)}>
                    {a.name}{a.due_at ? ` (Due: ${formatDateOnly(a.due_at)})` : ''}
                  </option>
                ))}
              </select>
            </div>

            {/* Student selection summary */}
            <div className="mb-2 flex items-center gap-3 text-sm text-gray-600">
              <span>{selectedStudentIds.length} of {sortedData.length} students selected (those with late days)</span>
              <button
                onClick={() => setSelectedStudentIds(sortedData.map(s => parseInt(s.student_id, 10)))}
                className="text-blue-600 hover:text-blue-800 font-medium"
              >
                Select All
              </button>
              <span className="text-gray-300">|</span>
              <button
                onClick={() => setSelectedStudentIds([])}
                className="text-blue-600 hover:text-blue-800 font-medium"
              >
                Deselect All
              </button>
            </div>

            {/* Student list */}
            <div className="mb-4 max-h-48 overflow-y-auto border border-gray-200 rounded-md p-2">
              {sortedData.map(student => (
                <label key={student.student_id} className="flex items-center gap-2 p-1 hover:bg-gray-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedStudentIds.includes(parseInt(student.student_id, 10))}
                    onChange={() => handlePostStudentToggle(student.student_id)}
                    className="h-4 w-4 text-indigo-600 rounded focus:ring-indigo-500"
                  />
                  <span className="text-sm text-gray-800">{student.student_name}</span>
                  <span className="text-xs text-gray-500">({student.total_late_days} late days)</span>
                  {postedUserIds.has(parseInt(student.student_id, 10)) && (
                    <span className="ml-2 text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                      Already posted
                    </span>
                  )}
                </label>
              ))}
            </div>

            {/* Override comment textarea (POST-08) */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Override Comment (optional)</label>
              <p className="text-xs text-gray-500 mb-1">If provided, this replaces the template for all selected students.</p>
              <textarea
                rows={4}
                value={overrideComment}
                onChange={(e) => setOverrideComment(e.target.value)}
                placeholder="Leave blank to use the default template..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono text-sm"
              />
            </div>

            {/* Dry run checkbox */}
            <div className="mb-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isDryRun}
                  onChange={(e) => setIsDryRun(e.target.checked)}
                  className="h-4 w-4 text-indigo-600 rounded focus:ring-indigo-500"
                />
                <span className="text-sm text-gray-700">Dry run (preview only, no Canvas API calls)</span>
              </label>
            </div>

            {/* Preview button */}
            <button
              onClick={handlePreview}
              disabled={!postAssignmentId || selectedStudentIds.length === 0 || previewLoading || posting}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
            >
              {previewLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />}
              Preview Comments
            </button>

            {/* Preview error */}
            {previewError && (
              <p className="mt-2 text-sm text-red-600">{previewError}</p>
            )}
          </div>
        )}

        {/* Posting History Table (POST-09) */}
        {showPostingPanel && postingHistory.length > 0 && (
          <div className="p-6 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Posting History</h3>
            {historyLoading && (
              <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Loading history...</span>
              </div>
            )}
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Student</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Comment</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Posted At</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {postingHistory.slice(0, 50).map((h, idx) => {
                    const studentName = lateDaysData.find(s => parseInt(s.student_id, 10) === h.user_id)?.student_name || `User ${h.user_id}`;
                    const commentPreview = h.comment_text && h.comment_text.length > 100
                      ? h.comment_text.substring(0, 100) + '...'
                      : h.comment_text || '';
                    const statusColors = {
                      posted: 'bg-green-100 text-green-800',
                      failed: 'bg-red-100 text-red-800',
                      skipped: 'bg-gray-100 text-gray-700',
                      dry_run: 'bg-blue-100 text-blue-800',
                    };
                    const statusColor = statusColors[h.status] || 'bg-gray-100 text-gray-700';
                    return (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap">{studentName}</td>
                        <td className="px-4 py-3">
                          <span className="font-mono text-xs text-gray-700">{commentPreview}</span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${statusColor}`}>
                            {h.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                          {h.posted_at ? formatDate(h.posted_at) : '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {postingHistory.length > 50 && (
              <p className="mt-2 text-xs text-gray-500">Showing most recent 50 entries.</p>
            )}
          </div>
        )}

        {/* Progress indicator (POST-07) */}
        {posting && (
          <div className="mx-6 my-4 flex items-center gap-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <RefreshCw className="w-4 h-4 animate-spin text-blue-600" />
            <span className="text-blue-800 font-medium">
              Posting {postProgress.current}/{postProgress.total} comments...
              {postProgress.skipped > 0 && ` (${postProgress.skipped} skipped)`}
            </span>
            <button onClick={cancelPosting} className="ml-auto text-sm text-red-600 hover:text-red-800">
              Cancel
            </button>
          </div>
        )}

        {/* Post result summary */}
        {postResult && !posting && (
          <div className="mx-6 my-4 p-4 bg-green-50 border border-green-200 rounded-lg">
            <p className="font-medium text-green-800">
              Posting complete: {postResult.successful} posted, {postResult.failed} failed, {postResult.skipped} skipped
              {postResult.dry_run && ' (DRY RUN)'}
            </p>
          </div>
        )}

        {/* Post error banner */}
        {postError && (
          <div className="mx-6 my-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="font-medium text-red-800">Error: {postError}</p>
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
                  <span className="ml-2 font-semibold">{displayedAssignments.length}</span>
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

            <div className="flex gap-4 text-xs text-gray-500 mb-2 items-center flex-wrap">
              <span className="flex items-center gap-1">
                <span className="inline-block w-4 h-4 rounded-full bg-green-100 border border-green-300"></span>
                Bank days (no penalty)
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block w-4 h-4 rounded-full bg-red-100 border border-red-300"></span>
                Penalty days
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-flex px-1 rounded bg-red-100 text-red-700 border border-red-300 font-bold">NA</span>
                Not Accepted (project deliverable)
              </span>
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
                    {displayedAssignments.map(assignment => (
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
                              Due: {formatDateOnly(assignment.due_at)}
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
                      {displayedAssignments.map(assignment => {
                        const entry = student.assignments[assignment.id];
                        const isOnTime = !entry || entry.days_late === 0;
                        const isNotAccepted = entry && entry.not_accepted;
                        const bankDays = entry ? (entry.days_late - entry.penalty_days) : 0;
                        const penaltyDays = entry ? entry.penalty_days : 0;
                        const daysLate = entry ? entry.days_late : 0;
                        return (
                          <td key={assignment.id} className="px-4 py-4 text-center">
                            {isOnTime ? (
                              <span className="inline-flex items-center justify-center w-8 h-8 rounded-full text-xs font-bold border border-gray-200 text-gray-400 bg-white">
                                —
                              </span>
                            ) : isNotAccepted ? (
                              <span
                                className="inline-flex items-center justify-center px-2 py-0.5 rounded text-xs font-bold bg-red-100 text-red-700 border border-red-300"
                                title={`Not Accepted — submitted ${daysLate} day${daysLate !== 1 ? 's' : ''} late (project deliverable)`}
                              >
                                NA
                              </span>
                            ) : penaltyDays > 0 && bankDays > 0 ? (
                              <span
                                className="inline-flex flex-col items-center justify-center w-8 rounded text-xs font-bold border border-red-300 overflow-hidden"
                                title={`${daysLate} days late: ${bankDays} bank, ${penaltyDays} penalty (${entry.penalty_percent}% deduction)`}
                              >
                                <span className="w-full text-center bg-green-100 text-green-700 py-0.5">{bankDays}</span>
                                <span className="w-full text-center bg-red-100 text-red-700 py-0.5">{penaltyDays}</span>
                              </span>
                            ) : penaltyDays > 0 ? (
                              <span
                                className="inline-flex items-center justify-center w-8 h-8 rounded-full text-xs font-bold border bg-red-100 text-red-700 border-red-300"
                                title={`${daysLate} days late: ${bankDays} bank, ${penaltyDays} penalty (${entry.penalty_percent}% deduction)`}
                              >
                                {daysLate}
                              </span>
                            ) : (
                              <span
                                className="inline-flex items-center justify-center w-8 h-8 rounded-full text-xs font-bold border bg-green-100 text-green-700 border-green-300"
                                title={`${bankDays} bank day${bankDays !== 1 ? 's' : ''} used (no penalty)`}
                              >
                                {bankDays}
                              </span>
                            )}
                          </td>
                        );
                      })}
                      <td className="px-6 py-4 text-center bg-gray-50 border-l-2 border-gray-300">
                        <div className="text-center">
                          <span className={`inline-flex items-center justify-center px-4 py-2 rounded-full font-bold text-sm border ${getTotalLateDaysColor(student.total_late_days)}`}>
                            {student.total_late_days}
                          </span>
                          {student.bank_remaining !== undefined && (
                            <div className="text-xs text-gray-500 mt-1">
                              {student.bank_remaining}/{student.total_bank} bank left
                            </div>
                          )}
                        </div>
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
            <p>No students match the current filters</p>
            <p className="text-sm mt-2">Try adjusting or clearing the TA group or penalty days filter</p>
            <button
              onClick={() => { setSelectedTAGroup(''); setPenaltyFilterAssignmentId(''); }}
              className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors"
            >
              Clear Filter
            </button>
          </div>
        )}
      </div>
    </div>

    {/* Preview Modal (POST-03) */}
    {showPreviewModal && previewData && (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[80vh] flex flex-col">
          {/* Modal header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">
              Preview Comments for {previewData.assignment_name}
            </h3>
            <button onClick={() => setShowPreviewModal(false)} className="text-gray-400 hover:text-gray-600">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Modal body */}
          <div className="flex-1 overflow-y-auto p-4">
            {/* Production warning in modal */}
            {isProductionCourse && (
              <div className="bg-yellow-50 border border-yellow-300 rounded p-3 mb-4 text-yellow-800 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 flex-shrink-0" />
                <span>Warning: You are posting to a live production course. Comments will appear on real student submissions.</span>
              </div>
            )}

            {/* Preview table */}
            <table className="min-w-full border border-gray-200 rounded-lg overflow-hidden">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Student</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Comment</th>
                  <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {(previewData.previews || []).map((item, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{item.user_name}</td>
                    <td className="px-4 py-3 text-sm text-gray-700">
                      <pre className="whitespace-pre-wrap font-mono text-xs bg-gray-50 p-2 rounded">{item.comment_text}</pre>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {item.already_posted && (
                        <span className="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded-full">Already posted</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Modal footer */}
          <div className="p-4 border-t border-gray-200">
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Override Comment (optional)</label>
              <textarea
                rows={3}
                value={overrideComment}
                onChange={(e) => setOverrideComment(e.target.value)}
                placeholder="Leave blank to use the default template..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono text-sm"
              />
            </div>
            <div className="mb-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isDryRun}
                  onChange={(e) => setIsDryRun(e.target.checked)}
                  className="h-4 w-4 text-indigo-600 rounded"
                />
                <span className="text-sm text-gray-700">Dry run (preview only, no Canvas API calls)</span>
              </label>
            </div>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowPreviewModal(false)}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => setShowConfirmDialog(true)}
                className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 flex items-center gap-2"
              >
                <Send className="w-4 h-4" />
                Post Comments
              </button>
            </div>
          </div>
        </div>
      </div>
    )}

    {/* Confirmation Dialog (POST-04) */}
    {showConfirmDialog && (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]">
        <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Confirm Posting</h3>

          <div className="space-y-2 mb-4 text-sm text-gray-700">
            <div><span className="font-medium">Course:</span> {courseInfo?.name || currentCourse?.name}</div>
            <div><span className="font-medium">Assignment:</span> {assignments.find(a => String(a.id) === String(postAssignmentId))?.name}</div>
            <div>
              <span className="font-medium">Students:</span> {selectedStudentIds.length - (previewData?.already_posted_count || 0)} new posts
            </div>
            <div>
              <span className="font-medium">Mode:</span>{' '}
              {isDryRun
                ? <span className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded-full text-xs">Dry Run</span>
                : <span className="px-2 py-0.5 bg-red-100 text-red-800 rounded-full text-xs font-bold">LIVE</span>
              }
            </div>
          </div>

          {isProductionCourse && !isDryRun && (
            <div className="mb-4 p-3 bg-red-50 border border-red-300 rounded text-red-800 text-sm">
              This will post to a LIVE production course!
            </div>
          )}

          <div className="flex justify-end gap-3">
            <button
              onClick={() => setShowConfirmDialog(false)}
              className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={handlePost}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 flex items-center gap-2"
            >
              <Send className="w-4 h-4" />
              Confirm &amp; Post
            </button>
          </div>
        </div>
      </div>
    )}
    </>
  );
};

export default LateDaysTracking;
