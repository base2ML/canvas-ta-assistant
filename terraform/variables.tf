# Variables for Canvas TA Dashboard Infrastructure

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (prod, dev, staging)"
  type        = string
  default     = "prod"
}

variable "canvas_api_url" {
  description = "Canvas LMS API base URL"
  type        = string
  default     = "https://your-institution.instructure.com"
}

variable "canvas_course_id" {
  description = "Canvas course ID to fetch data for"
  type        = string
}

variable "ecr_repository_url" {
  description = "ECR repository URL for the application container"
  type        = string
}

# Optional: Canvas API token (will be stored in Secrets Manager)
variable "canvas_api_token" {
  description = "Canvas API token (sensitive)"
  type        = string
  sensitive   = true
  default     = ""
}