# ECR Module

This module creates an Elastic Container Registry (ECR) repository for storing and managing Docker container images.

## Features

- **Image Scanning**: Automatic vulnerability scanning on image push
- **Encryption**: AES256 or KMS encryption at rest
- **Lifecycle Policies**: Automatic cleanup of old and untagged images
- **Tag Mutability**: Configurable image tag immutability
- **Cross-Account Access**: Optional policy for multi-account access
- **CloudWatch Integration**: Optional logging for scan results

## Architecture

```
┌───────────────────────────────────────────────┐
│         AWS ECR Repository                     │
│                                                │
│  ┌─────────────────────────────────────────┐  │
│  │  Docker Images                          │  │
│  │  • app:latest                           │  │
│  │  • app:abc123 (git sha)                 │  │
│  │  • app:v1.0.0                           │  │
│  └─────────────────────────────────────────┘  │
│                                                │
│  Features:                                     │
│  ✓ Vulnerability Scanning                     │
│  ✓ Encryption at Rest (AES256/KMS)            │
│  ✓ Lifecycle Policies                         │
│  ✓ Image Tag Mutability Control               │
│                                                │
└───────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
   GitHub Actions            ECS Tasks Pull
   Push Images               Images to Deploy
```

## Usage

```hcl
module "ecr" {
  source = "./modules/ecr"

  project_name    = "canvas-ta"
  environment     = "production"
  repository_name = "app"

  # Security settings
  enable_image_scanning = true
  image_tag_mutability  = "MUTABLE"
  encryption_type       = "AES256"

  # Lifecycle management
  enable_lifecycle_policy = true
  max_image_count         = 30
  untagged_image_days     = 7

  # Optional: Cross-account access
  enable_cross_account_access = false
  allowed_account_ids         = []
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| project_name | Name of the project | string | - | yes |
| environment | Environment name | string | - | yes |
| repository_name | ECR repository name | string | "app" | no |
| image_tag_mutability | Tag mutability (MUTABLE/IMMUTABLE) | string | "MUTABLE" | no |
| enable_image_scanning | Enable scanning on push | bool | true | no |
| encryption_type | Encryption type (AES256/KMS) | string | "AES256" | no |
| kms_key_arn | KMS key ARN for encryption | string | null | no |
| enable_lifecycle_policy | Enable lifecycle policy | bool | true | no |
| max_image_count | Max images to retain | number | 30 | no |
| untagged_image_days | Days to keep untagged images | number | 7 | no |
| enable_cross_account_access | Enable cross-account access | bool | false | no |
| allowed_account_ids | Allowed AWS account IDs | list(string) | [] | no |

## Outputs

| Name | Description |
|------|-------------|
| repository_url | Full URL of the ECR repository |
| repository_arn | ARN of the ECR repository |
| repository_name | Name of the ECR repository |
| registry_id | Registry ID |
| repository_registry_url | Registry URL for Docker operations |

## Image Lifecycle Policy

The default lifecycle policy automatically:

1. **Keeps the last 30 images**: Prevents unlimited growth
2. **Removes untagged images after 7 days**: Cleans up build artifacts

Example lifecycle rules:
```json
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Keep last 30 images",
      "selection": {
        "tagStatus": "any",
        "countType": "imageCountMoreThan",
        "countNumber": 30
      },
      "action": { "type": "expire" }
    },
    {
      "rulePriority": 2,
      "description": "Remove untagged images older than 7 days",
      "selection": {
        "tagStatus": "untagged",
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 7
      },
      "action": { "type": "expire" }
    }
  ]
}
```

## Image Scanning

ECR integrates with AWS's vulnerability scanning:

- **Basic Scanning**: Free, uses CVE database
- **Enhanced Scanning**: Continuous monitoring with Amazon Inspector (additional cost)
- **Scan on Push**: Automatically scans new images
- **Scan Results**: Available in ECR console and via API

## Docker Operations

### Push Image
```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <registry_id>.dkr.ecr.us-east-1.amazonaws.com

# Tag image
docker tag my-app:latest <repository_url>:latest

# Push image
docker push <repository_url>:latest
```

### Pull Image
```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <registry_id>.dkr.ecr.us-east-1.amazonaws.com

# Pull image
docker pull <repository_url>:latest
```

## Best Practices

1. **Use Image Tags**:
   - Tag with git SHA for traceability: `app:abc123`
   - Tag with semantic version: `app:v1.0.0`
   - Always maintain `latest` tag for convenience

2. **Enable Scanning**: Always scan images for vulnerabilities

3. **Lifecycle Policies**: Set appropriate retention to control costs

4. **Encryption**: Use AES256 for most cases, KMS for compliance requirements

5. **Tag Immutability**:
   - MUTABLE: For development flexibility
   - IMMUTABLE: For production reproducibility

## Cost Considerations

- **Storage**: $0.10 per GB/month
- **Data Transfer**:
  - To ECS in same region: Free
  - Out to internet: Standard AWS data transfer rates
- **Image Scanning**:
  - Basic: Free
  - Enhanced: ~$0.09 per image scan
- **API Calls**: Free for most operations

## Security

- All images encrypted at rest (AES256 or KMS)
- Automatic vulnerability scanning
- IAM-based access control
- Support for cross-account access with explicit policies
- Integration with AWS CloudTrail for audit logging

## Integration with GitHub Actions

The ECR repository integrates with the GitHub Actions deploy workflow:

```yaml
- name: Login to Amazon ECR
  uses: aws-actions/amazon-ecr-login@v2

- name: Build and push
  run: |
    docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
    docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
```

See `.github/workflows/deploy.yml` for complete implementation.
