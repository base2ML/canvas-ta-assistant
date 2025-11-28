# GitHub Actions Setup Guide - Serverless Deployment

This guide explains how to configure GitHub Actions for automated serverless deployment of the Canvas TA Dashboard to AWS Lambda, API Gateway, S3, and CloudFront.

## Overview

The project uses a **fully serverless architecture** with intelligent GitHub Actions workflows that automatically deploy infrastructure and application code using Terraform and AWS Lambda:

- **Infrastructure changes** → Terraform deploys Lambda, API Gateway, S3, CloudFront, Secrets Manager
- **Backend changes** → Lambda function code updated with new deployment package
- **Frontend changes** → React app built and deployed to S3 with CloudFront invalidation
- **CI/CD checks** → Linting, testing, and code quality validation

## Architecture Components

The serverless deployment includes:

- **AWS Lambda**: Python 3.11 FastAPI application (via Mangum adapter)
- **API Gateway**: HTTP API for REST endpoints with CORS support
- **CloudFront**: Global CDN for React frontend delivery
- **S3 Buckets**:
  - Frontend static assets (React build)
  - Canvas data storage
  - Lambda deployment packages
- **Secrets Manager**: Secure storage for Canvas API tokens and JWT secrets
- **CloudWatch**: Logging and monitoring for Lambda functions

## Required GitHub Secrets

Configure these secrets in your GitHub repository settings (`Settings` → `Secrets and variables` → `Actions`):

### AWS Credentials (Required)

| Secret Name | Description | How to Get |
|-------------|-------------|------------|
| `AWS_ACCESS_KEY_ID` | AWS access key for GitHub Actions | Create IAM user with deployment permissions |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key | Created when generating access key |

### Canvas API Configuration (Optional)

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `CANVAS_API_TOKEN` | Canvas LMS API token | `1234~abcd...` |
| `CANVAS_API_URL` | Canvas instance URL | `https://gatech.instructure.com` |
| `CANVAS_COURSE_ID` | Canvas course ID | `12345` |

**Note**: Canvas secrets are optional and only used for CI tests. Production Canvas credentials are managed via AWS Secrets Manager.

### Required IAM Permissions

Create an IAM user for GitHub Actions with the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:*",
        "apigateway:*",
        "s3:*",
        "cloudfront:*",
        "secretsmanager:*",
        "iam:GetRole",
        "iam:PassRole",
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "logs:*",
        "cloudwatch:*",
        "events:*"
      ],
      "Resource": "*"
    }
  ]
}
```

**Security Best Practice**: Use least-privilege IAM policies and restrict to specific resources in production.

## Workflows Overview

### 1. Main Deployment Pipeline (`.github/workflows/deploy.yml`)

**Triggers:**
- Push to `main` branch (production deployment)
- Push to `dev-*` branches (development deployment)
- Manual workflow dispatch with environment selection

**What it does:**
1. **Deploy Infrastructure** (Terraform)
   - Creates/updates Lambda functions
   - Configures API Gateway HTTP API
   - Sets up S3 buckets and CloudFront distribution
   - Manages Secrets Manager secrets
   - Outputs infrastructure details (API endpoint, S3 bucket, CloudFront ID)

2. **Deploy Backend** (Lambda)
   - Packages Python dependencies and application code
   - Creates Lambda deployment package (zip)
   - Updates Lambda function code
   - Waits for function update to complete
   - Tests health endpoint

3. **Deploy Frontend** (S3 + CloudFront)
   - Builds React application with Vite
   - Deploys to S3 bucket
   - Invalidates CloudFront cache for immediate updates

4. **Post-Deployment Tests**
   - API health checks
   - Authentication endpoint validation
   - Frontend accessibility tests
   - CORS configuration validation
   - Login functionality tests

**Environment Detection:**
- `main` branch → `prod` environment
- `dev-*` branches → `dev` environment
- Manual trigger → choose environment

**Deployment Flow:**
```
Infrastructure (Terraform)
    ↓
    ├─→ Backend (Lambda) → Health Check
    └─→ Frontend (S3/CloudFront) → Cache Invalidation
    ↓
Post-Deployment Tests → Summary Report
```

### 2. Lambda-Only Deployment (`.github/workflows/deploy-lambda.yml`)

**Triggers:**
- Push to `main` branch with changes to:
  - `main.py`, `auth.py`, `lambda_handler.py`
  - `pyproject.toml`
  - `canvas-react/**` (frontend code)
- Manual workflow dispatch

**What it does:**
- Fast Lambda-only deployment without Terraform
- Builds React frontend
- Creates Lambda deployment package with Python dependencies
- Uploads package to S3
- Updates Lambda function code from S3
- Verifies deployment with health check

**Use Case:**
- Quick updates for application code changes
- Bypasses Terraform when infrastructure is unchanged
- Faster than full deployment (skips Terraform plan/apply)

**Package Process:**
```bash
# Install Lambda-compatible dependencies
pip install --platform manylinux2014_x86_64 \
  --target=lambda-package \
  --python-version 3.11 \
  --only-binary=:all: \
  fastapi pydantic boto3 mangum ...

# Create deployment zip
zip -r lambda-package.zip .
```

### 3. CI/CD Pipeline (`.github/workflows/ci.yml`)

**Triggers:**
- Every push and pull request to `main` or `development` branches

**What it does:**
1. **Backend Linting** (Python)
   - Uses Ruff for linting and formatting checks
   - Reports violations in GitHub UI

2. **Backend Tests**
   - Runs pytest with coverage reporting
   - Tests Canvas API connectivity (dry-run)
   - Generates coverage reports

3. **Frontend Tests** (React)
   - Runs ESLint for code quality
   - Builds application with Vite
   - Runs Jest/Vitest tests (if configured)

4. **Lambda Package Test**
   - Validates Lambda packaging script
   - Checks package size (warns if >250MB)
   - Ensures deployment package is buildable

5. **Pre-commit Hooks**
   - Runs pre-commit hooks on all files
   - Checks for secrets, trailing whitespace, etc.

6. **CI Summary**
   - Aggregates all test results
   - Reports overall pass/fail status

**Optimization:**
- Jobs run in parallel for faster feedback
- Uses `continue-on-error` for non-critical checks
- Caches dependencies (npm, Python packages)

## Workflow Usage Examples

### Automatic Deployments

**Full deployment (main branch):**
```bash
# Make changes to backend, frontend, or infrastructure
git add .
git commit -m "feat: add new dashboard feature"
git push origin main
# → Triggers: deploy.yml (full deployment to prod)
```

**Development deployment:**
```bash
git checkout -b dev-new-feature
# Make changes
git add .
git commit -m "feat: experimental feature"
git push origin dev-new-feature
# → Triggers: deploy.yml (full deployment to dev)
```

**Quick Lambda update:**
```bash
# Edit main.py only
git add main.py
git commit -m "fix: authentication bug"
git push origin main
# → Triggers: deploy-lambda.yml (fast Lambda-only update)
```

**CI checks on pull request:**
```bash
git checkout -b feature/dashboard-improvements
# Make changes
git push origin feature/dashboard-improvements
# Create pull request
# → Triggers: ci.yml (linting, tests, packaging)
```

### Manual Deployments

**Deploy to specific environment:**
1. Go to `Actions` → `Deploy to AWS`
2. Click `Run workflow`
3. Select environment (`dev` or `prod`)
4. Click `Run workflow` button

**Quick Lambda deployment:**
1. Go to `Actions` → `Deploy Lambda`
2. Click `Run workflow`
3. Select branch
4. Click `Run workflow` button

## Deployment Process Details

### First-Time Setup

1. **Create IAM user for GitHub Actions:**
   ```bash
   # Create IAM user
   aws iam create-user --user-name github-actions-deploy

   # Attach policies (adjust for least privilege)
   aws iam attach-user-policy --user-name github-actions-deploy \
     --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

   # Create access key
   aws iam create-access-key --user-name github-actions-deploy
   ```

2. **Add secrets to GitHub:**
   - Navigate to repository `Settings` → `Secrets and variables` → `Actions`
   - Click `New repository secret`
   - Add `AWS_ACCESS_KEY_ID` (from access key output)
   - Add `AWS_SECRET_ACCESS_KEY` (from access key output)

3. **Configure Canvas API secrets (optional for CI tests):**
   - Add `CANVAS_API_TOKEN`
   - Add `CANVAS_API_URL`
   - Add `CANVAS_COURSE_ID`

4. **Initial infrastructure deployment:**
   ```bash
   # Push to main or trigger manual deployment
   git push origin main
   ```

   This will:
   - Create S3 buckets for frontend and data
   - Deploy Lambda function
   - Configure API Gateway
   - Set up CloudFront distribution
   - Configure Secrets Manager

### Regular Development Workflow

1. **Create feature branch:**
   ```bash
   git checkout -b feature/new-grading-view
   ```

2. **Make changes and test locally:**
   ```bash
   # Backend
   uv run uvicorn main:app --reload

   # Frontend
   cd canvas-react && npm run dev
   ```

3. **Commit and push:**
   ```bash
   git add .
   git commit -m "feat: add new grading view"
   git push origin feature/new-grading-view
   ```

4. **Create pull request:**
   - CI pipeline runs automatically
   - Review test results and linting output
   - Address any failures

5. **Merge to main:**
   ```bash
   # After PR approval
   git checkout main
   git merge feature/new-grading-view
   git push origin main
   ```

6. **Automatic deployment:**
   - Full deployment pipeline runs
   - Infrastructure updated (if Terraform changed)
   - Lambda function updated
   - Frontend deployed to S3/CloudFront
   - Post-deployment tests validate functionality

### Terraform State Management

The deployment uses remote Terraform state stored in S3:

**State Configuration:**
- Backend: S3 bucket (auto-created by `setup-backend.sh`)
- State locking: DynamoDB table (auto-created)
- Workspace: Environment-specific (dev, prod)

**Setup Script:**
```bash
./scripts/setup-backend.sh
```

This creates:
- S3 bucket: `canvas-ta-dashboard-terraform-state-<region>-<account-id>`
- DynamoDB table: `canvas-ta-dashboard-terraform-lock`

## Monitoring Deployments

### GitHub Actions UI

1. Navigate to `Actions` tab in repository
2. Select workflow run to view detailed logs
3. Review job summaries for:
   - Terraform plan output
   - Lambda update status
   - Health check results
   - Deployment summary with resource URLs

### AWS Console Monitoring

**Lambda Functions:**
```bash
# Get Lambda function status
aws lambda get-function --function-name canvas-ta-dashboard-api-lambda-prod

# View recent invocations
aws lambda get-function-event-invoke-config \
  --function-name canvas-ta-dashboard-api-lambda-prod

# Tail logs
aws logs tail /aws/lambda/canvas-ta-dashboard-api-lambda-prod --follow
```

**API Gateway:**
```bash
# Get API details
aws apigatewayv2 get-apis \
  --query 'Items[?Name==`canvas-ta-dashboard-api-prod`]'

# Test endpoint
curl https://<api-id>.execute-api.us-east-1.amazonaws.com/health
```

**CloudFront:**
```bash
# List distributions
aws cloudfront list-distributions \
  --query 'DistributionList.Items[?Comment==`Canvas TA Dashboard Frontend`]'

# Get distribution status
aws cloudfront get-distribution --id <distribution-id>
```

**S3 Buckets:**
```bash
# List frontend files
aws s3 ls s3://canvas-ta-dashboard-frontend-prod/

# Check Canvas data
aws s3 ls s3://canvas-ta-dashboard-canvas-data-prod/
```

### CloudWatch Logs and Metrics

**Lambda Logs:**
- Log group: `/aws/lambda/canvas-ta-dashboard-api-lambda-{env}`
- Access via CloudWatch Logs console or AWS CLI

**Common CloudWatch Insights Queries:**

```sql
-- Find errors in Lambda logs
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 20

-- API request latency
fields @timestamp, @duration
| filter @type = "REPORT"
| stats avg(@duration), max(@duration), min(@duration)

-- Authentication failures
fields @timestamp, @message
| filter @message like /401/ or @message like /authentication/
| sort @timestamp desc
```

## Troubleshooting

### Common Issues

#### 1. Deployment Fails: "Terraform State Lock"

**Cause:** Previous Terraform run did not complete, leaving state locked

**Solution:**
```bash
# Force unlock (use with caution)
cd terraform
terraform force-unlock <lock-id>
```

#### 2. Lambda Update Fails: "Package Too Large"

**Cause:** Lambda deployment package exceeds 50MB limit

**Solution:**
- Review dependencies in `pyproject.toml`
- Remove unnecessary packages
- Use Lambda layers for large dependencies
- Check package size in CI logs

```bash
# Check package size locally
./scripts/package-lambda-api.sh
du -h lambda-api.zip
```

#### 3. Health Check Fails After Deployment

**Cause:** Lambda function not updated or API Gateway not synced

**Solution:**
1. Check Lambda function logs in CloudWatch
2. Verify environment variables are set correctly
3. Test Lambda function directly:
   ```bash
   aws lambda invoke \
     --function-name canvas-ta-dashboard-api-lambda-prod \
     --payload '{"requestContext":{"http":{"method":"GET","path":"/health"}}}' \
     response.json
   ```

#### 4. Frontend Shows Old Version After Deployment

**Cause:** CloudFront cache not invalidated or browser cache

**Solution:**
1. Verify CloudFront invalidation completed:
   ```bash
   aws cloudfront list-invalidations --distribution-id <id>
   ```
2. Force browser refresh (Ctrl+Shift+R)
3. Check S3 bucket for updated files:
   ```bash
   aws s3 ls s3://canvas-ta-dashboard-frontend-prod/ --recursive
   ```

#### 5. CORS Errors in Browser Console

**Cause:** CORS not configured properly in Lambda/API Gateway

**Solution:**
1. Check Lambda environment variables for `CORS_ORIGINS`
2. Verify API Gateway CORS configuration in Terraform
3. Test CORS manually:
   ```bash
   curl -X OPTIONS https://<api-endpoint>/api/auth/login \
     -H "Origin: https://your-frontend-domain.com" \
     -H "Access-Control-Request-Method: POST" \
     -i
   ```

#### 6. Terraform Apply Fails: "Resource Already Exists"

**Cause:** Terraform state out of sync with actual AWS resources

**Solution:**
1. Import existing resource:
   ```bash
   cd terraform
   terraform import <resource_type>.<name> <aws_resource_id>
   ```
2. Or remove from state if no longer needed:
   ```bash
   terraform state rm <resource_type>.<name>
   ```

#### 7. GitHub Actions: "AWS Credentials Not Found"

**Cause:** Secrets not configured or incorrect

**Solution:**
1. Verify secrets exist in GitHub repository settings
2. Check secret names match exactly (`AWS_ACCESS_KEY_ID`, not `aws_access_key_id`)
3. Regenerate IAM access keys if compromised

## Deployment Optimization

### Reduce Deployment Times

1. **Use Lambda-only workflow for code changes:**
   - `deploy-lambda.yml` is 2-3x faster than full deployment
   - Skips Terraform plan/apply
   - Only updates Lambda function code

2. **Leverage caching:**
   - npm packages cached in GitHub Actions
   - Python packages cached (UV)
   - Terraform providers cached

3. **Selective deployments:**
   - Push only necessary files
   - Use feature branches for testing
   - Merge to main only when ready

### Cost Optimization

1. **Serverless architecture benefits:**
   - No idle costs (pay only for invocations)
   - Auto-scaling without over-provisioning
   - AWS Free Tier eligible (Lambda, API Gateway, S3)

2. **Estimated monthly costs:**
   - Lambda: $1-5 (based on invocations)
   - API Gateway: $1-3 (based on requests)
   - S3: $1-2 (storage + data transfer)
   - CloudFront: $1-5 (data transfer)
   - Secrets Manager: $0.40/secret
   - **Total: ~$5-20/month** (typical usage)

3. **Cost monitoring:**
   - Enable AWS Cost Explorer
   - Set billing alerts
   - Use AWS Budgets for spending limits

## Additional Resources

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [API Gateway HTTP API Guide](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [Mangum - ASGI Adapter for AWS Lambda](https://mangum.io/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

## Security Best Practices

1. **Rotate AWS credentials regularly** (every 90 days)
2. **Use least-privilege IAM policies** (restrict to specific resources)
3. **Enable MFA for AWS console access**
4. **Store secrets in AWS Secrets Manager**, not environment variables
5. **Enable CloudWatch alarms** for Lambda errors and throttling
6. **Review CloudWatch logs** regularly for security events
7. **Use HTTPS only** for API and frontend (enforced by CloudFront)
8. **Configure API Gateway throttling** to prevent abuse
9. **Enable AWS CloudTrail** for audit logging
10. **Regularly update dependencies** to patch security vulnerabilities

---

**Last Updated**: 2025-11-28
**Documentation Version**: 2.0 (Serverless Architecture)
**Previous Version**: 1.0 (ECS/Fargate - Deprecated)
