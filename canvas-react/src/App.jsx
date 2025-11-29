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
                apiUrl={backendUrl} // Using backendUrl as base for now, though it might expect Canvas URL
                apiToken={getApiToken()}
                courses={[]} // These components might need to load their own courses or receive them
                onLoadCourses={() => { }} // Placeholder
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
                courses={[]} // These components might need to load their own courses or receive them
              />
            }
          />
        </Routes>
      </SimpleAuthWrapper>
    </BrowserRouter>
  );
};

export default App;
