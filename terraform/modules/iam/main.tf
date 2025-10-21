# IAM Module - Roles and Policies for ECS
# Creates IAM roles for ECS task execution and application tasks

# ============================================================================
# ECS Task Execution Role
# Used by ECS to pull container images and publish logs
# ============================================================================

resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.project_name}-${var.environment}-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-ecs-task-execution-role"
  }
}

# Attach AWS managed policy for ECS task execution
resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Additional policy for ECR access with image scanning
resource "aws_iam_role_policy" "ecs_task_execution_ecr" {
  name = "${var.project_name}-${var.environment}-ecs-task-execution-ecr-policy"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:DescribeImages"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

# Policy for accessing secrets (if using Secrets Manager or SSM Parameter Store)
resource "aws_iam_role_policy" "ecs_task_execution_secrets" {
  count = var.enable_secrets_access ? 1 : 0
  name  = "${var.project_name}-${var.environment}-ecs-task-execution-secrets-policy"
  role  = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "kms:Decrypt"
        ]
        Resource = var.secrets_arns
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameters",
          "ssm:GetParameter",
          "kms:Decrypt"
        ]
        Resource = var.ssm_parameter_arns
      }
    ]
  })
}

# ============================================================================
# ECS Task Role
# Used by the application running in the container
# ============================================================================

resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-${var.environment}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-ecs-task-role"
  }
}

# Policy for application to access S3 (if needed for file uploads/downloads)
resource "aws_iam_role_policy" "ecs_task_s3" {
  count = var.enable_s3_access ? 1 : 0
  name  = "${var.project_name}-${var.environment}-ecs-task-s3-policy"
  role  = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = var.s3_bucket_arns
      }
    ]
  })
}

# Policy for application to access DynamoDB (if needed)
resource "aws_iam_role_policy" "ecs_task_dynamodb" {
  count = var.enable_dynamodb_access ? 1 : 0
  name  = "${var.project_name}-${var.environment}-ecs-task-dynamodb-policy"
  role  = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem"
        ]
        Resource = var.dynamodb_table_arns
      }
    ]
  })
}

# Policy for application to publish CloudWatch metrics
resource "aws_iam_role_policy" "ecs_task_cloudwatch" {
  count = var.enable_cloudwatch_metrics ? 1 : 0
  name  = "${var.project_name}-${var.environment}-ecs-task-cloudwatch-policy"
  role  = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

# Policy for application to send emails via SES (if needed)
resource "aws_iam_role_policy" "ecs_task_ses" {
  count = var.enable_ses_access ? 1 : 0
  name  = "${var.project_name}-${var.environment}-ecs-task-ses-policy"
  role  = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = "*"
      }
    ]
  })
}

# Custom policy for additional permissions
resource "aws_iam_role_policy" "ecs_task_custom" {
  count  = var.custom_task_policy != "" ? 1 : 0
  name   = "${var.project_name}-${var.environment}-ecs-task-custom-policy"
  role   = aws_iam_role.ecs_task.id
  policy = var.custom_task_policy
}

# ============================================================================
# GitHub Actions Role for CI/CD (Optional)
# Allows GitHub Actions to deploy to ECS
# ============================================================================

resource "aws_iam_role" "github_actions" {
  count = var.enable_github_actions_role ? 1 : 0
  name  = "${var.project_name}-${var.environment}-github-actions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = var.github_oidc_provider_arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:*"
          }
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-github-actions-role"
  }
}

# Policy for GitHub Actions to deploy to ECS
resource "aws_iam_role_policy" "github_actions_deploy" {
  count = var.enable_github_actions_role ? 1 : 0
  name  = "${var.project_name}-${var.environment}-github-actions-deploy-policy"
  role  = aws_iam_role.github_actions[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:DescribeTaskDefinition",
          "ecs:RegisterTaskDefinition",
          "ecs:UpdateService",
          "ecs:DescribeServices"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = [
          aws_iam_role.ecs_task_execution.arn,
          aws_iam_role.ecs_task.arn
        ]
      }
    ]
  })
}
