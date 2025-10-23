import { useEffect, useState } from 'react'
import { getCurrentUser, signOut } from 'aws-amplify/auth'
import { Authenticator } from '@aws-amplify/ui-react'
import '@aws-amplify/ui-react/styles.css'
import { User, LogOut, Loader2 } from 'lucide-react'

/**
 * Authentication wrapper component that handles Cognito login/logout
 * and protects the main application
 */
export default function AuthWrapper({ children }) {
  const [isLoading, setIsLoading] = useState(true)
  const [currentUser, setCurrentUser] = useState(null)

  // Check authentication state on mount
  useEffect(() => {
    checkAuthState()
  }, [])

  const checkAuthState = async () => {
    try {
      const user = await getCurrentUser()
      setCurrentUser(user)
    } catch {
      // User is not authenticated
      setCurrentUser(null)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSignOut = async () => {
    try {
      await signOut()
      setCurrentUser(null)
    } catch (error) {
      console.error('Error signing out:', error)
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

  // If user is authenticated, show the main app with logout button
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
                  <span>{currentUser.username}</span>
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

  // If user is not authenticated, show the enhanced landing page
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        <div className="max-w-7xl mx-auto">
          <div className="relative z-10 pb-8 bg-gradient-to-br from-blue-50 to-indigo-100 sm:pb-16 md:pb-20 lg:w-full lg:pb-28 xl:pb-32">
            <main className="mt-10 mx-auto max-w-7xl px-4 sm:mt-12 sm:px-6 md:mt-16 lg:mt-20 lg:px-8 xl:mt-28">
              <div className="text-center lg:text-left">
                <h1 className="text-4xl tracking-tight font-extrabold text-gray-900 sm:text-5xl md:text-6xl">
                  <span className="block">Canvas TA</span>{' '}
                  <span className="block text-indigo-600">Dashboard</span>
                </h1>
                <p className="mt-3 text-base text-gray-500 sm:mt-5 sm:text-lg sm:max-w-xl sm:mx-auto md:mt-5 md:text-xl lg:mx-0">
                  Streamline your teaching assistant workflow with automated grading management,
                  assignment tracking, and student progress monitoring.
                </p>
                <div className="mt-5 sm:mt-8 sm:flex sm:justify-center lg:justify-start">
                  <div className="rounded-md shadow">
                    <p className="text-sm text-gray-600 mb-4">
                      🚀 Ready to get started? Sign up below to access your dashboard.
                    </p>
                  </div>
                </div>
              </div>
            </main>
          </div>
        </div>
      </div>

      {/* Authentication Section */}
      <div className="relative -mt-16">
        <div className="flex flex-col justify-center py-12 sm:px-6 lg:px-8">
          <div className="sm:mx-auto sm:w-full sm:max-w-md">
            <div className="bg-white py-8 px-4 shadow-xl rounded-lg sm:px-10">
              <div className="mb-6 text-center">
                <h2 className="text-2xl font-bold text-gray-900">
                  Get Started Today
                </h2>
                <p className="mt-2 text-sm text-gray-600">
                  Create your account or sign in to continue
                </p>
              </div>

              <Authenticator
                signUpAttributes={['email', 'name']}
                loginMechanisms={['email']}
                hideSignUp={false}
                formFields={{
                  signUp: {
                    email: {
                      order: 1,
                      placeholder: 'Enter your email address',
                    },
                    name: {
                      order: 2,
                      placeholder: 'Enter your full name',
                    },
                    password: {
                      order: 3,
                    },
                    confirm_password: {
                      order: 4,
                    },
                  },
                }}
              >
                {({ user }) => {
                  // This should not be reached as we handle auth state above
                  // but included for completeness
                  if (user && !currentUser) {
                    setCurrentUser(user)
                  }
                  return null
                }}
              </Authenticator>

              <div className="mt-6 text-center">
                <p className="text-xs text-gray-500">
                  By signing up, you agree to access your Canvas TA tools securely through AWS Cognito
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="py-12 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="lg:text-center">
            <h2 className="text-base text-indigo-600 font-semibold tracking-wide uppercase">Features</h2>
            <p className="mt-2 text-3xl leading-8 font-extrabold tracking-tight text-gray-900 sm:text-4xl">
              Everything you need to manage your TA workflow
            </p>
          </div>

          <div className="mt-10">
            <div className="space-y-10 md:space-y-0 md:grid md:grid-cols-2 md:gap-x-8 md:gap-y-10">
              <div className="relative">
                <div className="absolute flex items-center justify-center h-12 w-12 rounded-md bg-indigo-500 text-white">
                  📊
                </div>
                <p className="ml-16 text-lg leading-6 font-medium text-gray-900">Assignment Tracking</p>
                <p className="mt-2 ml-16 text-base text-gray-500">
                  Monitor assignment due dates, submission status, and grading progress across all your courses.
                </p>
              </div>

              <div className="relative">
                <div className="absolute flex items-center justify-center h-12 w-12 rounded-md bg-indigo-500 text-white">
                  👥
                </div>
                <p className="ml-16 text-lg leading-6 font-medium text-gray-900">TA Workload Management</p>
                <p className="mt-2 ml-16 text-base text-gray-500">
                  Distribute grading tasks evenly across your TA team and track completion status.
                </p>
              </div>

              <div className="relative">
                <div className="absolute flex items-center justify-center h-12 w-12 rounded-md bg-indigo-500 text-white">
                  🔗
                </div>
                <p className="ml-16 text-lg leading-6 font-medium text-gray-900">Canvas Integration</p>
                <p className="mt-2 ml-16 text-base text-gray-500">
                  Seamlessly connects with Canvas LMS through automated data synchronization.
                </p>
              </div>

              <div className="relative">
                <div className="absolute flex items-center justify-center h-12 w-12 rounded-md bg-indigo-500 text-white">
                  🔒
                </div>
                <p className="ml-16 text-lg leading-6 font-medium text-gray-900">Secure Authentication</p>
                <p className="mt-2 ml-16 text-base text-gray-500">
                  Enterprise-grade security with AWS Cognito - no Canvas credentials required.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}