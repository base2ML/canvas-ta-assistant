import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import EnhancedTADashboard from './EnhancedTADashboard';
import LateDaysTracking from './LateDaysTracking';
import PeerReviewTracking from './PeerReviewTracking';
import EnrollmentTracking from './EnrollmentTracking';
import Settings from './Settings';
import Navigation from './components/Navigation';
import { RefreshCw } from 'lucide-react';
import { apiFetch, BACKEND_URL } from './api';

const App = () => {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState(null);

  const loadCourses = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiFetch('/api/canvas/courses');
      setCourses(data.courses || []);
    } catch (err) {
      console.error('Error loading courses:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleRefreshData = async () => {
    setSyncing(true);
    setSyncMessage(null);
    try {
      const data = await apiFetch('/api/canvas/sync', { method: 'POST' });
      setSyncMessage({
        type: 'success',
        text: `Synced ${data.stats?.assignments || 0} assignments, ${data.stats?.users || 0} users`,
      });
      // Reload courses after sync
      loadCourses();
    } catch (err) {
      console.error('Sync failed:', err);
      setSyncMessage({
        type: 'error',
        text: err.message || 'Failed to connect to server',
      });
    } finally {
      setSyncing(false);
    }
  };

  // Load courses on mount
  useEffect(() => {
    loadCourses();
  }, [loadCourses]);

  // Clear sync message after 5 seconds
  useEffect(() => {
    if (syncMessage) {
      const timer = setTimeout(() => setSyncMessage(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [syncMessage]);

  return (
    <BrowserRouter>
      {/* Header with Refresh Button */}
      <header className="bg-white shadow-sm border-b sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
          <h1 className="text-xl font-bold text-gray-900">Canvas TA Dashboard</h1>
          <div className="flex items-center gap-4">
            {syncMessage && (
              <span
                className={`text-sm ${syncMessage.type === 'success' ? 'text-green-600' : 'text-red-600'
                  }`}
              >
                {syncMessage.text}
              </span>
            )}
            <button
              onClick={handleRefreshData}
              disabled={syncing}
              className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
              {syncing ? 'Syncing...' : 'Refresh Data'}
            </button>
          </div>
        </div>
      </header>

      <Navigation />

      <main className="min-h-screen bg-gray-50">
        <Routes>
          <Route
            path="/"
            element={
              <EnhancedTADashboard
                courses={courses}
                onLoadCourses={loadCourses}
                loadingCourses={loading}
              />
            }
          />
          <Route
            path="/late-days"
            element={
              <LateDaysTracking
                courses={courses}
                onLoadCourses={loadCourses}
              />
            }
          />
          <Route
            path="/peer-reviews"
            element={
              <PeerReviewTracking
                courses={courses}
                onLoadCourses={loadCourses}
              />
            }
          />
          <Route
            path="/enrollment"
            element={
              <EnrollmentTracking
                courses={courses}
                onLoadCourses={loadCourses}
              />
            }
          />
          <Route
            path="/settings"
            element={<Settings />}
          />
        </Routes>
      </main>
    </BrowserRouter>
  );
};

export default App;
