# Terraform Backend Configuration
# This configuration stores Terraform state in S3 with DynamoDB locking
#
# IMPORTANT: Before using this backend, you must:
# 1. Create an S3 bucket for state storage
# 2. Create a DynamoDB table for state locking
# 3. Update the bucket, key, and dynamodb_table values below
#
# To create the backend resources, run:
# aws s3api create-bucket --bucket canvas-ta-terraform-state --region us-east-1
# aws dynamodb create-table --table-name canvas-ta-terraform-locks \
#   --attribute-definitions AttributeName=LockID,AttributeType=S \
#   --key-schema AttributeName=LockID,KeyType=HASH \
#   --billing-mode PAY_PER_REQUEST --region us-east-1

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment after creating the S3 bucket and DynamoDB table
  # backend "s3" {
  #   bucket         = "canvas-ta-terraform-state"
  #   key            = "canvas-ta-assistant/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "canvas-ta-terraform-locks"
  #
  #   # Optional: Enable versioning for state file protection
  #   # versioning    = true
  # }
}

# AWS Provider Configuration
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Repository  = "canvas-ta-assistant"
    }
  }
}
