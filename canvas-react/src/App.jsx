import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import EnhancedTADashboard from './EnhancedTADashboard';
import LateDaysTracking from './LateDaysTracking';
import PeerReviewTracking from './PeerReviewTracking';
import EnrollmentTracking from './EnrollmentTracking';
import Settings from './Settings';
import Navigation from './components/Navigation';
import GradingScheduleSummary from './components/GradingScheduleSummary';
import { RefreshCw } from 'lucide-react';
import { apiFetch, BACKEND_URL } from './api';
import { setTimezone, formatDate } from './utils/dates';

const AppContent = () => {
  const location = useLocation();
  const [courses, setCourses] = useState([]);
  const [configuredCourse, setConfiguredCourse] = useState(null); // from settings
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [lastSyncedAt, setLastSyncedAt] = useState(null);
  const [previousPath, setPreviousPath] = useState(location.pathname);
  const [taBreakdownMode, setTaBreakdownMode] = useState('group');

  const loadSettings = useCallback(async () => {
    try {
      const data = await apiFetch('/api/settings');
      if (data.course_id) {
        setConfiguredCourse({ id: data.course_id, name: data.course_name || data.course_id });
      } else {
        setConfiguredCourse(null);
      }
      setTimezone(data.timezone ?? null);
      setTaBreakdownMode(data.ta_breakdown_mode ?? 'group');
      // Best-effort: initialize lastSyncedAt from last known sync time
      try {
        const syncData = await apiFetch('/api/canvas/sync/status');
        if (syncData?.last_sync?.completed_at) {
          setLastSyncedAt(new Date(syncData.last_sync.completed_at));
        }
      } catch {
        // Silently fail — lastSyncedAt will remain null until first sync
      }
    } catch (err) {
      console.error('Error loading settings:', err);
    }
  }, []);

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
      // Reload settings and courses after sync
      loadSettings();
      loadCourses();
      setLastSyncedAt(new Date());
      setRefreshTrigger(prev => prev + 1);
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

  // Load settings and courses on mount
  useEffect(() => {
    loadSettings();
    loadCourses();
  }, [loadSettings, loadCourses]);

  // Reload settings and courses when navigating away from Settings
  useEffect(() => {
    if (previousPath === '/settings' && location.pathname !== '/settings') {
      loadSettings();
      loadCourses();
    }
    setPreviousPath(location.pathname);
  }, [location.pathname, previousPath, loadSettings, loadCourses]);

  // Clear sync message after 5 seconds
  useEffect(() => {
    if (syncMessage) {
      const timer = setTimeout(() => setSyncMessage(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [syncMessage]);

  // Active course: find configured course in synced courses (for term info), fall back to settings
  const activeCourseId = configuredCourse?.id ?? null;
  const syncedActiveCourse = activeCourseId
    ? courses.find(c => String(c.id) === String(activeCourseId)) ?? null
    : null;
  // Use synced course for term info if available, otherwise show configured course name
  const activeCourse = syncedActiveCourse ?? configuredCourse;

  return (
    <>
      {/* Header with Refresh Button */}
      <header className="bg-white shadow-sm border-b sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Canvas TA Dashboard</h1>
            {activeCourse && (
              <p className="text-sm text-gray-500 leading-tight">
                {activeCourse.name}{activeCourse.term ? ` — ${activeCourse.term}` : ''}
              </p>
            )}
          </div>
          <div className="flex items-center gap-4">
            {syncMessage && (
              <span
                className={`text-sm ${syncMessage.type === 'success' ? 'text-green-600' : 'text-red-600'
                  }`}
              >
                {syncMessage.text}
              </span>
            )}
            {lastSyncedAt && !syncMessage && (
              <span className="text-xs text-gray-500">
                Synced: {formatDate(lastSyncedAt)}
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
                activeCourseId={activeCourseId}
                refreshTrigger={refreshTrigger}
                taBreakdownMode={taBreakdownMode}
              />
            }
          />
          <Route
            path="/late-days"
            element={
              <LateDaysTracking
                courses={courses}
                onLoadCourses={loadCourses}
                activeCourseId={activeCourseId}
                refreshTrigger={refreshTrigger}
              />
            }
          />
          <Route
            path="/peer-reviews"
            element={
              <PeerReviewTracking
                courses={courses}
                onLoadCourses={loadCourses}
                activeCourseId={activeCourseId}
              />
            }
          />
          <Route
            path="/enrollment"
            element={
              <EnrollmentTracking
                courses={courses}
                onLoadCourses={loadCourses}
                activeCourseId={activeCourseId}
                refreshTrigger={refreshTrigger}
              />
            }
          />
          <Route
            path="/grading-schedule"
            element={
              <GradingScheduleSummary
                activeCourseId={activeCourseId}
                refreshTrigger={refreshTrigger}
              />
            }
          />
          <Route
            path="/settings"
            element={<Settings />}
          />
        </Routes>
      </main>
    </>
  );
};

const App = () => {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
};

export default App;
