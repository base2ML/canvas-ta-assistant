# Authentication System Guide

## How Authentication Works

### Architecture Overview

```
User → React Frontend → AWS Cognito → API Gateway → Lambda (validates JWT)
```

### Authentication Flow

1. **User Signs In**:
   - User enters email and password in React frontend
   - AWS Amplify UI component sends credentials to Cognito
   - Cognito validates credentials and returns JWT tokens

2. **Token Management**:
   - AWS Amplify automatically stores tokens in browser localStorage
   - Access token (JWT) included in all API requests
   - Token automatically refreshed when expired

3. **API Request Authorization**:
   - Frontend includes JWT token in Authorization header
   - API Gateway forwards request to Lambda
   - Lambda validates JWT token with Cognito
   - If valid, request proceeds; if invalid, returns 403

### JWT Token Structure

The JWT token contains:
```json
{
  "sub": "f488a458-b0a1-7034-8c27-b393f2c9b12d",  // User ID
  "email": "testuser@example.com",
  "cognito:username": "testuser@example.com",
  "token_use": "access",
  "auth_time": 1698012345,
  "exp": 1698015945  // Expiration time
}
```

## How to Administer Users

### Method 1: AWS CLI (Recommended for Setup)

#### Create a New User

```bash
aws cognito-idp admin-create-user \
  --user-pool-id us-east-1_tWkVeJFdB \
  --username admin@gatech.edu \
  --user-attributes \
    Name=email,Value=admin@gatech.edu \
    Name=email_verified,Value=true \
  --temporary-password "TempPass123!" \
  --message-action SUPPRESS
```

#### Set Permanent Password

```bash
aws cognito-idp admin-set-user-password \
  --user-pool-id us-east-1_tWkVeJFdB \
  --username admin@gatech.edu \
  --password "YourSecurePassword123!" \
  --permanent
```

#### List All Users

```bash
aws cognito-idp list-users \
  --user-pool-id us-east-1_tWkVeJFdB
```

#### Delete a User

```bash
aws cognito-idp admin-delete-user \
  --user-pool-id us-east-1_tWkVeJFdB \
  --username testuser@example.com
```

#### Disable a User

```bash
aws cognito-idp admin-disable-user \
  --user-pool-id us-east-1_tWkVeJFdB \
  --username testuser@example.com
```

#### Enable a User

```bash
aws cognito-idp admin-enable-user \
  --user-pool-id us-east-1_tWkVeJFdB \
  --username testuser@example.com
```

#### Reset User Password

```bash
aws cognito-idp admin-reset-user-password \
  --user-pool-id us-east-1_tWkVeJFdB \
  --username admin@gatech.edu
```

### Method 2: AWS Console (GUI)

1. **Navigate to Cognito**:
   - Go to AWS Console → Cognito
   - Select "canvas-ta-dashboard-prod-user-pool"

2. **Manage Users**:
   - Click "Users" in left sidebar
   - Click "Create user" button
   - Fill in email and temporary password
   - Check "Mark email as verified"
   - Click "Create user"

3. **User Status**:
   - **FORCE_CHANGE_PASSWORD**: User must change password on first login
   - **CONFIRMED**: User has changed password and is active
   - **DISABLED**: User cannot login

### Method 3: Terraform (Infrastructure as Code)

For automated user creation during deployment:

```hcl
resource "aws_cognito_user" "admin" {
  user_pool_id = aws_cognito_user_pool.main.id
  username     = "admin@gatech.edu"

  attributes = {
    email          = "admin@gatech.edu"
    email_verified = true
  }
}
```

## Authentication Configuration

### Current Settings

- **User Pool ID**: `us-east-1_tWkVeJFdB`
- **Client ID**: `2eubr2jab24qlnbqm44fn6tb29`
- **Domain**: `canvas-ta-dashboard-prod-auth`
- **MFA**: OFF (can be enabled per user)
- **Password Policy**:
  - Minimum length: 8 characters
  - Require uppercase: Yes
  - Require lowercase: Yes
  - Require numbers: Yes
  - Require symbols: No

### Frontend Configuration

The React app uses AWS Amplify configured in `canvas-react/src/aws-config.js`:

```javascript
const awsConfig = {
  Auth: {
    Cognito: {
      userPoolId: 'us-east-1_tWkVeJFdB',
      userPoolClientId: '2eubr2jab24qlnbqm44fn6tb29',
      region: 'us-east-1',
      signUpVerificationMethod: 'code',
      loginWith: {
        email: true,
        username: false,
        phone: false,
      }
    }
  }
}
```

### Backend Configuration

The Lambda function validates JWT tokens by checking:
1. Token signature (signed by Cognito)
2. Token expiration
3. Token audience (client ID)
4. Token issuer (Cognito user pool)

This is handled automatically by the FastAPI dependency injection system.

## User Management Best Practices

### For TAs and Instructors

1. **Use Georgia Tech Emails**:
   ```bash
   aws cognito-idp admin-create-user \
     --user-pool-id us-east-1_tWkVeJFdB \
     --username ta1@gatech.edu \
     --user-attributes Name=email,Value=ta1@gatech.edu Name=email_verified,Value=true
   ```

2. **Set Strong Passwords**:
   - Minimum 10 characters
   - Mix of uppercase, lowercase, numbers
   - Consider using password manager

3. **Disable Users When Course Ends**:
   ```bash
   aws cognito-idp admin-disable-user \
     --user-pool-id us-east-1_tWkVeJFdB \
     --username old-ta@gatech.edu
   ```

4. **Rotate Passwords Regularly**:
   ```bash
   aws cognito-idp admin-reset-user-password \
     --user-pool-id us-east-1_tWkVeJFdB \
     --username ta@gatech.edu
   ```

### Security Recommendations

1. **Enable MFA for Admins** (optional):
   ```bash
   aws cognito-idp admin-set-user-mfa-preference \
     --user-pool-id us-east-1_tWkVeJFdB \
     --username admin@gatech.edu \
     --software-token-mfa-settings Enabled=true,PreferredMfa=true
   ```

2. **Monitor Sign-In Activity**:
   ```bash
   aws cognito-idp admin-list-user-auth-events \
     --user-pool-id us-east-1_tWkVeJFdB \
     --username ta@gatech.edu
   ```

3. **Set Up CloudWatch Alarms**:
   - Failed login attempts
   - Unusual access patterns
   - Token refresh failures

## Troubleshooting

### User Cannot Login

1. **Check user status**:
   ```bash
   aws cognito-idp admin-get-user \
     --user-pool-id us-east-1_tWkVeJFdB \
     --username user@example.com
   ```

2. **Verify email is confirmed**:
   - Look for `"Name": "email_verified", "Value": "true"`

3. **Check if user is disabled**:
   - Look for `"Enabled": false`

### Token Expired Errors

- Tokens expire after 1 hour by default
- AWS Amplify automatically refreshes tokens
- If seeing errors, clear browser localStorage and re-login

### API Returns 403 Forbidden

1. **Check token is being sent**:
   - Open browser DevTools → Network tab
   - Look for Authorization header in requests

2. **Verify token format**:
   - Should be: `Authorization: Bearer eyJraWQ...`

3. **Check Lambda logs**:
   ```bash
   aws logs tail /aws/lambda/canvas-ta-dashboard-prod-api-handler --follow
   ```

## Quick Reference Commands

### Create User
```bash
aws cognito-idp admin-create-user \
  --user-pool-id us-east-1_tWkVeJFdB \
  --username EMAIL \
  --user-attributes Name=email,Value=EMAIL Name=email_verified,Value=true \
  --temporary-password "TempPass123!"
```

### Set Password
```bash
aws cognito-idp admin-set-user-password \
  --user-pool-id us-east-1_tWkVeJFdB \
  --username EMAIL \
  --password "PASSWORD" \
  --permanent
```

### List Users
```bash
aws cognito-idp list-users \
  --user-pool-id us-east-1_tWkVeJFdB \
  --limit 10
```

### Delete User
```bash
aws cognito-idp admin-delete-user \
  --user-pool-id us-east-1_tWkVeJFdB \
  --username EMAIL
```

## Environment Variables

The following credentials are required for the system:

**Frontend** (`.env` in `canvas-react/`):
```bash
VITE_COGNITO_USER_POOL_ID=us-east-1_tWkVeJFdB
VITE_COGNITO_USER_POOL_CLIENT_ID=2eubr2jab24qlnbqm44fn6tb29
VITE_API_ENDPOINT=https://1giptvnvj1.execute-api.us-east-1.amazonaws.com/prod
```

**Backend** (Lambda environment variables - auto-configured by Terraform):
```bash
ENVIRONMENT=prod
S3_BUCKET_NAME=canvas-ta-dashboard-prod-canvas-data
COGNITO_USER_POOL_ID=us-east-1_tWkVeJFdB
COGNITO_USER_POOL_CLIENT_ID=2eubr2jab24qlnbqm44fn6tb29
```

## Support

For authentication issues:
1. Check CloudWatch logs for Lambda function
2. Verify user status in Cognito console
3. Test with known-good credentials
4. Review API Gateway logs for 403 errors

---

**Last Updated**: 2025-10-22
**Cognito User Pool**: us-east-1_tWkVeJFdB
**Region**: us-east-1
