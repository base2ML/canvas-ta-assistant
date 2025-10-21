# Canvas TA Assistant - Root Terraform Variables

# ============================================================================
# General Configuration
# ============================================================================

variable "aws_region" {
  description = "AWS region where resources will be created"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name of the project, used for resource naming"
  type        = string
  default     = "canvas-ta"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be dev, staging, or production."
  }
}

variable "owner_email" {
  description = "Email of the resource owner for tagging"
  type        = string
  default     = ""
}

# ============================================================================
# VPC Module Variables
# ============================================================================

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_count" {
  description = "Number of public subnets to create"
  type        = number
  default     = 2
}

variable "private_subnet_count" {
  description = "Number of private subnets to create"
  type        = number
  default     = 2
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnets"
  type        = bool
  default     = true
}

variable "single_nat_gateway" {
  description = "Use a single NAT Gateway (cost optimization)"
  type        = bool
  default     = false
}

variable "enable_vpc_flow_logs" {
  description = "Enable VPC Flow Logs"
  type        = bool
  default     = true
}

variable "flow_logs_retention_days" {
  description = "CloudWatch log retention for VPC Flow Logs"
  type        = number
  default     = 30
}

# ============================================================================
# ECR Module Variables
# ============================================================================

variable "ecr_repository_name" {
  description = "Name of the ECR repository"
  type        = string
  default     = "cda-ta-dashboard"
}

variable "enable_ecr_image_scanning" {
  description = "Enable image scanning on push"
  type        = bool
  default     = true
}

variable "ecr_image_tag_mutability" {
  description = "Image tag mutability (MUTABLE or IMMUTABLE)"
  type        = string
  default     = "MUTABLE"
}

variable "ecr_encryption_type" {
  description = "Encryption type for ECR (AES256 or KMS)"
  type        = string
  default     = "AES256"
}

variable "enable_ecr_lifecycle_policy" {
  description = "Enable lifecycle policy for image retention"
  type        = bool
  default     = true
}

variable "ecr_max_image_count" {
  description = "Maximum number of images to keep"
  type        = number
  default     = 30
}

variable "ecr_untagged_image_days" {
  description = "Days to keep untagged images"
  type        = number
  default     = 7
}

# ============================================================================
# IAM Module Variables
# ============================================================================

variable "enable_secrets_access" {
  description = "Enable access to Secrets Manager and SSM"
  type        = bool
  default     = false
}

variable "secrets_arns" {
  description = "List of Secrets Manager ARNs"
  type        = list(string)
  default     = []
}

variable "ssm_parameter_arns" {
  description = "List of SSM Parameter Store ARNs"
  type        = list(string)
  default     = []
}

variable "enable_s3_access" {
  description = "Enable S3 access for application"
  type        = bool
  default     = false
}

variable "s3_bucket_arns" {
  description = "List of S3 bucket ARNs"
  type        = list(string)
  default     = []
}

variable "enable_dynamodb_access" {
  description = "Enable DynamoDB access"
  type        = bool
  default     = false
}

variable "dynamodb_table_arns" {
  description = "List of DynamoDB table ARNs"
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

variable "enable_github_actions_role" {
  description = "Create IAM role for GitHub Actions"
  type        = bool
  default     = false
}

variable "github_oidc_provider_arn" {
  description = "ARN of GitHub OIDC provider"
  type        = string
  default     = ""
}

variable "github_repository" {
  description = "GitHub repository (owner/repo)"
  type        = string
  default     = "base2ML/canvas-ta-assistant"
}

# ============================================================================
# ALB Module Variables
# ============================================================================

variable "alb_internal" {
  description = "Whether ALB is internal"
  type        = bool
  default     = false
}

variable "alb_enable_deletion_protection" {
  description = "Enable deletion protection for ALB"
  type        = bool
  default     = false
}

variable "alb_allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access ALB"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "alb_health_check_path" {
  description = "Health check path"
  type        = string
  default     = "/api/health"
}

variable "alb_health_check_interval" {
  description = "Health check interval (seconds)"
  type        = number
  default     = 30
}

variable "alb_health_check_timeout" {
  description = "Health check timeout (seconds)"
  type        = number
  default     = 5
}

variable "alb_health_check_healthy_threshold" {
  description = "Healthy threshold count"
  type        = number
  default     = 2
}

variable "enable_https" {
  description = "Enable HTTPS listener"
  type        = bool
  default     = false
}

variable "enable_https_redirect" {
  description = "Redirect HTTP to HTTPS"
  type        = bool
  default     = false
}

variable "certificate_arn" {
  description = "ARN of ACM certificate"
  type        = string
  default     = ""
}

variable "ssl_policy" {
  description = "SSL policy for HTTPS"
  type        = string
  default     = "ELBSecurityPolicy-TLS13-1-2-2021-06"
}

variable "enable_alb_cloudwatch_alarms" {
  description = "Enable CloudWatch alarms for ALB"
  type        = bool
  default     = true
}

variable "alb_response_time_threshold" {
  description = "Response time threshold (seconds)"
  type        = number
  default     = 1.0
}

variable "alb_error_5xx_threshold" {
  description = "5xx error threshold"
  type        = number
  default     = 10
}

variable "enable_alb_access_logs" {
  description = "Enable ALB access logs"
  type        = bool
  default     = false
}

variable "alb_access_logs_bucket" {
  description = "S3 bucket for ALB access logs"
  type        = string
  default     = ""
}

variable "alb_access_logs_prefix" {
  description = "S3 prefix for ALB access logs"
  type        = string
  default     = "alb-logs"
}

# ============================================================================
# ECS Module Variables
# ============================================================================

variable "container_name" {
  description = "Name of the container"
  type        = string
  default     = "app"
}

variable "container_image" {
  description = "Docker image (defaults to ECR repository)"
  type        = string
  default     = ""
}

variable "container_port" {
  description = "Port exposed by container"
  type        = number
  default     = 8000
}

variable "environment_variables" {
  description = "Environment variables for container"
  type        = map(string)
  default     = {}
}

variable "ecs_secrets" {
  description = "Secrets from Secrets Manager or SSM"
  type        = map(string)
  default     = {}
}

variable "task_cpu" {
  description = "Fargate task CPU units"
  type        = number
  default     = 512
}

variable "task_memory" {
  description = "Fargate task memory (MB)"
  type        = number
  default     = 1024
}

variable "desired_count" {
  description = "Desired number of tasks"
  type        = number
  default     = 2
}

variable "deployment_minimum_healthy_percent" {
  description = "Minimum healthy percent during deployment"
  type        = number
  default     = 100
}

variable "deployment_maximum_percent" {
  description = "Maximum percent during deployment"
  type        = number
  default     = 200
}

variable "enable_deployment_circuit_breaker" {
  description = "Enable deployment circuit breaker"
  type        = bool
  default     = true
}

variable "enable_deployment_rollback" {
  description = "Enable automatic rollback"
  type        = bool
  default     = true
}

variable "enable_fargate_spot" {
  description = "Enable Fargate Spot"
  type        = bool
  default     = false
}

variable "fargate_weight" {
  description = "Weight for Fargate capacity provider"
  type        = number
  default     = 100
}

variable "fargate_spot_weight" {
  description = "Weight for Fargate Spot"
  type        = number
  default     = 0
}

variable "fargate_base_capacity" {
  description = "Base capacity for Fargate"
  type        = number
  default     = 1
}

variable "enable_autoscaling" {
  description = "Enable auto-scaling"
  type        = bool
  default     = true
}

variable "autoscaling_min_capacity" {
  description = "Minimum number of tasks"
  type        = number
  default     = 1
}

variable "autoscaling_max_capacity" {
  description = "Maximum number of tasks"
  type        = number
  default     = 10
}

variable "autoscaling_cpu_target" {
  description = "Target CPU utilization"
  type        = number
  default     = 70
}

variable "autoscaling_memory_target" {
  description = "Target memory utilization"
  type        = number
  default     = 80
}

variable "autoscaling_scale_in_cooldown" {
  description = "Scale-in cooldown (seconds)"
  type        = number
  default     = 300
}

variable "autoscaling_scale_out_cooldown" {
  description = "Scale-out cooldown (seconds)"
  type        = number
  default     = 60
}

variable "enable_container_health_check" {
  description = "Enable container health check"
  type        = bool
  default     = true
}

variable "ecs_health_check_command" {
  description = "Health check command"
  type        = list(string)
  default     = ["CMD-SHELL", "curl -f http://localhost:8000/api/health || exit 1"]
}

variable "enable_container_insights" {
  description = "Enable Container Insights"
  type        = bool
  default     = true
}

variable "enable_ecs_cloudwatch_alarms" {
  description = "Enable CloudWatch alarms for ECS"
  type        = bool
  default     = true
}

variable "ecs_cpu_alarm_threshold" {
  description = "CPU alarm threshold"
  type        = number
  default     = 85
}

variable "ecs_memory_alarm_threshold" {
  description = "Memory alarm threshold"
  type        = number
  default     = 85
}

variable "log_retention_days" {
  description = "CloudWatch log retention days"
  type        = number
  default     = 30
}

variable "enable_ecs_exec" {
  description = "Enable ECS Exec"
  type        = bool
  default     = false
}

variable "enable_service_discovery" {
  description = "Enable service discovery"
  type        = bool
  default     = false
}

variable "service_discovery_name" {
  description = "Service discovery name"
  type        = string
  default     = "app"
}
