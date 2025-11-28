# Authentication System Documentation

## Overview

The Canvas TA Dashboard uses a simple, secure, and serverless authentication system based on JWT (JSON Web Tokens) and S3. This system eliminates the need for complex identity providers like Cognito while maintaining security and low cost.

## Architecture

### Backend (`auth.py`)

**User Storage**:
- **Location**: `s3://YOUR_BUCKET/auth/users.json`
- **Format**: JSON file containing user records
- **Security**:
    - Passwords are hashed using **bcrypt** (cost factor 12)
    - File is encrypted at rest (S3 Server-Side Encryption)
    - Access is restricted via IAM roles

**Authentication Flow**:
1. **Login**: User submits email + password to `/api/auth/login`.
2. **Verification**: Backend downloads `users.json` from S3 and verifies the password hash.
3. **Token Issue**: If valid, a JWT access token is generated (default expiration: 7 days).
4. **Storage**: Frontend stores the JWT in `localStorage`.
5. **Access**: All subsequent API requests include the JWT in the `Authorization: Bearer <token>` header.

### Frontend (`SimpleAuthWrapper.jsx`)

- **Login UI**: A clean, dependency-free login form.
- **State**: Manages authentication state using React Context.
- **Persistence**: Automatically restores session from `localStorage` on refresh.

## User Management

Users are managed via the CLI script `scripts/manage_users.py`. This script interacts directly with the S3 bucket to safely modify the `users.json` file.

### Prerequisites

- Python 3.11+
- AWS Credentials configured
- `S3_BUCKET_NAME` environment variable set (or passed as argument)

### Commands

**1. Add a User**
```bash
# Interactive password prompt
python scripts/manage_users.py add ta1@gatech.edu "John Smith"

# Specify role (default is 'ta')
python scripts/manage_users.py add admin@gatech.edu "Admin User" --role admin
```

**2. List Users**
```bash
python scripts/manage_users.py list
```

**3. Remove a User**
```bash
python scripts/manage_users.py remove ta1@gatech.edu
```

**4. Change Password**
To change a password, simply remove the user and add them again with the new password.

## Security Configuration

### Environment Variables

The following environment variables are required for the backend (Lambda):

| Variable | Description |
|----------|-------------|
| `S3_BUCKET_NAME` | Name of the S3 bucket storing `auth/users.json` |
| `JWT_SECRET_KEY` | **CRITICAL**: Secret key for signing JWTs. Must be changed in production. |

### Production Security Checklist

1.  **JWT Secret**: Ensure `JWT_SECRET_KEY` is set to a long, random string in the Lambda configuration. **NEVER** use the default development secret in production.
2.  **S3 Encryption**: Ensure the S3 bucket has Server-Side Encryption (SSE) enabled.
3.  **HTTPS**: Ensure API Gateway and CloudFront are serving traffic over HTTPS.

## API Endpoints

### Public
- `POST /api/auth/login`: Authenticate and receive a token.

### Protected (Requires Bearer Token)
- `GET /api/auth/me`: Get current user details.
- `POST /api/auth/logout`: Logout (client-side clearing).
- All `/api/canvas/*` endpoints.

## Troubleshooting

**"Invalid email or password"**
- Verify the user exists using `python scripts/manage_users.py list`.
- Check if the S3 bucket name is correctly configured.

**"Token has expired"**
- JWT tokens expire after 7 days. The user must log in again.

**"Users file not found"**
- The system will automatically create an empty `users.json` if one doesn't exist. Run `list` to trigger this creation.
