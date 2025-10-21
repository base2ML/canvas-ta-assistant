# Canvas TA Assistant - Deployment Guide

This guide walks you through deploying the Canvas TA Assistant infrastructure to AWS using Terraform.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [First-Time Deployment](#first-time-deployment)
4. [Deploying the Application](#deploying-the-application)
5. [Post-Deployment Configuration](#post-deployment-configuration)
6. [Updating Infrastructure](#updating-infrastructure)
7. [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)
8. [Cost Management](#cost-management)

## Prerequisites

### Required Tools

- **Terraform**: >= 1.5.0 ([Installation Guide](https://developer.hashicorp.com/terraform/downloads))
- **AWS CLI**: >= 2.0 ([Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html))
- **Docker**: For building images ([Installation Guide](https://docs.docker.com/get-docker/))

### AWS Account Requirements

- AWS account with administrator access (or specific IAM permissions)
- AWS CLI configured with credentials
- Sufficient service quotas for:
  - VPC (1)
  - ECS (1 cluster, 10+ tasks)
  - Elastic IPs (2 for NAT Gateways)
  - Application Load Balancers (1)

### Verify Prerequisites

```bash
# Check Terraform version
terraform version

# Check AWS CLI configuration
aws sts get-caller-identity

# Check Docker
docker --version
```

## Initial Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/base2ML/canvas-ta-assistant.git
cd canvas-ta-assistant/terraform
```

### Step 2: Create Terraform Backend

The Terraform state needs to be stored in S3 for team collaboration and safety.

```bash
# Create S3 bucket for state
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

# Create DynamoDB table for locking
aws dynamodb create-table \
  --table-name canvas-ta-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### Step 3: Configure Backend

Edit `backend.tf` and uncomment the backend configuration:

```hcl
backend "s3" {
  bucket         = "canvas-ta-terraform-state"
  key            = "canvas-ta-assistant/terraform.tfstate"
  region         = "us-east-1"
  encrypt        = true
  dynamodb_table = "canvas-ta-terraform-locks"
}
```

### Step 4: Initialize Terraform

```bash
terraform init
```

You should see:
```
Terraform has been successfully initialized!
```

## First-Time Deployment

### Step 1: Choose Environment

For your first deployment, start with **development**:

```bash
# Review the development configuration
cat environments/dev.tfvars
```

### Step 2: Plan the Infrastructure

```bash
terraform plan -var-file=environments/dev.tfvars
```

Review the plan carefully. You should see resources being created:
- 1 VPC
- 4 Subnets (2 public, 2 private)
- 1 NAT Gateway (dev uses single NAT)
- 1 Internet Gateway
- 1 ECR Repository
- IAM Roles
- 1 Application Load Balancer
- 1 ECS Cluster
- Security Groups
- CloudWatch Log Groups

### Step 3: Apply the Configuration

```bash
terraform apply -var-file=environments/dev.tfvars
```

Type `yes` when prompted.

**⏱️ Deployment time**: 5-10 minutes

### Step 4: Save Outputs

```bash
terraform output > deployment-outputs.txt
```

Important outputs:
- `alb_url`: Your application URL
- `ecr_repository_url`: Where to push Docker images
- `ecs_cluster_name`: ECS cluster name
- `ecs_service_name`: ECS service name

## Deploying the Application

Now that infrastructure is ready, deploy the application.

### Step 1: Get ECR Repository URL

```bash
ECR_URL=$(terraform output -raw ecr_repository_url)
echo $ECR_URL
```

### Step 2: Authenticate Docker to ECR

```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ECR_URL
```

### Step 3: Build Docker Image

From the project root:

```bash
cd ..  # Back to project root
docker build -t canvas-ta-dashboard:latest .
```

### Step 4: Tag and Push Image

```bash
docker tag canvas-ta-dashboard:latest $ECR_URL:latest
docker push $ECR_URL:latest
```

### Step 5: Deploy to ECS

```bash
# Get cluster and service names
CLUSTER=$(cd terraform && terraform output -raw ecs_cluster_name)
SERVICE=$(cd terraform && terraform output -raw ecs_service_name)

# Force new deployment
aws ecs update-service \
  --cluster $CLUSTER \
  --service $SERVICE \
  --force-new-deployment \
  --region us-east-1
```

### Step 6: Verify Deployment

```bash
# Check service status
aws ecs describe-services \
  --cluster $CLUSTER \
  --services $SERVICE \
  --region us-east-1

# View logs
LOG_GROUP=$(cd terraform && terraform output -raw ecs_log_group_name)
aws logs tail $LOG_GROUP --follow
```

### Step 7: Access the Application

```bash
APP_URL=$(cd terraform && terraform output -raw alb_url)
echo "Application URL: $APP_URL"

# Test health endpoint
curl $APP_URL/api/health
```

Expected response:
```json
{"status": "healthy"}
```

## Post-Deployment Configuration

### Configure Custom Domain (Optional)

If you have a domain name:

1. **Request ACM Certificate**:
   ```bash
   aws acm request-certificate \
     --domain-name canvas-ta.example.com \
     --validation-method DNS \
     --region us-east-1
   ```

2. **Validate Certificate**: Add DNS records shown in ACM console

3. **Update Terraform Configuration**:
   Edit `environments/production.tfvars`:
   ```hcl
   enable_https = true
   enable_https_redirect = true
   certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/abc123"
   ```

4. **Apply Changes**:
   ```bash
   terraform apply -var-file=environments/production.tfvars
   ```

5. **Create DNS Record**:
   Point `canvas-ta.example.com` to ALB DNS name (from `alb_dns_name` output)

### Configure Secrets (Recommended)

Store sensitive data in AWS Secrets Manager:

```bash
# Create secret
aws secretsmanager create-secret \
  --name canvas-ta/production/canvas-api-key \
  --secret-string "your-canvas-api-key-here" \
  --region us-east-1

# Get secret ARN
SECRET_ARN=$(aws secretsmanager describe-secret \
  --secret-id canvas-ta/production/canvas-api-key \
  --query ARN --output text)

echo "Secret ARN: $SECRET_ARN"
```

Update `environments/production.tfvars`:

```hcl
enable_secrets_access = true
secrets_arns = [
  "arn:aws:secretsmanager:us-east-1:123456789012:secret:canvas-ta/production/canvas-api-key-abc123"
]

ecs_secrets = {
  CANVAS_API_KEY = "arn:aws:secretsmanager:us-east-1:123456789012:secret:canvas-ta/production/canvas-api-key-abc123"
}
```

Apply changes:
```bash
terraform apply -var-file=environments/production.tfvars
```

### Enable GitHub Actions CI/CD

1. **Create OIDC Provider** (one-time):
   ```bash
   aws iam create-open-id-connect-provider \
     --url https://token.actions.githubusercontent.com \
     --client-id-list sts.amazonaws.com \
     --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
   ```

2. **Get OIDC Provider ARN**:
   ```bash
   OIDC_ARN=$(aws iam list-open-id-connect-providers \
     --query "OpenIDConnectProviderList[?contains(Arn, 'token.actions.githubusercontent.com')].Arn" \
     --output text)
   echo "OIDC Provider ARN: $OIDC_ARN"
   ```

3. **Update Terraform**:
   Edit `environments/production.tfvars`:
   ```hcl
   enable_github_actions_role = true
   github_oidc_provider_arn   = "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
   github_repository          = "base2ML/canvas-ta-assistant"
   ```

4. **Apply and Get Role ARN**:
   ```bash
   terraform apply -var-file=environments/production.tfvars
   ROLE_ARN=$(terraform output -raw github_actions_role_arn)
   echo "GitHub Actions Role ARN: $ROLE_ARN"
   ```

5. **Add to GitHub Secrets**:
   - Go to repository Settings → Secrets → Actions
   - Add `AWS_GITHUB_ACTIONS_ROLE_ARN` with the role ARN

## Updating Infrastructure

### Modifying Resources

1. **Edit Configuration**: Update `environments/*.tfvars` or module files

2. **Plan Changes**:
   ```bash
   terraform plan -var-file=environments/production.tfvars
   ```

3. **Review Changes**: Carefully review what will be modified

4. **Apply Changes**:
   ```bash
   terraform apply -var-file=environments/production.tfvars
   ```

### Scaling Resources

**Increase Task Resources**:

Edit `environments/production.tfvars`:
```hcl
task_cpu    = 1024  # 1 vCPU (was 512)
task_memory = 2048  # 2 GB (was 1024)
```

**Adjust Auto-Scaling**:

```hcl
autoscaling_min_capacity = 3
autoscaling_max_capacity = 30
autoscaling_cpu_target   = 60
```

Apply:
```bash
terraform apply -var-file=environments/production.tfvars
```

## Monitoring and Troubleshooting

### View Application Logs

```bash
LOG_GROUP=$(terraform output -raw ecs_log_group_name)

# Tail logs
aws logs tail $LOG_GROUP --follow

# Filter for errors
aws logs tail $LOG_GROUP --follow --filter-pattern "ERROR"
```

### Check ECS Service Status

```bash
CLUSTER=$(terraform output -raw ecs_cluster_name)
SERVICE=$(terraform output -raw ecs_service_name)

aws ecs describe-services \
  --cluster $CLUSTER \
  --services $SERVICE
```

### View CloudWatch Metrics

Go to CloudWatch Console:
- Container Insights → ECS Clusters → `<cluster-name>`
- View CPU, Memory, Network metrics

### Common Issues

#### Tasks Not Starting

1. Check logs:
   ```bash
   aws logs tail $LOG_GROUP --follow
   ```

2. Verify image exists in ECR:
   ```bash
   aws ecr describe-images --repository-name cda-ta-dashboard
   ```

3. Check task execution role permissions

#### High Response Times

1. Check auto-scaling:
   ```bash
   aws application-autoscaling describe-scalable-targets \
     --service-namespace ecs
   ```

2. Increase task resources or count

#### 502/503 Errors

1. Verify health check endpoint works
2. Check security groups
3. Review target group health in ALB console

## Cost Management

### Monitor Costs

```bash
# Get current month costs
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE
```

### Reduce Costs

**Development Environment**:
- Use Fargate Spot (already enabled in dev.tfvars)
- Single NAT Gateway (already configured)
- Scale down to 1 task
- Disable Container Insights

**Staging Environment**:
- Use mixed Fargate/Spot
- Single NAT Gateway
- Reduce log retention to 7 days

**Production Optimization**:
- Right-size tasks (start small)
- Use auto-scaling aggressively
- Review Container Insights value

### Destroy Environment

**⚠️ WARNING**: This will delete all resources!

```bash
# Development
terraform destroy -var-file=environments/dev.tfvars

# Production (be careful!)
terraform destroy -var-file=environments/production.tfvars
```

## Next Steps

1. **Set up monitoring**: Configure CloudWatch alarms with SNS notifications
2. **Enable backups**: Configure automated snapshots if using databases
3. **Security hardening**: Review security groups, enable WAF if needed
4. **Performance testing**: Load test your application
5. **Disaster recovery**: Document and test recovery procedures

## Getting Help

- **Terraform Issues**: Check `terraform validate` and review error messages
- **AWS Issues**: Check AWS CloudWatch logs and service consoles
- **Application Issues**: Review application logs in CloudWatch

## Resources

- [Terraform AWS Provider Docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [AWS Fargate Pricing](https://aws.amazon.com/fargate/pricing/)
- [Project README](../README.md)
