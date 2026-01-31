import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import EnhancedTADashboard from './EnhancedTADashboard';
import LateDaysTracking from './LateDaysTracking';
import Settings from './Settings';
import Navigation from './components/Navigation';
import { RefreshCw } from 'lucide-react';

const App = () => {
  const [backendUrl] = useState(
    import.meta.env.VITE_API_ENDPOINT || 'http://localhost:8000'
  );
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState(null);

  const loadCourses = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${backendUrl}/api/canvas/courses`);

      if (!response.ok) {
        throw new Error(`Failed to load courses: ${response.statusText}`);
      }

      const data = await response.json();
      setCourses(data.courses || []);
    } catch (err) {
      console.error('Error loading courses:', err);
    } finally {
      setLoading(false);
    }
  }, [backendUrl]);

  const handleRefreshData = async () => {
    setSyncing(true);
    setSyncMessage(null);
    try {
      const response = await fetch(`${backendUrl}/api/canvas/sync`, {
        method: 'POST',
      });

      if (response.ok) {
        const data = await response.json();
        setSyncMessage({
          type: 'success',
          text: `Synced ${data.stats?.assignments || 0} assignments, ${data.stats?.users || 0} users`,
        });
        // Reload courses after sync
        loadCourses();
      } else {
        const error = await response.json();
        setSyncMessage({
          type: 'error',
          text: error.detail || 'Sync failed',
        });
      }
    } catch (err) {
      console.error('Sync failed:', err);
      setSyncMessage({
        type: 'error',
        text: 'Failed to connect to server',
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
                backendUrl={backendUrl}
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
                backendUrl={backendUrl}
                apiUrl={backendUrl}
                courses={courses}
                onLoadCourses={loadCourses}
              />
            }
          />
          <Route
            path="/settings"
            element={<Settings backendUrl={backendUrl} />}
          />
        </Routes>
      </main>
    </BrowserRouter>
  );
};

export default App;
