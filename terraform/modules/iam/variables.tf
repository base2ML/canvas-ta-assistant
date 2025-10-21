# IAM Module Variables

variable "project_name" {
  description = "Name of the project, used for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

# ============================================================================
# ECS Task Execution Role Variables
# ============================================================================

variable "enable_secrets_access" {
  description = "Enable access to AWS Secrets Manager and SSM Parameter Store"
  type        = bool
  default     = false
}

variable "secrets_arns" {
  description = "List of Secrets Manager secret ARNs the task can access"
  type        = list(string)
  default     = []
}

variable "ssm_parameter_arns" {
  description = "List of SSM Parameter Store ARNs the task can access"
  type        = list(string)
  default     = []
}

# ============================================================================
# ECS Task Role Variables
# ============================================================================

variable "enable_s3_access" {
  description = "Enable S3 access for the application"
  type        = bool
  default     = false
}

variable "s3_bucket_arns" {
  description = "List of S3 bucket ARNs the application can access"
  type        = list(string)
  default     = []
}

variable "enable_dynamodb_access" {
  description = "Enable DynamoDB access for the application"
  type        = bool
  default     = false
}

variable "dynamodb_table_arns" {
  description = "List of DynamoDB table ARNs the application can access"
  type        = list(string)
  default     = []
}

variable "enable_cloudwatch_metrics" {
  description = "Enable CloudWatch metrics publishing"
  type        = bool
  default     = true
}

variable "enable_ses_access" {
  description = "Enable SES access for sending emails"
  type        = bool
  default     = false
}

variable "custom_task_policy" {
  description = "Custom IAM policy JSON for additional task permissions"
  type        = string
  default     = ""
}

# ============================================================================
# GitHub Actions Role Variables
# ============================================================================

variable "enable_github_actions_role" {
  description = "Create IAM role for GitHub Actions OIDC authentication"
  type        = bool
  default     = false
}

variable "github_oidc_provider_arn" {
  description = "ARN of the GitHub OIDC provider (required if enable_github_actions_role is true)"
  type        = string
  default     = ""
}

variable "github_repository" {
  description = "GitHub repository in format 'owner/repo' (required if enable_github_actions_role is true)"
  type        = string
  default     = ""
}
