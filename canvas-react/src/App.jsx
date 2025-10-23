import React, { useState } from 'react';
import { fetchAuthSession } from 'aws-amplify/auth';
import AuthWrapper from './components/AuthWrapper';
import EnhancedTADashboard from './EnhancedTADashboard';

const App = () => {
  const [backendUrl] = useState(
    import.meta.env.VITE_API_ENDPOINT ||
    'https://1giptvnvj1.execute-api.us-east-1.amazonaws.com/prod'
  );

  const getAuthHeaders = async () => {
    try {
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      };
    } catch (error) {
      console.error('Failed to get auth headers:', error);
      return {
        'Content-Type': 'application/json',
      };
    }
  };

  return (
    <AuthWrapper>
      <EnhancedTADashboard
        backendUrl={backendUrl}
        getAuthHeaders={getAuthHeaders}
      />
    </AuthWrapper>
  );
};

export default App;