import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Settings, Calendar, User, Server, Users } from 'lucide-react';
import TAGradingDashboard from './TAGradingDashboard';
import LateDaysTracking from './LateDaysTracking';

const App = () => {
  const [apiUrl, setApiUrl] = useState(import.meta.env.VITE_CANVAS_API_URL || '');
  const [apiToken, setApiToken] = useState(import.meta.env.VITE_CANVAS_API_KEY || '');
  const [courseIds, setCourseIds] = useState(import.meta.env.VITE_CANVAS_COURSE_ID || '');
  const [backendUrl, setBackendUrl] = useState(import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000');
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isConfigured, setIsConfigured] = useState(false);
  const [userInfo, setUserInfo] = useState(null);
  const [showTADashboard, setShowTADashboard] = useState(false);
  const [showLateDays, setShowLateDays] = useState(false);

  // Load saved credentials on mount
  useEffect(() => {
    const savedUrl = localStorage.getItem('canvas_api_url');
    const savedToken = localStorage.getItem('canvas_api_token');
    const savedCourseIds = localStorage.getItem('canvas_course_ids');
    const savedBackendUrl = localStorage.getItem('backend_url');
    
    // Use saved values, fallback to environment variables, then empty string
    const finalUrl = savedUrl || import.meta.env.VITE_CANVAS_API_URL || '';
    const finalToken = savedToken || import.meta.env.VITE_CANVAS_API_KEY || '';
    const finalCourseIds = savedCourseIds || import.meta.env.VITE_CANVAS_COURSE_ID || '';
    const finalBackendUrl = savedBackendUrl || import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
    
    // Update state with final values
    setApiUrl(finalUrl);
    setApiToken(finalToken);
    setCourseIds(finalCourseIds);
    setBackendUrl(finalBackendUrl);
    
    // If we have all required values (either saved or from env), auto-configure
    if (finalUrl && finalToken && finalCourseIds) {
      setIsConfigured(true);
      // Just validate credentials and set courses for TA dashboard
      validateAndSetCourses(finalUrl, finalToken, finalCourseIds, finalBackendUrl);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Intentionally empty - only run on mount

  const validateCredentials = async (url, token, backend) => {
    try {
      console.log('Validating credentials...', { url, backend });
      
      const response = await fetch(`${backend}/api/validate-credentials`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          base_url: url,
          api_token: token
        })
      });

      const data = await response.json();
      console.log('Validation response:', data);
      
      if (response.ok && data.valid) {
        setUserInfo(data.user);
        return true;
      } else {
        throw new Error(data.error || 'Invalid credentials');
      }
    } catch (err) {
      console.error('Validation error:', err);
      throw new Error(`Failed to validate credentials: ${err.message}`);
    }
  };

  const testConnection = async () => {
    if (!apiUrl || !apiToken || !backendUrl) {
      setError('Please fill in Canvas URL, API token, and backend URL first');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${backendUrl}/api/test-connection`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          base_url: apiUrl,
          api_token: apiToken
        })
      });

      const data = await response.json();
      console.log('Connection test result:', data);
      
      if (data.success) {
        setError('✅ Connection test successful! Your credentials should work.');
      } else {
        setError(`❌ Connection test failed: ${data.error}\n\nURL tested: ${data.url_tested}\nStatus: ${data.status_code || 'Network error'}`);
      }
    } catch (err) {
      setError(`❌ Connection test failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const saveCredentials = async () => {
    if (!apiUrl || !apiToken || !courseIds || !backendUrl) {
      setError('Please fill in all required fields');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // First validate credentials
      await validateCredentials(apiUrl, apiToken, backendUrl);
      
      // Save to localStorage
      localStorage.setItem('canvas_api_url', apiUrl);
      localStorage.setItem('canvas_api_token', apiToken);
      localStorage.setItem('canvas_course_ids', courseIds);
      localStorage.setItem('backend_url', backendUrl);
      
      setIsConfigured(true);
      
      // Set courses for TA dashboard
      await validateAndSetCourses(apiUrl, apiToken, courseIds, backendUrl);
      
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const validateAndSetCourses = useCallback(async (url = apiUrl, token = apiToken, courseIdList = courseIds, backend = backendUrl) => {
    setLoading(true);
    setError('');
    
    try {
      const courseIdArray = courseIdList.split(',').map(id => id.trim()).filter(id => id);
      
      if (courseIdArray.length === 0) {
        throw new Error('Please provide at least one course ID');
      }

      const response = await fetch(`${backend}/api/assignments`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          base_url: url,
          api_token: token,
          course_ids: courseIdArray
        })
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Failed to fetch course data');
      }

      setCourses(data.courses || []);

    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, [apiUrl, apiToken, courseIds, backendUrl]);

  const handleRefresh = () => {
    validateAndSetCourses();
  };

  const handleTestConnection = () => {
    testConnection();
  };

  const handleSaveCredentials = () => {
    saveCredentials();
  };


  if (!isConfigured) {
    return (
      <div className="max-w-lg mx-auto mt-8 p-6 bg-white rounded-lg shadow-lg">
        <div className="text-center mb-6">
          <Server className="mx-auto h-12 w-12 text-purple-500 mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">TA Canvas Dashboard Setup</h1>
          <p className="text-gray-600">Configure Canvas API connection for TA assignment tracking</p>
          {(import.meta.env.VITE_CANVAS_API_URL || import.meta.env.VITE_CANVAS_API_KEY || import.meta.env.VITE_CANVAS_COURSE_ID) && (
            <p className="text-sm text-purple-600 mt-2">
              ✓ Default values loaded from environment variables
            </p>
          )}
        </div>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Backend URL
            </label>
            <input
              type="text"
              placeholder={import.meta.env.VITE_BACKEND_URL || "http://localhost:8000"}
              value={backendUrl}
              onChange={(e) => setBackendUrl(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              URL of your Python FastAPI backend server
            </p>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Canvas API URL
            </label>
            <input
              type="text"
              placeholder={import.meta.env.VITE_CANVAS_API_URL || "https://your-school.instructure.com"}
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              API Token
            </label>
            <input
              type="password"
              placeholder={import.meta.env.VITE_CANVAS_API_KEY ? "••••••••••••••••" : "Your Canvas API token"}
              value={apiToken}
              onChange={(e) => setApiToken(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              Generate this in Canvas: Account → Settings → Approved Integrations → New Access Token
            </p>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Course IDs
            </label>
            <input
              type="text"
              placeholder={import.meta.env.VITE_CANVAS_COURSE_ID || "12345, 67890, 11111 (comma-separated)"}
              value={courseIds}
              onChange={(e) => setCourseIds(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              Find course IDs in Canvas URLs (e.g., /courses/12345). Enter multiple IDs separated by commas.
            </p>
          </div>
          
          {error && (
            <div className="p-3 bg-red-100 border border-red-300 rounded-md text-red-700 text-sm whitespace-pre-line">
              {error}
            </div>
          )}
          
          <div className="flex space-x-2">
            <button
              onClick={handleTestConnection}
              disabled={loading}
              className="flex-1 bg-gray-500 text-white py-2 px-4 rounded-md hover:bg-gray-600 disabled:opacity-50 transition-colors flex items-center justify-center"
            >
              {loading ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Testing...
                </>
              ) : (
                'Test Connection'
              )}
            </button>
            <button
              onClick={handleSaveCredentials}
              disabled={loading}
              className="flex-1 bg-purple-500 text-white py-2 px-4 rounded-md hover:bg-purple-600 disabled:opacity-50 transition-colors flex items-center justify-center"
            >
              {loading ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Connecting...
                </>
              ) : (
                'Start TA Dashboard'
              )}
            </button>
          </div>
        </div>
      </div>
    );
  }


  // Show TA Dashboard if selected
  if (showTADashboard) {
    return (
      <TAGradingDashboard
        apiUrl={apiUrl}
        apiToken={apiToken}
        backendUrl={backendUrl}
        courses={courses}
        onBack={() => setShowTADashboard(false)}
        onLateDays={() => {
          setShowTADashboard(false);
          setShowLateDays(true);
        }}
      />
    );
  }

  // Show Late Days Tracking if selected
  if (showLateDays) {
    return (
      <LateDaysTracking
        apiUrl={apiUrl}
        apiToken={apiToken}
        backendUrl={backendUrl}
        courses={courses}
        onBack={() => setShowLateDays(false)}
        onTAGrading={() => {
          setShowLateDays(false);
          setShowTADashboard(true);
        }}
        onLoadCourses={() => validateAndSetCourses()}
      />
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg">
        {/* Header */}
        <div className="border-b border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">TA Canvas Dashboard</h1>
              <p className="text-gray-600 mt-1">Track assignment grading status across courses</p>
              {userInfo && (
                <div className="flex items-center mt-2 text-sm text-gray-500">
                  <User className="h-4 w-4 mr-1" />
                  {userInfo.name} ({userInfo.email})
                </div>
              )}
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => setShowTADashboard(!showTADashboard)}
                className="flex items-center px-4 py-2 bg-purple-500 text-white rounded-md hover:bg-purple-600 transition-colors"
              >
                <Users className="h-4 w-4 mr-2" />
                TA Grading
              </button>
              <button
                onClick={() => setShowLateDays(!showLateDays)}
                className="flex items-center px-4 py-2 bg-orange-500 text-white rounded-md hover:bg-orange-600 transition-colors"
              >
                <Calendar className="h-4 w-4 mr-2" />
                Late Days
              </button>
              <button
                onClick={handleRefresh}
                disabled={loading}
                className="flex items-center px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 transition-colors"
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
              <button
                onClick={() => {
                  localStorage.clear();
                  setIsConfigured(false);
                  setCourses([]);
                  setUserInfo(null);
                  setShowTADashboard(false);
                  setShowLateDays(false);
                }}
                className="flex items-center px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 transition-colors"
              >
                <Settings className="h-4 w-4 mr-2" />
                Settings
              </button>
            </div>
          </div>
        </div>



        {/* Error Display */}
        {error && (
          <div className="m-6 p-4 bg-red-100 border border-red-300 rounded-md text-red-700 whitespace-pre-line">
            {error}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="p-12 text-center">
            <RefreshCw className="h-8 w-8 animate-spin mx-auto text-blue-500 mb-4" />
            <p className="text-gray-600">Loading assignments...</p>
          </div>
        )}

        {/* TA Dashboard Access */}
        <div className="p-12 text-center">
          <Users className="h-16 w-16 mx-auto text-purple-500 mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Welcome to TA Dashboard</h2>
          <p className="text-gray-600 mb-6">Access the TA management tools to track grading progress and monitor student late days.</p>
          <div className="flex justify-center space-x-4">
            <button
              onClick={() => setShowTADashboard(true)}
              className="inline-flex items-center px-6 py-3 bg-purple-500 text-white rounded-md hover:bg-purple-600 transition-colors"
            >
              <Users className="h-5 w-5 mr-2" />
              TA Grading Dashboard
            </button>
            <button
              onClick={() => setShowLateDays(true)}
              className="inline-flex items-center px-6 py-3 bg-orange-500 text-white rounded-md hover:bg-orange-600 transition-colors"
            >
              <Calendar className="h-5 w-5 mr-2" />
              Late Days Tracking
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;