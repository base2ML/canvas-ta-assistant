# Canvas TA Assistant - Terraform Infrastructure

This directory contains Terraform Infrastructure as Code (IaC) for deploying the Canvas TA Assistant application to AWS using modern best practices.

## Architecture Overview

The infrastructure consists of:

- **VPC**: Multi-AZ networking with public and private subnets
- **ECR**: Container registry for Docker images
- **ECS on Fargate**: Serverless container orchestration
- **Application Load Balancer**: Traffic distribution and SSL termination
- **IAM**: Least-privilege roles and policies
- **CloudWatch**: Centralized logging and monitoring
- **Auto Scaling**: CPU and memory-based scaling

```
┌─────────────────────────────────────────────────────────────────┐
│                          AWS Cloud                              │
│                                                                 │
│  ┌───────────────────────────────────────────────────────┐     │
│  │  VPC (10.0.0.0/16)                                    │     │
│  │                                                       │     │
│  │  ┌────────────────────────────────────────┐          │     │
│  │  │  Public Subnets (2 AZs)                │          │     │
│  │  │  ┌────────────┐      ┌────────────┐    │          │     │
│  │  │  │    ALB     │      │    NAT     │    │          │     │
│  │  │  └─────┬──────┘      └─────┬──────┘    │          │     │
│  │  └────────┼───────────────────┼────────────┘          │     │
│  │           │                   │                       │     │
│  │  ┌────────┼───────────────────┼────────────┐          │     │
│  │  │  Private Subnets (2 AZs)   │            │          │     │
│  │  │        │                   │            │          │     │
│  │  │  ┌─────▼───────┐     ┌─────▼───────┐   │          │     │
│  │  │  │  ECS Tasks  │     │  ECS Tasks  │   │          │     │
│  │  │  │  (Fargate)  │     │  (Fargate)  │   │          │     │
│  │  │  └─────────────┘     └─────────────┘   │          │     │
│  │  └────────────────────────────────────────┘          │     │
│  └───────────────────────────────────────────────────────┘     │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │     ECR      │  │   IAM Roles  │  │  CloudWatch  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
terraform/
├── README.md                    # This file
├── backend.tf                   # S3 backend configuration
├── main.tf                      # Root module (orchestrates all modules)
├── variables.tf                 # Input variables
├── outputs.tf                   # Output values
├── terraform.tfvars.example     # Example variables file
├── .gitignore                   # Terraform-specific gitignore
│
├── environments/                # Environment-specific configurations
│   ├── dev.tfvars              # Development environment
│   ├── staging.tfvars          # Staging environment
│   └── production.tfvars       # Production environment
│
└── modules/                     # Reusable Terraform modules
    ├── vpc/                     # VPC and networking
    ├── ecr/                     # Container registry
    ├── iam/                     # IAM roles and policies
    ├── alb/                     # Application Load Balancer
    └── ecs/                     # ECS cluster and services
```

## Prerequisites

1. **Terraform**: Install Terraform >= 1.5.0
   ```bash
   # macOS
   brew install terraform

   # Linux
   wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
   unzip terraform_1.6.0_linux_amd64.zip
   sudo mv terraform /usr/local/bin/
   ```

2. **AWS CLI**: Configure AWS credentials
   ```bash
   aws configure
   ```

3. **AWS Permissions**: Ensure your AWS account has permissions to create:
   - VPC, Subnets, NAT Gateways, Internet Gateways
   - ECR repositories
   - ECS clusters, services, and task definitions
   - Application Load Balancers
   - IAM roles and policies
   - CloudWatch log groups

## Quick Start

### 1. Initialize Terraform

```bash
cd terraform
terraform init
```

### 2. Create Backend Resources (First Time Only)

The Terraform state needs to be stored in S3. Create the backend resources:

```bash
# Create S3 bucket for Terraform state
aws s3api create-bucket \
  --bucket canvas-ta-terraform-state \
  --region us-east-1

# Enable versioning for state file protection
aws s3api put-bucket-versioning \
  --bucket canvas-ta-terraform-state \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name canvas-ta-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

Then uncomment the backend configuration in `backend.tf`.

### 3. Plan the Infrastructure

#### Development Environment
```bash
terraform plan -var-file=environments/dev.tfvars
```

#### Staging Environment
```bash
terraform plan -var-file=environments/staging.tfvars
```

#### Production Environment
```bash
terraform plan -var-file=environments/production.tfvars
```

### 4. Apply the Configuration

```bash
# For production
terraform apply -var-file=environments/production.tfvars

# Approve the changes when prompted
```

### 5. View Outputs

```bash
terraform output
```

This will display:
- Application URL (ALB DNS name)
- ECR repository URL
- ECS cluster and service names
- CloudWatch log group name

## Environment Configuration

### Development Environment

Optimized for cost and rapid development:

- **Resources**: Minimal (0.25 vCPU, 512 MB RAM)
- **Instances**: 1 task
- **NAT Gateway**: Single NAT (cost savings)
- **Fargate Spot**: Enabled (70% cost reduction)
- **Monitoring**: Minimal
- **Auto-scaling**: Disabled

**Estimated Cost**: ~$20-30/month

```bash
terraform apply -var-file=environments/dev.tfvars
```

### Staging Environment

Balanced configuration for testing:

- **Resources**: Moderate (0.5 vCPU, 1 GB RAM)
- **Instances**: 2 tasks
- **NAT Gateway**: Single NAT
- **Fargate Spot**: Mixed (50/50)
- **Monitoring**: Enabled
- **Auto-scaling**: 1-5 tasks

**Estimated Cost**: ~$50-80/month

```bash
terraform apply -var-file=environments/staging.tfvars
```

### Production Environment

High availability and reliability:

- **Resources**: Adequate (0.5 vCPU, 1 GB RAM, adjustable)
- **Instances**: 3 tasks minimum
- **NAT Gateway**: One per AZ (high availability)
- **Fargate Spot**: Disabled (reliability)
- **Monitoring**: Full Container Insights
- **Auto-scaling**: 2-20 tasks

**Estimated Cost**: ~$150-300/month (varies with traffic)

```bash
terraform apply -var-file=environments/production.tfvars
```

## Customization

### Adjust Task Resources

Edit the appropriate `environments/*.tfvars` file:

```hcl
task_cpu    = 1024  # 1 vCPU
task_memory = 2048  # 2 GB
```

### Enable HTTPS

1. Request an ACM certificate:
   ```bash
   aws acm request-certificate \
     --domain-name canvas-ta.example.com \
     --validation-method DNS \
     --region us-east-1
   ```

2. Update `environments/production.tfvars`:
   ```hcl
   enable_https          = true
   enable_https_redirect = true
   certificate_arn       = "arn:aws:acm:us-east-1:123456789012:certificate/abc123"
   ```

3. Apply changes:
   ```bash
   terraform apply -var-file=environments/production.tfvars
   ```

### Configure Environment Variables

Add environment variables in `environments/*.tfvars`:

```hcl
environment_variables = {
  ENVIRONMENT = "production"
  LOG_LEVEL   = "INFO"
  CUSTOM_VAR  = "value"
}
```

### Use Secrets Manager

1. Create secret:
   ```bash
   aws secretsmanager create-secret \
     --name canvas-api-key \
     --secret-string "your-api-key" \
     --region us-east-1
   ```

2. Update `environments/*.tfvars`:
   ```hcl
   enable_secrets_access = true
   secrets_arns = [
     "arn:aws:secretsmanager:us-east-1:123456789012:secret:canvas-api-key-abc123"
   ]

   ecs_secrets = {
     CANVAS_API_KEY = "arn:aws:secretsmanager:us-east-1:123456789012:secret:canvas-api-key-abc123"
   }
   ```

## Deployment Workflow

### Initial Deployment

1. **Create infrastructure**:
   ```bash
   terraform apply -var-file=environments/production.tfvars
   ```

2. **Build and push Docker image**:
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ecr-url>
   docker build -t <ecr-url>:latest .
   docker push <ecr-url>:latest
   ```

3. **Update ECS service**:
   ```bash
   aws ecs update-service \
     --cluster <cluster-name> \
     --service <service-name> \
     --force-new-deployment
   ```

### Updating Infrastructure

```bash
# Make changes to Terraform files or tfvars
terraform plan -var-file=environments/production.tfvars
terraform apply -var-file=environments/production.tfvars
```

### Updating Application Code

Use GitHub Actions (see `.github/workflows/deploy.yml`):

```yaml
# Automatically deploys on push to main/production branches
git push origin main
```

Or manually:

```bash
# Build and push new image
docker build -t <ecr-url>:new-tag .
docker push <ecr-url>:new-tag

# Update task definition and service via Terraform or AWS CLI
```

## Monitoring and Operations

### View Logs

```bash
# Tail logs
aws logs tail /ecs/canvas-ta-production --follow

# Filter logs
aws logs tail /ecs/canvas-ta-production --follow --filter-pattern "ERROR"
```

### Check Service Status

```bash
aws ecs describe-services \
  --cluster canvas-ta-production-cluster \
  --services canvas-ta-production-service
```

### View Metrics

Visit CloudWatch Console:
- Container Insights for detailed metrics
- Custom dashboards for application monitoring

### Access Running Container (if ECS Exec enabled)

```bash
aws ecs execute-command \
  --cluster canvas-ta-production-cluster \
  --task <task-id> \
  --container app \
  --interactive \
  --command "/bin/bash"
```

## Cost Optimization

### Development Environment

- Use Fargate Spot (70% savings)
- Single NAT Gateway
- Minimal monitoring
- Lower log retention

**Savings**: ~50-70% vs production

### Staging Environment

- Mixed Fargate and Fargate Spot
- Single NAT Gateway
- Reduced log retention

**Savings**: ~30-40% vs production

### Production Optimizations

- Right-size tasks (start small, scale up)
- Use auto-scaling to match demand
- Set appropriate log retention (30 days vs unlimited)
- Review Container Insights cost vs value

## Troubleshooting

### Terraform Init Fails

```bash
# Clear Terraform cache
rm -rf .terraform
terraform init
```

### Plan Shows Unwanted Changes

```bash
# Review what changed
terraform plan -var-file=environments/production.tfvars -out=plan.tfplan
terraform show plan.tfplan
```

### Apply Fails

```bash
# Check AWS credentials
aws sts get-caller-identity

# Check permissions
aws iam get-user
```

### ECS Tasks Not Starting

1. Check CloudWatch logs: `/ecs/canvas-ta-<env>`
2. Verify ECR image exists and is accessible
3. Check security groups allow ALB → ECS traffic
4. Ensure subnets have NAT Gateway for internet access

### High Costs

1. Review auto-scaling settings
2. Check for idle resources
3. Consider Fargate Spot for non-production
4. Reduce log retention
5. Use AWS Cost Explorer to identify expensive resources

## Terraform Commands Reference

```bash
# Initialize
terraform init

# Format code
terraform fmt -recursive

# Validate configuration
terraform validate

# Plan changes
terraform plan -var-file=environments/production.tfvars

# Apply changes
terraform apply -var-file=environments/production.tfvars

# Destroy infrastructure
terraform destroy -var-file=environments/production.tfvars

# Show current state
terraform show

# List resources
terraform state list

# View outputs
terraform output

# Import existing resource
terraform import module.vpc.aws_vpc.main vpc-123456
```

## Security Best Practices

1. **Remote State**: Always use S3 backend with encryption
2. **State Locking**: Enable DynamoDB locking
3. **Secrets**: Never commit `.tfvars` files with secrets
4. **IAM**: Follow least-privilege principle
5. **VPC**: Always use private subnets for ECS tasks
6. **HTTPS**: Enable SSL/TLS for production
7. **Monitoring**: Enable CloudWatch alarms
8. **Backup**: Enable versioning on S3 state bucket

## CI/CD Integration

The infrastructure is designed to work with GitHub Actions:

1. **Infrastructure**: Managed by Terraform (this directory)
2. **Application**: Deployed via GitHub Actions (`.github/workflows/deploy.yml`)

### GitHub Actions Setup

The deploy workflow automatically:
1. Builds Docker image
2. Pushes to ECR
3. Updates ECS task definition
4. Deploys new version

See `.github/workflows/deploy.yml` for details.

## Module Documentation

Each module has its own detailed README:

- [VPC Module](./modules/vpc/README.md)
- [ECR Module](./modules/ecr/README.md)
- [IAM Module](./modules/iam/README.md)
- [ALB Module](./modules/alb/README.md)
- [ECS Module](./modules/ecs/README.md)

## Support

For issues or questions:

1. Check module READMEs for specific guidance
2. Review AWS CloudWatch logs
3. Check Terraform state: `terraform state list`
4. Validate configuration: `terraform validate`

## License

This infrastructure code is part of the Canvas TA Assistant project.
