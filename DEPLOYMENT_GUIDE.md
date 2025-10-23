# Multi-Tenant Canvas TA Dashboard - Deployment Guide

This guide walks you through deploying the complete multi-tenant Canvas TA Dashboard system to AWS.

## 🏗️ Architecture Overview

The system now includes:
- **AWS Cognito**: User authentication and registration
- **DynamoDB**: User profiles and course associations
- **S3**: Cached Canvas data storage
- **Lambda**: Scheduled Canvas data fetching
- **AppRunner**: FastAPI backend hosting
- **Cloudflare/CDN**: React frontend hosting

## 📋 Prerequisites

1. **AWS CLI** configured with admin permissions
2. **Docker** installed for container builds
3. **Node.js 18+** for React frontend builds
4. **Python 3.11+** for backend development

## 🚀 Step 1: Deploy Infrastructure

The infrastructure has been successfully deployed! Here are the key resources:

### AWS Resources Created
```bash
# Cognito Authentication
COGNITO_USER_POOL_ID=us-east-1_moQU5rUSO
COGNITO_USER_POOL_CLIENT_ID=72pg3ce5vm6rgoa51cb9tpgj0c

# DynamoDB Tables
USERS_TABLE=canvas-ta-users-dev
USER_COURSES_TABLE=canvas-ta-user-courses-dev
CACHE_METADATA_TABLE=canvas-ta-course-cache-dev

# S3 Storage
COURSE_DATA_BUCKET=canvas-ta-course-data-dev-741783034843

# Lambda Function
LAMBDA_FUNCTION=canvas-ta-data-fetcher-dev (runs every 15 minutes)

# IAM Roles
APPRUNNER_INSTANCE_ROLE=arn:aws:iam::741783034843:role/canvas-ta-apprunner-instance-role-dev
```

### Environment Files Created
- `backend-canvas-fastapi/.env.dev` - Backend configuration
- `canvas-react/.env.dev` - Frontend configuration

## 🔧 Step 2: Update Backend Deployment

### 2.1 Docker Build with New Dependencies

The backend now includes authentication dependencies. Update your Dockerfile to install the new packages:

```dockerfile
# In your Dockerfile, ensure these packages are installed:
RUN pip install boto3>=1.28.0 PyJWT>=2.8.0 passlib[bcrypt]>=1.7.4 python-jose[cryptography]>=3.3.0 email-validator>=2.0.0
```

### 2.2 AppRunner Configuration

Update your AppRunner service with the new environment variables:

```json
{
  "Version": 1,
  "Runtime": "PYTHON_3_11",
  "Environment": {
    "ENVIRONMENT": "dev",
    "USERS_TABLE": "canvas-ta-users-dev",
    "USER_COURSES_TABLE": "canvas-ta-user-courses-dev",
    "CACHE_METADATA_TABLE": "canvas-ta-course-cache-dev",
    "COURSE_DATA_BUCKET": "canvas-ta-course-data-dev-741783034843",
    "CANVAS_TOKENS_SECRET": "arn:aws:secretsmanager:us-east-1:741783034843:secret:canvas-ta-tokens-dev-AP99vM",
    "COGNITO_USER_POOL_ID": "us-east-1_moQU5rUSO",
    "COGNITO_USER_POOL_CLIENT_ID": "72pg3ce5vm6rgoa51cb9tpgj0c",
    "JWT_SECRET": "your-production-jwt-secret-here"
  },
  "Build": {
    "Commands": {
      "Build": [
        "pip install -r requirements.txt"
      ]
    }
  },
  "Run": {
    "Runtime": "python3",
    "Command": "uvicorn main:app --host 0.0.0.0 --port 8000",
    "Network": {
      "Port": 8000,
      "Env": "PORT"
    }
  }
}
```

### 2.3 IAM Role Update

Update your AppRunner service to use the new IAM role:

```bash
aws apprunner update-service \\
  --service-arn "arn:aws:apprunner:us-east-1:741783034843:service/cda-ta-dashboard/179efa27ed024f89a3a8d7a200b2ef50" \\
  --source-configuration '{
    "ImageRepository": {
      "ImageConfiguration": {
        "RuntimeEnvironmentVariables": {
          // ... environment variables from above
        }
      }
    }
  }' \\
  --instance-configuration '{
    "InstanceRoleArn": "arn:aws:iam::741783034843:role/canvas-ta-apprunner-instance-role-dev"
  }'
```

## 🎨 Step 3: Update Frontend Deployment

### 3.1 Install New Dependencies

```bash
cd canvas-react
npm install aws-amplify @aws-amplify/ui-react
```

### 3.2 Build with Environment Variables

Create production `.env` file:
```bash
# canvas-react/.env.production
VITE_COGNITO_USER_POOL_ID=us-east-1_moQU5rUSO
VITE_COGNITO_USER_POOL_CLIENT_ID=72pg3ce5vm6rgoa51cb9tpgj0c
VITE_BACKEND_URL=https://your-apprunner-domain.com
```

Build for production:
```bash
npm run build
```

### 3.3 Deploy to CDN

Deploy the `dist/` folder to your CDN/static hosting service.

## 🧪 Step 4: Test Multi-Tenant Flow

### 4.1 User Registration Flow
1. **Visit Frontend** → User sees Cognito login form
2. **Sign Up** → User creates account with email/password
3. **Email Verification** → User receives verification code
4. **Login** → User accesses dashboard

### 4.2 Course Access Flow
1. **Add Course** → User enters Canvas URL, API token, course ID
2. **Token Storage** → Encrypted token stored in DynamoDB
3. **Data Fetching** → Lambda fetches course data every 15 minutes
4. **Shared Access** → All users of same course see cached data

### 4.3 Dashboard Features
- **Assignment Tracking**: Real-time grading status
- **TA Management**: Workload distribution
- **Late Days**: Student penalty tracking
- **Peer Reviews**: Collaboration monitoring

## 🔐 Step 5: Security Checklist

### 5.1 Production Security
- [ ] **JWT Secret**: Generate secure random secret for production
- [ ] **CORS**: Restrict to specific domains (not "*")
- [ ] **API Tokens**: Verify encryption at rest in DynamoDB
- [ ] **HTTPS**: Enforce SSL/TLS for all endpoints
- [ ] **Secrets**: Never commit credentials to version control

### 5.2 FERPA Compliance
- [ ] **Data TTL**: Verify 90-day automatic cleanup
- [ ] **Access Control**: Only enrolled users can access course data
- [ ] **Audit Logging**: Enable CloudTrail for compliance
- [ ] **Regional Storage**: Confirm US-only data residency

## 🚨 Troubleshooting

### Common Issues

**1. Lambda Function Fails**
```bash
# Check Lambda logs
aws logs tail /aws/lambda/canvas-ta-data-fetcher-dev --follow

# Common fixes:
# - Verify Canvas API tokens in Secrets Manager
# - Check DynamoDB permissions
# - Validate S3 bucket access
```

**2. AppRunner Authentication Errors**
```bash
# Verify IAM role permissions
aws iam get-role --role-name canvas-ta-apprunner-instance-role-dev

# Check environment variables
aws apprunner describe-service --service-arn "your-service-arn"
```

**3. Cognito Login Issues**
```bash
# Verify User Pool configuration
aws cognito-idp describe-user-pool --user-pool-id us-east-1_moQU5rUSO

# Check callback URLs and CORS settings
```

### Health Checks

```bash
# Test Lambda function
aws lambda invoke --function-name canvas-ta-data-fetcher-dev --payload '{"source":"health-check"}' output.json

# Test backend API
curl -X GET https://your-apprunner-domain.com/api/health

# Check DynamoDB tables
aws dynamodb describe-table --table-name canvas-ta-users-dev
```

## 📊 Monitoring

### CloudWatch Metrics
- **Lambda**: Success/failure rates, execution duration
- **DynamoDB**: Read/write capacity, throttling
- **S3**: Object count, storage size
- **AppRunner**: CPU, memory, request count

### Cost Monitoring
- **Estimated Monthly Cost**: $15-25 for dev environment
- **Production Scaling**: Costs scale with user count and courses
- **Optimization**: S3 Intelligent Tiering, DynamoDB on-demand

## 🔄 Maintenance

### Regular Tasks
1. **Monitor CloudWatch** for errors and performance
2. **Review DynamoDB** usage and optimize queries
3. **Update dependencies** for security patches
4. **Canvas API changes** - monitor for deprecations
5. **User feedback** and feature requests

### Emergency Procedures
1. **Lambda failures** → Check Canvas API status
2. **DynamoDB throttling** → Enable auto-scaling
3. **S3 access issues** → Verify IAM permissions
4. **Authentication problems** → Check Cognito configuration

---

## 🎉 Deployment Complete!

Your multi-tenant Canvas TA Dashboard is now ready for production use. Users can:

✅ **Register and login** with Cognito authentication
✅ **Add multiple courses** with secure API token storage
✅ **Share cached data** across users of the same course
✅ **Access real-time dashboards** with sub-second load times
✅ **Track TA workloads** and assignment progress
✅ **Monitor student late days** and peer reviews

The system automatically optimizes costs by sharing course data and provides FERPA-compliant data management with 90-day TTL.