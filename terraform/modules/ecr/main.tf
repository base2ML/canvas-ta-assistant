# ECR Module - Container Registry
# Creates an Elastic Container Registry for storing Docker images

resource "aws_ecr_repository" "main" {
  name                 = "${var.project_name}-${var.environment}-${var.repository_name}"
  image_tag_mutability = var.image_tag_mutability

  # Image scanning on push for security
  image_scanning_configuration {
    scan_on_push = var.enable_image_scanning
  }

  # Encryption at rest
  encryption_configuration {
    encryption_type = var.encryption_type
    kms_key         = var.kms_key_arn
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-${var.repository_name}"
  }
}

# Lifecycle policy to manage image retention
resource "aws_ecr_lifecycle_policy" "main" {
  count      = var.enable_lifecycle_policy ? 1 : 0
  repository = aws_ecr_repository.main.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last ${var.max_image_count} images"
        selection = {
          tagStatus     = "any"
          countType     = "imageCountMoreThan"
          countNumber   = var.max_image_count
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Remove untagged images older than ${var.untagged_image_days} days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = var.untagged_image_days
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# Repository policy for cross-account access (if needed)
resource "aws_ecr_repository_policy" "main" {
  count      = var.enable_cross_account_access ? 1 : 0
  repository = aws_ecr_repository.main.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowPushPull"
        Effect = "Allow"
        Principal = {
          AWS = var.allowed_account_ids
        }
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
      }
    ]
  })
}

# CloudWatch log group for ECR scanning results (if enabled)
resource "aws_cloudwatch_log_group" "ecr_scanning" {
  count             = var.enable_image_scanning && var.enable_scanning_logs ? 1 : 0
  name              = "/aws/ecr/${var.project_name}-${var.environment}-${var.repository_name}/scanning"
  retention_in_days = var.scanning_logs_retention_days

  tags = {
    Name = "${var.project_name}-${var.environment}-ecr-scanning-logs"
  }
}
