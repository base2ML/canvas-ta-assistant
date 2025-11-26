// API endpoint configuration
export const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT ||
  (import.meta.env.MODE === 'production'
    ? 'https://your-cloudfront-domain.cloudfront.net/api'
    : 'http://localhost:8000');

// Export empty object to maintain compatibility if other files import it
const awsConfig = {};
export default awsConfig;
