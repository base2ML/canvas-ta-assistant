import React from 'react';
import { Users, CheckCircle, Clock, XCircle } from 'lucide-react';

const SubmissionStatusCards = ({ metrics }) => {
  if (!metrics) return null;

  return (
    <div className="grid grid-cols-4 gap-4 mb-6">
      {/* Total Card */}
      <div className="bg-slate-100 border-2 border-slate-300 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <Users className="w-5 h-5 text-slate-600" />
          <span className="text-sm font-medium text-slate-600">TOTAL</span>
        </div>
        <div className="text-3xl font-bold text-slate-900">
          {metrics.total_expected}
        </div>
      </div>

      {/* On Time Card */}
      <div className="bg-green-50 border-2 border-green-300 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <CheckCircle className="w-5 h-5 text-green-600" />
          <span className="text-sm font-medium text-green-700">ON TIME</span>
        </div>
        <div className="text-3xl font-bold text-green-900">
          {metrics.on_time}
        </div>
        <div className="text-sm text-green-600 mt-1">
          {metrics.on_time_percentage.toFixed(1)}%
        </div>
      </div>

      {/* Late Card */}
      <div className="bg-amber-50 border-2 border-amber-300 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <Clock className="w-5 h-5 text-amber-600" />
          <span className="text-sm font-medium text-amber-700">LATE</span>
        </div>
        <div className="text-3xl font-bold text-amber-900">
          {metrics.late}
        </div>
        <div className="text-sm text-amber-600 mt-1">
          {metrics.late_percentage.toFixed(1)}%
        </div>
      </div>

      {/* Missing Card */}
      <div className="bg-red-50 border-2 border-red-300 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <XCircle className="w-5 h-5 text-red-600" />
          <span className="text-sm font-medium text-red-700">MISSING</span>
        </div>
        <div className="text-3xl font-bold text-red-900">
          {metrics.missing}
        </div>
        <div className="text-sm text-red-600 mt-1">
          {metrics.missing_percentage.toFixed(1)}%
        </div>
      </div>
    </div>
  );
};

export default SubmissionStatusCards;
