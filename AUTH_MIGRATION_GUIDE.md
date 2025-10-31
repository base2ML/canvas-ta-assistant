# Authentication Migration Guide

## Overview

The Canvas TA Dashboard has migrated from AWS Cognito to a simple, maintainable JWT authentication system stored in S3. This guide covers the new authentication system and migration steps.

## What Changed

### Before (Cognito):
- ❌ AWS Cognito User Pool management
- ❌ Complex AWS Amplify SDK integration
- ❌ User sign-up flows and email verification
- ❌ ~300 lines of authentication code
- ❌ Monthly AWS Cognito costs

### After (Simple JWT):
- ✅ S3-stored user file with bcrypt-hashed passwords
- ✅ Simple login form (email + password)
- ✅ JWT tokens for stateless authentication
- ✅ ~150 lines of authentication code
- ✅ Zero authentication costs

## New Architecture

### Backend (`auth.py`)

**User Storage**:
- File: `s3://YOUR_BUCKET/auth/users.json`
- Format: JSON with bcrypt-hashed passwords
- Encrypted at rest (S3 server-side encryption)

**Authentication Flow**:
1. User submits email + password via `/api/auth/login`
2. Backend verifies password hash using bcrypt
3. Backend generates JWT token (7-day expiration)
4. Frontend stores JWT in localStorage
5. All API requests include JWT in `Authorization: Bearer <token>` header

**Security Features**:
- Bcrypt password hashing (cost factor 12)
- JWT token expiration (7 days)
- S3 encryption at rest (AES256)
- HTTPS transport (ALB)
- No plaintext passwords stored anywhere

### Frontend (`SimpleAuthWrapper.jsx`)

**Simple Login Flow**:
1. User sees login form (no sign-up)
2. Enter email + password
3. JWT token stored in `localStorage`
4. Auto-login on page refresh if token valid
5. Logout clears `localStorage`

**No Dependencies**:
- ❌ Removed `aws-amplify` package
- ❌ Removed `@aws-amplify/ui-react` package
- ✅ Pure React + fetch API

## User Management

### Adding Users (CLI)

```bash
# Add a new TA
python scripts/manage_users.py add ta1@gatech.edu "John Smith"

# Add an admin
python scripts/manage_users.py add admin@gatech.edu "Admin User" --role admin

# List all users
python scripts/manage_users.py list

# Remove a user
python scripts/manage_users.py remove ta1@gatech.edu
```

### User File Format (`s3://BUCKET/auth/users.json`)

```json
{
  "users": [
    {
      "email": "ta1@gatech.edu",
      "password_hash": "$2b$12$...",
      "name": "John Smith",
      "role": "ta",
      "created_at": "2025-10-31T12:00:00Z"
    }
  ]
}
```

**⚠️ IMPORTANT**: Never commit this file to git or store passwords in plaintext!

## Deployment Changes

### Terraform Updates

**Removed**:
- `modules/cognito/` - Entire Cognito module
- Cognito User Pool resources
- Cognito IAM permissions in ECS task role

**Added**:
- `JWT_SECRET_KEY` environment variable for ECS

**Environment Variables (ECS)**:
```terraform
container_environment = [
  {
    name  = "S3_BUCKET_NAME"
    value = module.s3.bucket_name
  },
  {
    name  = "JWT_SECRET_KEY"
    value = var.jwt_secret_key  # Change in production!
  }
]
```

### Backend Dependencies

**Removed** from `pyproject.toml`:
- `passlib[bcrypt]` (replaced with direct bcrypt)
- `python-jose[cryptography]` (redundant, using PyJWT)

**Added**:
- `bcrypt>=4.0.0` (for password hashing)
- `loguru>=0.7.3` (better logging)

### Frontend Dependencies

**Removed** from `package.json`:
- `aws-amplify`
- `@aws-amplify/ui-react`

## API Endpoints

### Authentication Endpoints

**POST `/api/auth/login`**
```json
// Request
{
  "email": "ta1@gatech.edu",
  "password": "your-password"
}

// Response
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbG...",
  "token_type": "bearer",
  "user": {
    "email": "ta1@gatech.edu",
    "name": "John Smith",
    "role": "ta"
  }
}
```

**POST `/api/auth/logout`**
```
Headers: Authorization: Bearer <token>

Response: {"message": "Logged out successfully"}
```

**GET `/api/auth/me`**
```
Headers: Authorization: Bearer <token>

Response:
{
  "email": "ta1@gatech.edu",
  "name": "John Smith",
  "role": "ta"
}
```

### Protected Endpoints

All existing Canvas API endpoints now use JWT authentication instead of Cognito:
- `/api/canvas/courses`
- `/api/canvas/assignments/{course_id}`
- `/api/dashboard/submission-status/{course_id}`
- etc.

## Migration Steps

### 1. Deploy New Infrastructure

```bash
# Update Terraform (removes Cognito)
cd terraform/
terraform init
terraform plan -var="ecr_repository_url=YOUR_ECR_URL" -var="jwt_secret_key=CHANGE_ME"
terraform apply

# Deploy backend with new auth
./deploy-infrastructure.sh
```

### 2. Create Initial Users

```bash
# Set S3 bucket name
export S3_BUCKET_NAME=canvas-ta-dashboard-data-prod

# Add your TAs
python scripts/manage_users.py add ta1@gatech.edu "TA One"
python scripts/manage_users.py add ta2@gatech.edu "TA Two"
python scripts/manage_users.py add admin@gatech.edu "Admin User" --role admin

# Verify users were created
python scripts/manage_users.py list
```

### 3. Deploy Frontend

```bash
# Install dependencies (removes Amplify)
cd canvas-react/
npm install

# Build frontend
npm run build

# Test locally
npm run dev
# Navigate to http://localhost:5173
# Login with created credentials
```

### 4. Update Environment Variables

**Frontend (`.env.production`):**
```bash
VITE_API_ENDPOINT=https://your-alb-endpoint.us-east-1.elb.amazonaws.com
```

**Backend (Terraform/ECS):**
- `S3_BUCKET_NAME` - Already configured
- `JWT_SECRET_KEY` - **CHANGE FROM DEFAULT IN PRODUCTION!**

### 5. Security Checklist

- [ ] Change `JWT_SECRET_KEY` from default value
- [ ] Verify S3 bucket encryption is enabled
- [ ] Confirm HTTPS is enabled on ALB
- [ ] Test login with created user
- [ ] Verify protected endpoints require authentication
- [ ] Test logout functionality
- [ ] Verify token expiration works (7 days)

## JWT Secret Key Management

**⚠️ CRITICAL**: Change the JWT secret key in production!

### Option 1: Terraform Variable (Simple)

```bash
terraform apply -var="jwt_secret_key=$(openssl rand -base64 32)"
```

### Option 2: AWS Secrets Manager (Recommended for Production)

1. Create secret:
```bash
aws secretsmanager create-secret \
  --name canvas-ta-dashboard-jwt-secret-prod \
  --secret-string "$(openssl rand -base64 32)"
```

2. Update ECS task definition to fetch from Secrets Manager
3. Grant ECS task role permission to read secret

### Option 3: Environment Variable

Set in GitHub Actions secrets for automated deployment.

## Troubleshooting

### Login Fails: "Invalid email or password"

**Causes**:
1. User doesn't exist in S3
2. Password incorrect
3. S3 bucket not accessible

**Solutions**:
```bash
# Verify user exists
python scripts/manage_users.py list

# Re-add user with new password
python scripts/manage_users.py remove ta1@gatech.edu
python scripts/manage_users.py add ta1@gatech.edu "John Smith"

# Check S3 access
aws s3 ls s3://YOUR_BUCKET/auth/
```

### Token Expired

**Symptoms**: API returns 401 after successful login

**Solution**:
- Tokens expire after 7 days
- User needs to log in again
- Frontend will auto-redirect to login

### Users File Not Found

**Symptoms**: Backend logs "Users file not found in S3"

**Solution**:
```bash
# Initialize empty users file
python scripts/manage_users.py list  # Creates empty file if not exists

# Or manually create
echo '{"users": []}' | aws s3 cp - s3://YOUR_BUCKET/auth/users.json \
  --server-side-encryption AES256
```

### Frontend Shows Login Loop

**Causes**:
1. CORS not configured correctly
2. API endpoint wrong
3. Token not being stored

**Solutions**:
1. Check browser console for CORS errors
2. Verify `VITE_API_ENDPOINT` in `.env`
3. Check browser localStorage for `access_token`

## Security Best Practices

### Password Management

✅ **DO**:
- Use strong passwords (8+ characters, mixed case, numbers)
- Change default JWT secret key
- Rotate passwords periodically
- Use password manager for TAs

❌ **DON'T**:
- Share passwords via email/Slack
- Use same password across services
- Store passwords in plaintext anywhere
- Commit users.json to git

### Token Management

✅ **DO**:
- Set reasonable expiration (7 days default)
- Clear tokens on logout
- Validate tokens on every request

❌ **DON'T**:
- Set very long expiration (>30 days)
- Share JWT tokens
- Store tokens in cookies without httpOnly

### S3 Security

✅ **DO**:
- Enable encryption at rest (AES256)
- Use IAM roles for ECS tasks
- Limit S3 access to specific paths

❌ **DON'T**:
- Make bucket public
- Use overly permissive IAM policies
- Store backups of users.json in public locations

## Testing

### Unit Tests

```bash
# Backend tests
uv run pytest tests/test_auth.py

# Test user management
python scripts/manage_users.py list
```

### Integration Tests

```bash
# Test login endpoint
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ta1@gatech.edu","password":"test123"}'

# Test protected endpoint
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Frontend Tests

```bash
# Start frontend
npm run dev

# Test login
# 1. Navigate to http://localhost:5173
# 2. Enter credentials
# 3. Verify redirect to dashboard
# 4. Check browser localStorage for token
# 5. Test logout
```

## Cost Comparison

### Before (Cognito)

- Cognito User Pool: $0-50/month (depending on users)
- Secrets Manager: $0.40/month per secret
- **Total**: ~$10-50/month

### After (Simple JWT)

- S3 storage: $0.023/GB (users.json is <1KB = ~$0.00)
- S3 requests: $0.0004 per 1000 (negligible)
- **Total**: ~$0/month

**Savings**: ~$120-600/year

## Maintenance

### Adding New Users

```bash
# Regular workflow
python scripts/manage_users.py add newta@gatech.edu "New TA"
```

### Password Reset

```bash
# Remove and re-add with new password
python scripts/manage_users.py remove ta1@gatech.edu
python scripts/manage_users.py add ta1@gatech.edu "John Smith"
# User will need to use new password
```

### Backup Users

```bash
# Download from S3
aws s3 cp s3://YOUR_BUCKET/auth/users.json ./users_backup.json

# Restore if needed
aws s3 cp ./users_backup.json s3://YOUR_BUCKET/auth/users.json \
  --server-side-encryption AES256
```

**⚠️ IMPORTANT**: Store backups securely! They contain password hashes.

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review backend logs: `aws logs tail /ecs/canvas-ta-dashboard-task-prod --follow`
3. Check ECS task health: `aws ecs describe-services --cluster CLUSTER --services SERVICE`

## Additional Resources

- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
- [Bcrypt Password Hashing](https://en.wikipedia.org/wiki/Bcrypt)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
