import React from 'react';
import { CheckCircle, Clock, XCircle } from 'lucide-react';

const AssignmentStatusBreakdown = ({ assignmentMetrics }) => {
  if (!assignmentMetrics || assignmentMetrics.length === 0) return null;

  const formatDate = (dateString) => {
    if (!dateString) return 'No due date';
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <div className="mt-6 bg-white rounded-lg border border-slate-200 p-4">
      <h3 className="text-lg font-semibold mb-4">Status by Assignment</h3>
      <div className="space-y-2">
        {assignmentMetrics.map(assignment => (
          <div key={assignment.assignment_id} className="border-b pb-2 last:border-b-0">
            <div className="flex justify-between items-center">
              <span className="font-medium">{assignment.assignment_name}</span>
              <span className="text-sm text-slate-500">
                Due: {formatDate(assignment.due_date)}
              </span>
            </div>
            <div className="flex gap-6 mt-2 text-sm">
              <span className="text-green-600 flex items-center gap-1">
                <CheckCircle className="w-4 h-4" />
                {assignment.metrics.on_time} ({assignment.metrics.on_time_percentage.toFixed(1)}%)
              </span>
              <span className="text-amber-600 flex items-center gap-1">
                <Clock className="w-4 h-4" />
                {assignment.metrics.late} ({assignment.metrics.late_percentage.toFixed(1)}%)
              </span>
              <span className="text-red-600 flex items-center gap-1">
                <XCircle className="w-4 h-4" />
                {assignment.metrics.missing} ({assignment.metrics.missing_percentage.toFixed(1)}%)
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AssignmentStatusBreakdown;
