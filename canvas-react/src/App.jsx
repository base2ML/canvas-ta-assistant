import React, { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import SimpleAuthWrapper from './components/SimpleAuthWrapper';
import EnhancedTADashboard from './EnhancedTADashboard';
import TAGradingDashboard from './TAGradingDashboard';
import LateDaysTracking from './LateDaysTracking';
import PeerReviewTracking from './PeerReviewTracking';
import Navigation from './components/Navigation';

const App = () => {
  const [backendUrl] = useState(
    import.meta.env.VITE_API_ENDPOINT || 'http://localhost:8000'
  );
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(false);
  // const [error, setError] = useState(''); // Unused

  const getAuthHeaders = () => {
    const token = localStorage.getItem('access_token');
    return {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    };
  };

  // Helper to get raw token for components that need it
  const getApiToken = () => {
    return localStorage.getItem('access_token') || '';
  };

  const loadCourses = React.useCallback(async () => {
    setLoading(true);
    try {
      const headers = getAuthHeaders();
      // Skip fetch if no token (e.g. not logged in)
      if (!headers['Authorization']) {
        setLoading(false);
        return;
      }

      const response = await fetch(`${backendUrl}/api/canvas/courses`, { headers });

      if (!response.ok) {
        throw new Error(`Failed to load courses: ${response.statusText}`);
      }

      const data = await response.json();
      setCourses(data.courses || []);
    } catch (err) {
      console.error('Error loading courses:', err);
      // setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [backendUrl]);

  // Load courses on mount or when auth changes (simplified for now)
  React.useEffect(() => {
    loadCourses();
  }, [loadCourses]);

  return (
    <BrowserRouter>
      <SimpleAuthWrapper>
        <Navigation />
        <Routes>
          <Route
            path="/"
            element={
              <EnhancedTADashboard
                backendUrl={backendUrl}
                getAuthHeaders={getAuthHeaders}
                courses={courses}
                onLoadCourses={loadCourses}
                loadingCourses={loading}
              />
            }
          />
          <Route
            path="/grading"
            element={
              <TAGradingDashboard
                backendUrl={backendUrl}
                getAuthHeaders={getAuthHeaders}
              />
            }
          />
          <Route
            path="/late-days"
            element={
              <LateDaysTracking
                backendUrl={backendUrl}
                apiUrl={backendUrl}
                apiToken={getApiToken()}
                courses={courses}
                onLoadCourses={loadCourses}
              />
            }
          />
          <Route
            path="/peer-reviews"
            element={
              <PeerReviewTracking
                backendUrl={backendUrl}
                apiUrl={backendUrl}
                apiToken={getApiToken()}
                courses={courses}
              />
            }
          />
        </Routes>
      </SimpleAuthWrapper>
    </BrowserRouter>
  );
};

export default App;
