/**
 * Centralized API client for backend communication
 */

// Use environment variable if available, otherwise empty string for relative URLs
// In Docker with Nginx proxy, we use relative URLs which Nginx forwards to backend
const BACKEND_URL = import.meta.env.VITE_API_ENDPOINT || '';

/**
 * Fetch wrapper with error handling and JSON parsing
 * @param {string} endpoint - API endpoint (e.g., '/api/settings')
 * @param {RequestInit} options - Fetch options
 * @returns {Promise<any>} - Parsed JSON response
 */
export async function apiFetch(endpoint, options = {}) {
  const url = `${BACKEND_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorData.message || errorMessage;
      } catch {
        // Fallback to status text if JSON parsing fails
      }
      throw new Error(errorMessage);
    }

    // Try to parse JSON, fallback to text if it fails
    try {
      return await response.json();
    } catch {
      return await response.text();
    }
  } catch (error) {
    // Re-throw with additional context
    if (error instanceof Error) {
      throw error;
    }
    throw new Error(`API request failed: ${error}`);
  }
}

export { BACKEND_URL };
