# IAM Module

This module creates IAM roles and policies for ECS task execution, application tasks, and optional GitHub Actions CI/CD integration.

## Features

- **ECS Task Execution Role**: Allows ECS to pull container images and write logs
- **ECS Task Role**: Grants application permissions for AWS services
- **Least Privilege**: Minimal permissions following AWS best practices
- **Modular Policies**: Enable only the services your application needs
- **GitHub Actions Integration**: Optional OIDC-based role for CI/CD
- **Secrets Management**: Support for Secrets Manager and SSM Parameter Store

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    IAM Roles & Policies                      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ECS Task Execution Role                             │   │
│  │  • Pull ECR images                                   │   │
│  │  • Write CloudWatch Logs                             │   │
│  │  • Access Secrets Manager (optional)                 │   │
│  │  • Access SSM Parameters (optional)                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                   │
│                          ▼                                   │
│                    ECS Tasks                                 │
│                          │                                   │
│                          ▼                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ECS Task Role (Application Permissions)             │   │
│  │  • S3 access (optional)                              │   │
│  │  • DynamoDB access (optional)                        │   │
│  │  • CloudWatch Metrics (optional)                     │   │
│  │  • SES email sending (optional)                      │   │
│  │  • Custom policies (optional)                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  GitHub Actions Role (OIDC)                          │   │
│  │  • Push to ECR                                       │   │
│  │  • Update ECS services                               │   │
│  │  • Register task definitions                         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Usage

### Basic Configuration

```hcl
module "iam" {
  source = "./modules/iam"

  project_name = "canvas-ta"
  environment  = "production"

  # Enable CloudWatch metrics (recommended)
  enable_cloudwatch_metrics = true
}
```

### With Secrets Access

```hcl
module "iam" {
  source = "./modules/iam"

  project_name = "canvas-ta"
  environment  = "production"

  # Enable access to Secrets Manager
  enable_secrets_access = true
  secrets_arns = [
    "arn:aws:secretsmanager:us-east-1:123456789012:secret:canvas-api-key-abc123"
  ]

  # Enable access to SSM Parameter Store
  ssm_parameter_arns = [
    "arn:aws:ssm:us-east-1:123456789012:parameter/canvas-ta/production/*"
  ]
}
```

### With Application Permissions

```hcl
module "iam" {
  source = "./modules/iam"

  project_name = "canvas-ta"
  environment  = "production"

  # Enable S3 access for file storage
  enable_s3_access = true
  s3_bucket_arns = [
    "arn:aws:s3:::canvas-ta-production-uploads",
    "arn:aws:s3:::canvas-ta-production-uploads/*"
  ]

  # Enable DynamoDB access
  enable_dynamodb_access = true
  dynamodb_table_arns = [
    "arn:aws:dynamodb:us-east-1:123456789012:table/canvas-ta-sessions"
  ]

  # Enable SES for email notifications
  enable_ses_access = true

  # Enable CloudWatch metrics
  enable_cloudwatch_metrics = true
}
```

### With GitHub Actions OIDC

```hcl
module "iam" {
  source = "./modules/iam"

  project_name = "canvas-ta"
  environment  = "production"

  # Enable GitHub Actions role
  enable_github_actions_role = true
  github_oidc_provider_arn   = "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
  github_repository          = "base2ML/canvas-ta-assistant"
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| project_name | Name of the project | string | - | yes |
| environment | Environment name | string | - | yes |
| enable_secrets_access | Enable Secrets Manager access | bool | false | no |
| secrets_arns | Secrets Manager ARNs | list(string) | [] | no |
| ssm_parameter_arns | SSM Parameter ARNs | list(string) | [] | no |
| enable_s3_access | Enable S3 access | bool | false | no |
| s3_bucket_arns | S3 bucket ARNs | list(string) | [] | no |
| enable_dynamodb_access | Enable DynamoDB access | bool | false | no |
| dynamodb_table_arns | DynamoDB table ARNs | list(string) | [] | no |
| enable_cloudwatch_metrics | Enable CloudWatch metrics | bool | true | no |
| enable_ses_access | Enable SES access | bool | false | no |
| custom_task_policy | Custom IAM policy JSON | string | "" | no |
| enable_github_actions_role | Enable GitHub Actions role | bool | false | no |
| github_oidc_provider_arn | GitHub OIDC provider ARN | string | "" | no |
| github_repository | GitHub repository (owner/repo) | string | "" | no |

## Outputs

| Name | Description |
|------|-------------|
| ecs_task_execution_role_arn | ARN of ECS task execution role |
| ecs_task_execution_role_name | Name of ECS task execution role |
| ecs_task_role_arn | ARN of ECS task role |
| ecs_task_role_name | Name of ECS task role |
| github_actions_role_arn | ARN of GitHub Actions role |
| github_actions_role_name | Name of GitHub Actions role |

## IAM Roles Explained

### ECS Task Execution Role

Used by the **ECS service** to:
- Pull container images from ECR
- Write logs to CloudWatch Logs
- Retrieve secrets from Secrets Manager/SSM (if enabled)

This role is **not** used by your application code.

### ECS Task Role

Used by **your application code** running in the container to:
- Access AWS services (S3, DynamoDB, SES, etc.)
- Publish CloudWatch metrics
- Perform application-specific AWS operations

This role grants permissions to your application.

### GitHub Actions Role

Used by **GitHub Actions workflows** to:
- Authenticate to AWS using OIDC (no long-lived credentials)
- Push Docker images to ECR
- Update ECS task definitions and services
- Deploy new application versions

## GitHub Actions OIDC Setup

### 1. Create OIDC Provider (One-time setup)

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

### 2. Update GitHub Actions Workflow

```yaml
permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_GITHUB_ACTIONS_ROLE_ARN }}
          aws-region: us-east-1
```

### 3. Add Role ARN to GitHub Secrets

```bash
# Get the role ARN from Terraform output
terraform output github_actions_role_arn

# Add to GitHub repository secrets as AWS_GITHUB_ACTIONS_ROLE_ARN
```

## Security Best Practices

1. **Least Privilege**: Only enable the permissions your application needs
2. **Resource-Specific ARNs**: Always specify exact resource ARNs instead of `*`
3. **Secrets Management**: Use Secrets Manager or SSM Parameter Store, not environment variables
4. **OIDC for CI/CD**: Use GitHub OIDC instead of long-lived access keys
5. **Regular Audits**: Review IAM policies regularly and remove unused permissions
6. **Enable CloudTrail**: Monitor IAM role usage with CloudTrail logging

## Common Permissions

### Application Needs to Read/Write Files
```hcl
enable_s3_access = true
s3_bucket_arns = [
  "arn:aws:s3:::my-bucket",
  "arn:aws:s3:::my-bucket/*"
]
```

### Application Needs to Store Session Data
```hcl
enable_dynamodb_access = true
dynamodb_table_arns = [
  "arn:aws:dynamodb:us-east-1:123456789012:table/sessions"
]
```

### Application Needs to Send Emails
```hcl
enable_ses_access = true
```

### Application Needs to Read API Keys
```hcl
enable_secrets_access = true
secrets_arns = [
  "arn:aws:secretsmanager:us-east-1:123456789012:secret:api-keys-*"
]
```

## Troubleshooting

### Task Cannot Pull ECR Images

**Error**: "CannotPullContainerError"

**Solution**: Ensure the task execution role has ECR permissions:
```hcl
# This is automatically included in the module
ecr:GetAuthorizationToken
ecr:BatchCheckLayerAvailability
ecr:GetDownloadUrlForLayer
ecr:BatchGetImage
```

### Application Cannot Access AWS Services

**Error**: "AccessDeniedException"

**Solution**:
1. Verify the correct IAM role is attached to the task definition
2. Enable the required service access in the module
3. Ensure resource ARNs are correct

### GitHub Actions Cannot Deploy

**Error**: "User: ... is not authorized to perform: ecs:UpdateService"

**Solution**:
1. Verify OIDC provider is created
2. Check GitHub repository name matches configuration
3. Ensure role ARN is correctly set in GitHub secrets

## Cost Considerations

- IAM roles and policies are **free**
- Secrets Manager: ~$0.40/secret/month + $0.05 per 10,000 API calls
- SSM Parameter Store: Free for standard parameters, $0.05 per advanced parameter

## Integration with Other Modules

The IAM module is used by:
- **ECS Module**: Requires task execution and task role ARNs
- **GitHub Actions**: Uses the GitHub Actions role for CI/CD
- **Application Code**: Uses task role for AWS service access
