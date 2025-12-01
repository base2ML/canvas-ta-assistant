import React from 'react';
import { CheckCircle, Clock, XCircle, ChevronDown, ChevronRight, Calendar, AlertTriangle, Eye, AlertCircleIcon } from 'lucide-react';

const AssignmentStatusBreakdown = ({ assignmentStats, expandedAssignments, onToggleExpanded }) => {
  if (!assignmentStats || assignmentStats.length === 0) return null;

  const formatDate = (dateString) => {
    if (!dateString) return 'No due date';
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="bg-white shadow-sm rounded-lg p-6 mb-6">
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
                  onClick={() => onToggleExpanded(assignment.assignment_id)}
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
                            className={`h-2 rounded-full transition-all duration-300 ${isCompleted ? 'bg-green-500' : 'bg-yellow-500'
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

                        {/* Submission Status Cards */}
                        <div className="grid grid-cols-3 gap-2 mt-3">
                          {/* On Time Card */}
                          <div className="bg-green-50 border border-green-200 rounded-md p-2">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center space-x-1">
                                <CheckCircle className="h-3 w-3 text-green-600" />
                                <span className="text-xs font-medium text-green-900">On Time</span>
                              </div>
                              <span className="text-lg font-bold text-green-600">
                                {assignment.submitted_on_time || 0}
                              </span>
                            </div>
                          </div>

                          {/* Late Card */}
                          <div className="bg-yellow-50 border border-yellow-200 rounded-md p-2">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center space-x-1">
                                <Clock className="h-3 w-3 text-yellow-600" />
                                <span className="text-xs font-medium text-yellow-900">Late</span>
                              </div>
                              <span className="text-lg font-bold text-yellow-600">
                                {assignment.submitted_late || 0}
                              </span>
                            </div>
                          </div>

                          {/* Missing Card */}
                          <div className="bg-red-50 border border-red-200 rounded-md p-2">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center space-x-1">
                                <AlertCircleIcon className="h-3 w-3 text-red-600" />
                                <span className="text-xs font-medium text-red-900">Missing</span>
                              </div>
                              <span className="text-lg font-bold text-red-600">
                                {assignment.not_submitted || 0}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="text-xs text-gray-400 mt-2">
                          {hasBreakdown
                            ? `Click to view TA grading breakdown (${taBreakdown?.length || 0} TAs assigned)`
                            : `Click to view details (no TA assignments found in Canvas)`}
                        </div>
                      </div>
                    </div>

                    <div className="text-right ml-4">
                      <div
                        className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${isCompleted
                            ? 'bg-green-100 text-green-800'
                            : 'bg-yellow-100 text-yellow-800'
                          }`}
                      >
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
                    <h5 className="font-medium text-gray-900 mb-3">TA Workload Breakdown</h5>
                    {hasBreakdown ? (
                      <div className="overflow-x-auto">
                        <table className="min-w-full bg-white border border-gray-200 rounded-lg">
                          <thead className="bg-gray-50">
                            <tr>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                TA Name
                              </th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Students
                              </th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Graded
                              </th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Progress
                              </th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                On Time
                              </th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Late
                              </th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Missing
                              </th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-200">
                            {taBreakdown.map((taStats, index) => (
                              <tr key={index} className="hover:bg-gray-50">
                                <td className="px-4 py-3 text-sm font-medium text-gray-900">
                                  {taStats.ta_name}
                                </td>
                                <td className="px-4 py-3 text-sm text-gray-600">
                                  {taStats.total_assigned}
                                </td>
                                <td className="px-4 py-3 text-sm text-gray-600">
                                  {taStats.graded}/{taStats.total_assigned}
                                </td>
                                <td className="px-4 py-3 text-sm">
                                  <div className="flex items-center space-x-2">
                                    <div className="w-16 bg-gray-200 rounded-full h-2">
                                      <div
                                        className={`h-2 rounded-full ${taStats.percentage_complete === 100
                                            ? 'bg-green-500'
                                            : 'bg-yellow-500'
                                          }`}
                                        style={{ width: `${taStats.percentage_complete}%` }}
                                      ></div>
                                    </div>
                                    <span
                                      className={`text-xs font-medium ${taStats.percentage_complete === 100
                                          ? 'text-green-600'
                                          : 'text-yellow-600'
                                        }`}
                                    >
                                      {taStats.percentage_complete}%
                                    </span>
                                  </div>
                                </td>
                                <td className="px-4 py-3 text-sm text-green-600">
                                  {taStats.submitted_on_time}
                                </td>
                                <td className="px-4 py-3 text-sm text-yellow-600">
                                  {taStats.submitted_late}
                                </td>
                                <td className="px-4 py-3 text-sm text-red-600">
                                  {taStats.not_submitted}
                                </td>
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
  );
};

export default AssignmentStatusBreakdown;
