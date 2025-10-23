/**
 * AWS Amplify configuration for Cognito authentication
 * Configured for the multi-tenant Canvas TA Dashboard
 */

const awsConfig = {
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID || 'us-east-1_tWkVeJFdB',
      userPoolClientId: import.meta.env.VITE_COGNITO_USER_POOL_CLIENT_ID || '2eubr2jab24qlnbqm44fn6tb29',
      region: 'us-east-1',
      signUpVerificationMethod: 'code', // 'code' | 'link'
      loginWith: {
        email: true,
        username: false,
        phone: false,
      },
      userAttributes: {
        email: {
          required: true,
        },
        name: {
          required: true,
        },
      },
    },
  },
};

export default awsConfig;