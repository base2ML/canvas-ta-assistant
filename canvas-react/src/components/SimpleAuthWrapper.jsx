import { useEffect, useState } from 'react'
import { User, LogOut, Loader2 } from 'lucide-react'
import LoginForm from './LoginForm'

/**
 * Simple authentication wrapper without AWS Amplify
 * Manages JWT token-based authentication
 */
export default function SimpleAuthWrapper({ children }) {
  const [isLoading, setIsLoading] = useState(true)
  const [currentUser, setCurrentUser] = useState(null)

  // Check authentication state on mount
  useEffect(() => {
    checkAuthState()
  }, [])

  const checkAuthState = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const userJson = localStorage.getItem('user')

      if (!token || !userJson) {
        setCurrentUser(null)
        setIsLoading(false)
        return
      }

      // Verify token is still valid by calling the API
      const apiEndpoint = import.meta.env.VITE_API_ENDPOINT || 'http://localhost:8000'

      const response = await fetch(`${apiEndpoint}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (response.ok) {
        const user = JSON.parse(userJson)
        setCurrentUser(user)
      } else {
        // Token is invalid, clear storage
        localStorage.removeItem('access_token')
        localStorage.removeItem('user')
        setCurrentUser(null)
      }
    } catch (error) {
      console.error('Auth check failed:', error)
      setCurrentUser(null)
    } finally {
      setIsLoading(false)
    }
  }

  const handleLoginSuccess = (user) => {
    setCurrentUser(user)
  }

  const handleSignOut = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const apiEndpoint = import.meta.env.VITE_API_ENDPOINT || 'http://localhost:8000'

      // Call logout endpoint (optional, just logs the event)
      if (token) {
        await fetch(`${apiEndpoint}/api/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
      }
    } catch (error) {
      console.error('Logout API call failed:', error)
    } finally {
      // Clear local storage regardless of API call success
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      setCurrentUser(null)
    }
  }

  // Show loading spinner while checking auth state
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-blue-600" />
          <p className="mt-2 text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  // If user is authenticated, show the main app with navigation
  if (currentUser) {
    return (
      <div className="min-h-screen bg-gray-50">
        {/* Navigation bar with user info and logout */}
        <nav className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16 items-center">
              <div className="flex items-center">
                <h1 className="text-xl font-semibold text-gray-900">Canvas TA Dashboard</h1>
              </div>
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2 text-sm text-gray-600">
                  <User className="h-4 w-4" />
                  <span>{currentUser.name || currentUser.email}</span>
                </div>
                <button
                  onClick={handleSignOut}
                  className="inline-flex items-center space-x-2 px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          </div>
        </nav>

        {/* Main application content */}
        <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          {children}
        </main>
      </div>
    )
  }

  // If user is not authenticated, show login form
  return <LoginForm onLoginSuccess={handleLoginSuccess} />
}
