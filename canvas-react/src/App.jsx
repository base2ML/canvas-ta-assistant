import React, { useState } from 'react';
import SimpleAuthWrapper from './components/SimpleAuthWrapper';
import EnhancedTADashboard from './EnhancedTADashboard';

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

  return (
    <SimpleAuthWrapper>
      <EnhancedTADashboard
        backendUrl={backendUrl}
        getAuthHeaders={getAuthHeaders}
      />
    </SimpleAuthWrapper>
  );
};

export default App;