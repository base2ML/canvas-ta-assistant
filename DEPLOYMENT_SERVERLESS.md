# Canvas TA Assistant - Serverless Deployment Guide

Complete guide for deploying the Canvas TA Assistant application to AWS using a lightweight, affordable serverless microservices architecture.

## Table of Contents
- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Architecture Overview](#architecture-overview)
- [One-Command Deployment](#one-command-deployment)
- [Manual Deployment Steps](#manual-deployment-steps)
- [Configuration](#configuration)
- [CI/CD with GitHub Actions](#cicd-with-github-actions)
- [Post-Deployment](#post-deployment)
- [Monitoring & Operations](#monitoring--operations)
- [Cost Management](#cost-management)
- [Troubleshooting](#troubleshooting)
- [Rollback Procedures](#rollback-procedures)

## Quick Start

**Deploy everything to AWS in one command:**

```bash
# Set Canvas API token
export CANVAS_API_TOKEN="your-canvas-api-token"

# Run deployment script
./deploy-serverless.sh dev
```

That's it! The script will:
1. ✅ Check prerequisites
2. ✅ Setup Terraform backend
3. ✅ Build React frontend
4. ✅ Package Lambda functions
5. ✅ Deploy infrastructure
6. ✅ Deploy frontend to S3/CloudFront
7. ✅ Deploy backend to Lambda
8. ✅ Run smoke tests
9. ✅ Display deployment summary

## Prerequisites

### Required Tools
- **AWS CLI** v2.x - [Install](https://aws.amazon.com/cli/)
- **Terraform** v1.6+ - [Install](https://www.terraform.io/downloads)
- **Node.js** v20+ - [Install](https://nodejs.org/)
- **Python** 3.11+ - [Install](https://www.python.org/)
- **uv** (Python package manager) - Auto-installed by script

### AWS Account Setup

1. **Create AWS Account** (if you don't have one)
   - Sign up at https://aws.amazon.com/

2. **Configure AWS Credentials**
   ```bash
   aws configure
   # Enter:
   # - AWS Access Key ID
   # - AWS Secret Access Key
   # - Default region: us-east-1
   # - Default output format: json
   ```

3. **Verify AWS Access**
   ```bash
   aws sts get-caller-identity
   ```

### Canvas API Token

1. Log into Canvas LMS
2. Navigate to **Account → Settings → Approved Integrations**
3. Click **+ New Access Token**
4. Set purpose: "TA Dashboard API Access"
5. Copy the generated token (save securely!)

## Architecture Overview

### Serverless Components

```
GitHub Repo → GitHub Actions → AWS
                                 ├─ CloudFront (Frontend CDN)
                                 ├─ S3 (Static Assets + Canvas Data)
                                 ├─ API Gateway (REST API)
                                 ├─ Lambda (API Handler + Canvas Sync)
                                 ├─ DynamoDB (Sessions, Cache, TA Assignments)
                                 ├─ Cognito (Authentication)
                                 ├─ EventBridge (Scheduled Canvas Sync)
                                 └─ CloudWatch (Monitoring & Logs)
```

### Cost-Optimized Design
- **No always-on servers** - Pay only for actual usage
- **Serverless scaling** - Automatically handles traffic spikes
- **Free tier eligible** - Many services have generous free tiers
- **Estimated cost**: $30-50/month for low traffic

## One-Command Deployment

### Development Environment
```bash
export CANVAS_API_TOKEN="your-token-here"
./deploy-serverless.sh dev
```

### Production Environment
```bash
export CANVAS_API_TOKEN="your-token-here"
./deploy-serverless.sh prod
```

### What the Script Does

1. **Prerequisites Check** ✓
   - Verifies AWS CLI, Terraform, Node.js, Python installed
   - Checks AWS credentials configured
   - Installs uv package manager if needed

2. **Terraform Backend Setup** ✓
   - Creates S3 bucket for state storage
   - Creates DynamoDB table for state locking
   - Enables versioning and encryption

3. **Frontend Build** ✓
   - Installs npm dependencies
   - Runs ESLint linting
   - Creates production build (Vite)

4. **Lambda Packaging** ✓
   - Packages API handler with dependencies
   - Packages Canvas sync function with dependencies
   - Creates deployment zip files

5. **Infrastructure Deployment** ✓
   - Initializes Terraform
   - Plans infrastructure changes
   - Applies approved changes
   - Saves outputs for next steps

6. **Frontend Deployment** ✓
   - Updates configuration with API endpoints
   - Uploads to S3 with optimal caching
   - Invalidates CloudFront cache

7. **Backend Deployment** ✓
   - Updates Lambda function code
   - Publishes new versions
   - Waits for deployment to complete

8. **Smoke Tests** ✓
   - Tests health endpoint
   - Tests API configuration endpoint
   - Measures API response time

9. **Deployment Summary** ✓
   - Displays website URL
   - Shows API endpoints
   - Provides monitoring links

## Manual Deployment Steps

If you prefer step-by-step manual deployment:

### Step 1: Setup Terraform Backend
```bash
# Create S3 bucket for Terraform state
aws s3api create-bucket \
  --bucket canvas-ta-terraform-state \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket canvas-ta-terraform-state \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket canvas-ta-terraform-state \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name canvas-ta-terraform-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### Step 2: Configure Environment
```bash
# Edit environment variables
cd terraform-serverless/environments
cp dev.tfvars my-config.tfvars
vim my-config.tfvars

# Update:
# - canvas_course_id
# - alarm_email
# - cors_allowed_origins (add your domains)
```

### Step 3: Deploy Infrastructure
```bash
cd terraform-serverless

# Initialize Terraform
terraform init

# Plan changes
terraform plan \
  -var-file="environments/dev.tfvars" \
  -var="canvas_api_token=${CANVAS_API_TOKEN}" \
  -out=tfplan

# Apply changes
terraform apply tfplan

# Save outputs
terraform output -json > ../outputs.json
```

### Step 4: Build & Deploy Frontend
```bash
cd canvas-react

# Install dependencies
npm ci

# Build production bundle
npm run build

# Get S3 bucket name from Terraform output
S3_BUCKET=$(cat ../outputs.json | jq -r '.frontend_bucket_name.value')

# Upload to S3
aws s3 sync dist/ "s3://${S3_BUCKET}/" --delete

# Get CloudFront distribution ID
CF_ID=$(cat ../outputs.json | jq -r '.cloudfront_distribution_id.value')

# Invalidate cache
aws cloudfront create-invalidation --distribution-id ${CF_ID} --paths "/*"
```

### Step 5: Deploy Backend Lambda Functions
```bash
# Package API handler
mkdir -p lambda-packages/api-handler
cp main.py lambda-packages/api-handler/
uv pip install --target lambda-packages/api-handler -r pyproject.toml
cd lambda-packages/api-handler && zip -r ../../api-handler.zip . && cd ../..

# Get Lambda function name
API_FUNCTION=$(cat outputs.json | jq -r '.api_lambda_function_name.value')

# Update Lambda code
aws lambda update-function-code \
  --function-name ${API_FUNCTION} \
  --zip-file fileb://api-handler.zip

# Publish version
aws lambda publish-version --function-name ${API_FUNCTION}
```

### Step 6: Verify Deployment
```bash
# Get API URL
API_URL=$(cat outputs.json | jq -r '.api_gateway_url.value')

# Test health endpoint
curl ${API_URL}/health

# Test config endpoint
curl ${API_URL}/api/config
```

## Configuration

### Environment Variables

**Development (`terraform-serverless/environments/dev.tfvars`)**:
```hcl
environment          = "dev"
aws_region           = "us-east-1"
canvas_course_id     = "123456"
alarm_email          = "dev-team@example.com"
monthly_budget_limit = 50
log_retention_days   = 7
```

**Production (`terraform-serverless/environments/prod.tfvars`)**:
```hcl
environment             = "prod"
aws_region              = "us-east-1"
canvas_course_id        = "123456"
alarm_email             = "ops-team@example.com"
monthly_budget_limit    = 100
log_retention_days      = 30
enable_deletion_protection = true
```

### Canvas Configuration

Required variables in `.tfvars`:
- `canvas_api_url` - Canvas LMS base URL
- `canvas_course_id` - Course ID to sync data from
- `canvas_api_token` - API token (via environment variable)

### CORS Configuration

Update `cors_allowed_origins` in `.tfvars`:
```hcl
cors_allowed_origins = [
  "https://your-production-domain.com",
  "https://d111111abcdef8.cloudfront.net"  # CloudFront domain
]
```

## CI/CD with GitHub Actions

### Setup GitHub Secrets

1. Navigate to **Settings → Secrets and variables → Actions**
2. Add the following secrets:

| Secret Name | Description |
|------------|-------------|
| `AWS_ACCESS_KEY_ID` | AWS access key for deployment |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key for deployment |
| `CANVAS_API_TOKEN` | Canvas API token |

### Automated Deployment Workflow

**Trigger**: Push to `main` or `develop` branch

**Workflow**:
1. Build & test frontend
2. Build & test backend
3. Security scanning
4. Terraform plan
5. Deploy infrastructure (with approval)
6. Deploy frontend to S3/CloudFront
7. Deploy backend to Lambda
8. Run validation tests
9. Send notifications

**Manual Deployment**:
```bash
# Trigger workflow manually via GitHub UI
# Actions → Deploy Serverless Architecture → Run workflow
```

### Branch Strategy

- `main` → Production environment (requires approval)
- `develop` → Development environment (auto-deploy)
- `feature/*` → Preview deployments (manual trigger)

## Post-Deployment

### Create Cognito Users

```bash
# Get User Pool ID
USER_POOL_ID=$(cd terraform-serverless && terraform output -raw cognito_user_pool_id)

# Create admin user
aws cognito-idp admin-create-user \
  --user-pool-id ${USER_POOL_ID} \
  --username admin@example.com \
  --user-attributes Name=email,Value=admin@example.com Name=email_verified,Value=true \
  --temporary-password "TempPass123!" \
  --message-action SUPPRESS

# User will need to change password on first login
```

### Configure Canvas Course

1. Update `canvas_course_id` in Terraform variables
2. Re-run deployment to apply changes
3. Lambda function will sync data every 15 minutes

### Test Canvas Data Sync

```bash
# Get Lambda function name
SYNC_FUNCTION=$(cd terraform-serverless && terraform output -raw sync_lambda_function_name)

# Manually invoke sync function
aws lambda invoke \
  --function-name ${SYNC_FUNCTION} \
  --payload '{}' \
  response.json

# Check logs
aws logs tail /aws/lambda/${SYNC_FUNCTION} --follow
```

## Monitoring & Operations

### CloudWatch Dashboard

Access the pre-configured dashboard:
```bash
# Get dashboard URL
cd terraform-serverless && terraform output -raw cloudwatch_dashboard_url
```

**Metrics Displayed**:
- API Gateway: Request count, latency, errors
- Lambda: Invocations, duration, errors, cold starts
- S3: Storage size, request count
- DynamoDB: Read/write capacity, throttling
- Cost: Daily spend by service

### View Logs

```bash
# API Lambda logs
aws logs tail /aws/lambda/canvas-ta-dashboard-dev-api-handler --follow

# Canvas sync Lambda logs
aws logs tail /aws/lambda/canvas-ta-dashboard-dev-canvas-sync --follow

# API Gateway access logs
aws logs tail /aws/apigateway/canvas-ta-dashboard-dev-api --follow
```

### CloudWatch Alarms

Pre-configured alarms:
- 🚨 **Critical**: API 5xx errors > 5% (5 min window)
- ⚠️ **Warning**: Lambda duration > 25s (approaching timeout)
- 📊 **Info**: Data sync failures (retry exhausted)
- 💰 **Budget**: Monthly spend > $80 (80% of budget)

### Performance Metrics

**Target SLAs**:
- API P95 latency: < 500ms
- Frontend load time: < 2s
- Data sync success rate: > 99.5%
- API uptime: > 99.9%

**Check Current Performance**:
```bash
# API response time
time curl -s https://your-api-url.com/health

# Lambda metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=canvas-ta-dashboard-dev-api-handler \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum
```

## Cost Management

### Monthly Cost Estimate

**Development Environment** (~$30-50/month):
| Service | Configuration | Cost |
|---------|--------------|------|
| CloudFront | 100 GB transfer | $8.50 |
| S3 | 10 GB storage | $2.00 |
| API Gateway | 1M requests | $3.50 |
| Lambda | 2M requests, mixed duration | $9.00 |
| DynamoDB | 5 GB, on-demand | $3.00 |
| Cognito | <50K MAU | $0.00 |
| Other | Logs, metrics, secrets | $5.00 |
| **Total** | | **~$31/month** |

**Production Environment** (~$80-120/month with 10K users)

### Cost Optimization Tips

1. **Lambda Memory Tuning**
   ```bash
   # Monitor current usage
   aws lambda get-function \
     --function-name canvas-ta-dashboard-dev-api-handler \
     --query 'Configuration.MemorySize'

   # Adjust based on actual memory usage (CloudWatch logs show max used)
   ```

2. **S3 Lifecycle Policies**
   - Already configured: 30d → Standard-IA → 90d → Glacier → 365d delete
   - Review and adjust based on data access patterns

3. **CloudFront Caching**
   - Increase TTL for static assets (already optimized)
   - Use custom domain with longer DNS TTL

4. **DynamoDB Optimization**
   - Review on-demand pricing vs provisioned capacity after 30 days
   - Consider reserved capacity for stable workloads

5. **Lambda Concurrency Limits**
   - Set reserved concurrency to prevent runaway costs
   - Current limit: 10 concurrent executions per function

### Cost Monitoring

```bash
# View current month-to-date costs
aws ce get-cost-and-usage \
  --time-period Start=$(date -u -d 'month ago' +%Y-%m-%d),End=$(date -u +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE

# Set up billing alarms (already configured via Terraform)
```

### Budget Alerts

Budget alarms trigger at:
- 50% of monthly limit (email notification)
- 80% of monthly limit (email notification)
- 100% of monthly limit (email notification + SNS topic)

## Troubleshooting

### Common Issues

#### 1. Terraform Backend Error
```
Error: Failed to get existing workspaces: S3 bucket does not exist
```

**Solution**:
```bash
# Create backend resources
./scripts/setup-terraform-backend.sh

# Or manually:
aws s3 mb s3://canvas-ta-terraform-state --region us-east-1
aws dynamodb create-table --table-name canvas-ta-terraform-lock ...
```

#### 2. Lambda Cold Start Issues
```
API response time > 3s on first request
```

**Solution**:
```bash
# Enable provisioned concurrency (adds cost)
aws lambda put-provisioned-concurrency-config \
  --function-name canvas-ta-dashboard-prod-api-handler \
  --qualifier '$LATEST' \
  --provisioned-concurrent-executions 2
```

#### 3. CORS Errors in Frontend
```
Access to fetch at 'https://api...' from origin 'https://...' has been blocked by CORS policy
```

**Solution**:
```bash
# Update CORS configuration in terraform-serverless/environments/prod.tfvars
cors_allowed_origins = [
  "https://your-cloudfront-domain.cloudfront.net",
  "https://your-custom-domain.com"
]

# Re-deploy
terraform apply
```

#### 4. Canvas Sync Failures
```
Lambda function timing out after 15 minutes
```

**Solution**:
```bash
# Check logs for specific error
aws logs tail /aws/lambda/canvas-ta-dashboard-dev-canvas-sync --since 1h

# Increase memory (improves CPU performance)
aws lambda update-function-configuration \
  --function-name canvas-ta-dashboard-dev-canvas-sync \
  --memory-size 2048

# Or adjust timeout (max 15min for Lambda)
```

#### 5. Frontend 404 Errors
```
CloudFront returns 404 for all routes except /
```

**Solution**:
```bash
# Update CloudFront error pages to return index.html for 404
# This is configured in terraform-serverless/modules/frontend/main.tf
# Verify custom_error_response is present
```

### Debug Commands

```bash
# Check Lambda logs
aws logs tail /aws/lambda/<function-name> --follow

# Check API Gateway logs
aws logs tail /aws/apigateway/<api-name> --follow

# Test Lambda function locally
aws lambda invoke \
  --function-name <function-name> \
  --payload '{}' \
  response.json

# Check S3 bucket contents
aws s3 ls s3://<bucket-name>/ --recursive

# Check CloudFront cache behavior
aws cloudfront get-distribution --id <distribution-id>

# Validate Cognito configuration
aws cognito-idp describe-user-pool --user-pool-id <pool-id>
```

## Rollback Procedures

### Frontend Rollback

```bash
# List S3 object versions
aws s3api list-object-versions \
  --bucket canvas-ta-dashboard-dev-frontend \
  --prefix index.html

# Restore previous version
aws s3api copy-object \
  --bucket canvas-ta-dashboard-dev-frontend \
  --copy-source canvas-ta-dashboard-dev-frontend/index.html?versionId=<version-id> \
  --key index.html

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id <distribution-id> \
  --paths "/*"
```

### Backend (Lambda) Rollback

```bash
# List Lambda versions
aws lambda list-versions-by-function \
  --function-name canvas-ta-dashboard-dev-api-handler

# Update alias to previous version
aws lambda update-alias \
  --function-name canvas-ta-dashboard-dev-api-handler \
  --name production \
  --function-version <previous-version>
```

### Infrastructure Rollback

```bash
# Rollback Terraform changes
cd terraform-serverless

# View state history
terraform state list

# Rollback to previous state
terraform apply -var-file="environments/dev.tfvars" <previous-plan>

# Or destroy and re-apply
terraform destroy -var-file="environments/dev.tfvars"
terraform apply -var-file="environments/dev.tfvars"
```

### Full System Rollback

```bash
# Checkout previous Git commit
git log --oneline
git checkout <previous-commit-hash>

# Re-run deployment
./deploy-serverless.sh dev
```

## Security Best Practices

### 1. Secrets Management
- ✅ Canvas API token stored in AWS Secrets Manager
- ✅ Never commit `.env` files or tokens to Git
- ✅ Use environment variables for sensitive data
- ✅ Rotate API tokens quarterly

### 2. Network Security
- ✅ API Gateway with AWS WAF (production)
- ✅ CloudFront with HTTPS only
- ✅ Lambda functions in private subnets (optional)
- ✅ S3 bucket policies restrict public access

### 3. Authentication & Authorization
- ✅ Cognito JWT token validation
- ✅ API Gateway authorizer integration
- ✅ MFA enabled for production users
- ✅ Password policies enforced

### 4. Data Protection
- ✅ S3 encryption at rest (AES-256)
- ✅ DynamoDB encryption at rest
- ✅ Secrets Manager encryption
- ✅ TLS 1.2+ for all data in transit

### 5. Compliance (FERPA)
- ✅ Audit logging via CloudTrail
- ✅ Data retention policies configured
- ✅ Access controls for student data
- ✅ Regular security reviews

## Support & Resources

### Documentation
- [Architecture Design](./ARCHITECTURE.md)
- [Terraform Modules](./terraform-serverless/modules/)
- [GitHub Actions Workflow](./.github/workflows/deploy-serverless.yml)

### AWS Resources
- [Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [API Gateway Quotas](https://docs.aws.amazon.com/apigateway/latest/developerguide/limits.html)
- [S3 Best Practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/best-practices.html)

### Community
- [GitHub Issues](https://github.com/base2ML/canvas-ta-assistant/issues)
- [Canvas Community](https://community.canvaslms.com/)
- [AWS re:Post](https://repost.aws/)

## Next Steps

After successful deployment:

1. ✅ **Create Cognito users** for TAs and instructors
2. ✅ **Configure Canvas course ID** in Terraform variables
3. ✅ **Test Canvas data sync** manually
4. ✅ **Setup monitoring alerts** with your email
5. ✅ **Review CloudWatch dashboard** for metrics
6. ✅ **Test frontend** with real user workflows
7. ✅ **Setup custom domain** (optional, via Route 53)
8. ✅ **Enable multi-region** (future enhancement)

## Conclusion

You now have a fully functional, serverless Canvas TA Dashboard deployed on AWS with:
- 🚀 Automated CI/CD from GitHub
- 💰 60-70% cost reduction vs ECS
- 📈 Infinite scalability with pay-per-use
- 🔒 Production-grade security
- 📊 Comprehensive monitoring

**Estimated Monthly Cost**: $30-50 for development, $80-120 for production (10K users)

For questions or issues, please open a GitHub issue or contact the development team.

---

**Last Updated**: 2025-01-21
**Version**: 1.0.0
**Maintainers**: Canvas TA Dashboard Team
