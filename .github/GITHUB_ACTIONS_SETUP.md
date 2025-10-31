# GitHub Actions Setup Guide

This guide explains how to configure GitHub Actions for automated deployment of the Canvas TA Dashboard.

## Overview

The project uses intelligent GitHub Actions workflows that automatically detect changes and deploy only what's necessary:

- **Backend changes** → Rebuild Docker image with backend updates
- **Frontend changes** → Rebuild Docker image with cached backend layers
- **Infrastructure changes** → Run Terraform plan/apply
- **CI/CD checks** → Run only relevant tests based on changed files

## Required GitHub Secrets

Configure these secrets in your GitHub repository settings (`Settings` → `Secrets and variables` → `Actions`):

### AWS Credentials

| Secret Name | Description | How to Get |
|-------------|-------------|------------|
| `AWS_ACCESS_KEY_ID` | AWS access key for GitHub Actions | Create IAM user with deployment permissions |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key | Created when generating access key |

**Required IAM Permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:*",
        "ecs:*",
        "ec2:Describe*",
        "elasticloadbalancing:Describe*",
        "logs:*"
      ],
      "Resource": "*"
    }
  ]
}
```

### ECS Configuration (Optional - for legacy deploy.yml)

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `ECR_REGISTRY` | ECR registry URL | `123456789012.dkr.ecr.us-east-1.amazonaws.com` |
| `ECS_CLUSTER_NAME` | ECS cluster name | `canvas-ta-dashboard-cluster-prod` |
| `ECS_SERVICE_NAME` | ECS service name | `canvas-ta-dashboard-service-prod` |
| `ECS_TASK_DEFINITION` | Task definition family | `canvas-ta-dashboard-task-prod` |

**Note:** The new optimized workflows automatically discover these values from Terraform outputs.

## Workflows Overview

### 1. CI/CD Pipeline (`.github/workflows/ci.yml`)

**Triggers:** Every push and pull request

**What it does:**
- Runs backend tests (Python/FastAPI) when backend files change
- Runs frontend tests (React/Vite) when frontend files change
- Builds Docker image when Dockerfile or code changes
- Runs pre-commit hooks for code quality

**Path-based optimization:**
- Backend tests only run if `main.py`, `pyproject.toml` changed
- Frontend tests only run if `canvas-react/**` changed
- Docker build only runs if `Dockerfile`, `main.py`, or `canvas-react/**` changed

### 2. Backend Deployment (`.github/workflows/deploy-backend.yml`)

**Triggers:**
- Push to `main` or `production` branches
- Changes in: `main.py`, `pyproject.toml`, `uv.lock`, `Dockerfile`
- Manual workflow dispatch

**What it does:**
1. Builds Docker image with Docker layer caching
2. Pushes to ECR with tags: `latest` and `<commit-sha>`
3. Forces ECS service deployment
4. Waits for deployment to stabilize

**Optimization:**
- Uses GitHub Actions cache for Docker layers
- Only triggers when backend files actually change
- Force deployment ensures new containers are deployed

### 3. Frontend Deployment (`.github/workflows/deploy-frontend.yml`)

**Triggers:**
- Push to `main` or `production` branches
- Changes in: `canvas-react/**`
- Manual workflow dispatch

**What it does:**
1. Builds Docker image with cached backend layers (faster!)
2. Pushes to ECR with tags: `latest` and `<commit-sha>`
3. Forces ECS service deployment
4. Waits for deployment to stabilize

**Optimization:**
- Reuses backend Docker layers from cache
- Only rebuilds frontend assets
- Significantly faster than full rebuild

### 4. Infrastructure Deployment (`.github/workflows/deploy-infrastructure.yml`)

**Triggers:**
- Push to `main` or `production` branches with Terraform changes
- Manual workflow dispatch with action choice (plan/apply/destroy)

**What it does:**
1. Creates ECR repository if it doesn't exist
2. Runs `terraform init` and `terraform validate`
3. Runs `terraform plan` and shows changes
4. On production branch or manual apply: runs `terraform apply`
5. Uploads Terraform outputs as artifacts

**Features:**
- Comments Terraform plan on pull requests
- Manual workflow dispatch for plan/apply/destroy operations
- Automatic ECR repository creation

### 5. Legacy Deployment (`.github/workflows/deploy.yml`)

**Status:** ⚠️ Kept for backward compatibility, but new workflows are recommended

**Note:** This workflow always rebuilds everything. Consider using the new optimized workflows instead.

## Workflow Usage Examples

### Automatic Deployments

**Backend changes only:**
```bash
# Edit main.py
git add main.py
git commit -m "Fix authentication bug"
git push origin main
# → Triggers: CI + Backend Deployment (fast)
```

**Frontend changes only:**
```bash
# Edit React components
git add canvas-react/
git commit -m "Update dashboard UI"
git push origin main
# → Triggers: CI + Frontend Deployment (uses cached backend)
```

**Infrastructure changes:**
```bash
# Edit Terraform files
git add terraform/
git commit -m "Add S3 lifecycle policy"
git push origin main
# → Triggers: Infrastructure Deployment (Terraform plan/apply)
```

### Manual Deployments

**Deploy backend manually:**
1. Go to `Actions` → `Deploy Backend`
2. Click `Run workflow`
3. Select branch and run

**Deploy infrastructure with specific action:**
1. Go to `Actions` → `Deploy Infrastructure`
2. Click `Run workflow`
3. Choose action: `plan`, `apply`, or `destroy`
4. Select branch and run

## Deployment Process

### First-Time Setup

1. **Create IAM user for GitHub Actions:**
   ```bash
   aws iam create-user --user-name github-actions-deploy
   aws iam attach-user-policy --user-name github-actions-deploy \
     --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess
   aws iam attach-user-policy --user-name github-actions-deploy \
     --policy-arn arn:aws:iam::aws:policy/AmazonECS_FullAccess
   aws iam create-access-key --user-name github-actions-deploy
   ```

2. **Add secrets to GitHub:**
   - Copy `AccessKeyId` → `AWS_ACCESS_KEY_ID` secret
   - Copy `SecretAccessKey` → `AWS_SECRET_ACCESS_KEY` secret

3. **Create infrastructure:**
   - Push Terraform changes to trigger infrastructure deployment
   - Or manually run: `Deploy Infrastructure` workflow with `apply` action

4. **Deploy application:**
   - Push code changes to trigger automatic deployment
   - Or manually run: `Deploy Backend` or `Deploy Frontend` workflow

### Regular Development Workflow

1. **Create feature branch:**
   ```bash
   git checkout -b feature/new-dashboard-widget
   ```

2. **Make changes and commit:**
   ```bash
   git add canvas-react/
   git commit -m "Add new dashboard widget"
   git push origin feature/new-dashboard-widget
   ```

3. **Create pull request:**
   - CI pipeline runs automatically
   - Terraform plan commented on PR (if infrastructure changed)
   - Review test results and plan

4. **Merge to main:**
   ```bash
   # After PR approval
   git checkout main
   git merge feature/new-dashboard-widget
   git push origin main
   ```

5. **Automatic deployment:**
   - Appropriate workflow runs based on changed files
   - Monitor deployment in GitHub Actions tab
   - Check ECS service for new task deployment

## Monitoring Deployments

### GitHub Actions UI

1. Go to `Actions` tab in GitHub repository
2. Select workflow run to view logs
3. Check deployment summary for status

### AWS Console

**Check ECS deployment:**
```bash
aws ecs describe-services \
  --cluster canvas-ta-dashboard-cluster-prod \
  --services canvas-ta-dashboard-service-prod \
  --query 'services[0].deployments'
```

**View ECS task logs:**
```bash
aws logs tail /ecs/canvas-ta-dashboard-task-prod --follow
```

**Check ECR images:**
```bash
aws ecr list-images \
  --repository-name canvas-ta-dashboard \
  --query 'imageIds[*].imageTag'
```

## Troubleshooting

### Deployment Fails: "Service Not Stable"

**Cause:** ECS tasks are crashing or failing health checks

**Solution:**
1. Check ECS task logs: `aws logs tail /ecs/canvas-ta-dashboard-task-prod`
2. Verify environment variables in ECS task definition
3. Check S3 bucket access permissions
4. Verify Cognito configuration

### Docker Build Fails: "Out of Disk Space"

**Cause:** Docker layer cache consuming too much space

**Solution:**
1. GitHub Actions automatically manages cache
2. Force fresh build by manually triggering workflow

### Terraform Apply Fails: "Resource Already Exists"

**Cause:** Terraform state out of sync with actual resources

**Solution:**
1. Import existing resource: `terraform import`
2. Or remove from state: `terraform state rm`
3. Run workflow again

### ECS Service Not Updating with Latest Image

**Cause:** Using `:latest` tag without forcing deployment

**Solution:**
- Our workflows use `--force-new-deployment` flag
- Verify workflow includes this flag in ECS update step

## Optimization Tips

### Reduce Build Times

1. **Use path filters effectively:**
   - Workflows only trigger on relevant file changes
   - Saves GitHub Actions minutes

2. **Docker layer caching:**
   - Frontend deploys reuse backend layers
   - Significantly faster builds

3. **Parallel CI jobs:**
   - Backend and frontend tests run in parallel
   - Faster feedback on pull requests

### Cost Optimization

1. **Selective deployments:**
   - Only deploy what changed
   - Reduces ECR storage and data transfer

2. **Efficient testing:**
   - Skip expensive tests when only docs changed
   - Use path-based job conditions

3. **Cache management:**
   - GitHub Actions cache automatically managed
   - Reduces build times and costs

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [AWS ECS Deployment Guide](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-types.html)
- [Docker Build Cache Best Practices](https://docs.docker.com/build/cache/)
- [Terraform GitHub Actions](https://developer.hashicorp.com/terraform/tutorials/automation/github-actions)
