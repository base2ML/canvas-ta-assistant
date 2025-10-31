# Canvas TA Dashboard Infrastructure
# Complete infrastructure for user authentication, data pipeline, and dashboard

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Local values for resource naming
locals {
  project_name = "canvas-ta-dashboard"
  environment  = var.environment

  common_tags = {
    Project     = local.project_name
    Environment = local.environment
    ManagedBy   = "terraform"
  }
}

# Note: Cognito has been removed - now using simple JWT authentication
# User management is handled via S3-stored user file (auth/users.json)

# S3 Bucket for Canvas Data Storage
module "s3" {
  source = "./modules/s3"

  project_name = local.project_name
  environment  = local.environment

  # Bucket configuration
  enable_versioning = true
  enable_encryption = true

  # Lifecycle rules for cost optimization
  lifecycle_rules = [
    {
      id     = "canvas_data_lifecycle"
      status = "Enabled"

      transitions = [
        {
          days          = 30
          storage_class = "STANDARD_IA"
        },
        {
          days          = 90
          storage_class = "GLACIER"
        }
      ]

      expiration = {
        days = 365
      }
    }
  ]

  tags = local.common_tags
}

# Lambda Function for Canvas API Data Fetching
module "lambda" {
  source = "./modules/lambda"

  project_name = local.project_name
  environment  = local.environment

  # Function configuration
  function_name = "canvas-data-fetcher"
  runtime       = "python3.11"
  timeout       = 900  # 15 minutes max execution time
  memory_size   = 512

  # Environment variables
  environment_variables = {
    S3_BUCKET_NAME    = module.s3.bucket_name
    CANVAS_API_URL    = var.canvas_api_url
    CANVAS_COURSE_ID  = var.canvas_course_id
    ENVIRONMENT       = local.environment
  }

  # IAM permissions
  s3_bucket_arn = module.s3.bucket_arn

  tags = local.common_tags
}

# EventBridge for Lambda Scheduling
module "eventbridge" {
  source = "./modules/eventbridge"

  project_name = local.project_name
  environment  = local.environment

  # Schedule: every 15 minutes
  schedule_expression = "rate(15 minutes)"

  # Lambda function ARN
  lambda_function_arn = module.lambda.function_arn
  lambda_function_name = module.lambda.function_name

  tags = local.common_tags
}

# ECS Infrastructure for Dashboard
module "ecs" {
  source = "./modules/ecs"

  project_name = local.project_name
  environment  = local.environment

  # VPC Configuration
  vpc_cidr = "10.0.0.0/16"
  availability_zones = ["${var.aws_region}a", "${var.aws_region}b"]

  # ECS Configuration
  container_image = "${var.ecr_repository_url}:latest"
  container_port  = 8000
  cpu             = 512
  memory          = 1024
  desired_count   = 2

  # Environment variables for ECS container
  container_environment = [
    {
      name  = "ENVIRONMENT"
      value = local.environment
    },
    {
      name  = "S3_BUCKET_NAME"
      value = module.s3.bucket_name
    },
    {
      name  = "AWS_REGION"
      value = var.aws_region
    },
    {
      name  = "JWT_SECRET_KEY"
      value = var.jwt_secret_key
    }
  ]

  # IAM permissions for ECS tasks
  s3_bucket_arn = module.s3.bucket_arn

  tags = local.common_tags
}