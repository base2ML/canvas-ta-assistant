import { useAuthenticator } from '@aws-amplify/ui-react'

/**
 * Authentication context hook for accessing auth state in child components
 */
export function useAuth() {
  const { user, signOut } = useAuthenticator((context) => [context.user, context.signOut])

  return {
    user,
    signOut,
    isAuthenticated: !!user,
  }
}
