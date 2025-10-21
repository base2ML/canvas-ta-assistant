# ECR Module Variables

variable "project_name" {
  description = "Name of the project, used for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

variable "repository_name" {
  description = "Name of the ECR repository"
  type        = string
  default     = "app"
}

variable "image_tag_mutability" {
  description = "Image tag mutability setting (MUTABLE or IMMUTABLE)"
  type        = string
  default     = "MUTABLE"

  validation {
    condition     = contains(["MUTABLE", "IMMUTABLE"], var.image_tag_mutability)
    error_message = "Image tag mutability must be either MUTABLE or IMMUTABLE."
  }
}

variable "enable_image_scanning" {
  description = "Enable image scanning on push"
  type        = bool
  default     = true
}

variable "encryption_type" {
  description = "Encryption type for images (AES256 or KMS)"
  type        = string
  default     = "AES256"

  validation {
    condition     = contains(["AES256", "KMS"], var.encryption_type)
    error_message = "Encryption type must be either AES256 or KMS."
  }
}

variable "kms_key_arn" {
  description = "ARN of KMS key for encryption (required if encryption_type is KMS)"
  type        = string
  default     = null
}

variable "enable_lifecycle_policy" {
  description = "Enable lifecycle policy for image retention"
  type        = bool
  default     = true
}

variable "max_image_count" {
  description = "Maximum number of images to keep in the repository"
  type        = number
  default     = 30

  validation {
    condition     = var.max_image_count > 0 && var.max_image_count <= 1000
    error_message = "Max image count must be between 1 and 1000."
  }
}

variable "untagged_image_days" {
  description = "Number of days to keep untagged images"
  type        = number
  default     = 7

  validation {
    condition     = var.untagged_image_days >= 1
    error_message = "Untagged image retention must be at least 1 day."
  }
}

variable "enable_cross_account_access" {
  description = "Enable cross-account access to ECR repository"
  type        = bool
  default     = false
}

variable "allowed_account_ids" {
  description = "List of AWS account IDs allowed to access the repository"
  type        = list(string)
  default     = []
}

variable "enable_scanning_logs" {
  description = "Enable CloudWatch logs for image scanning results"
  type        = bool
  default     = false
}

variable "scanning_logs_retention_days" {
  description = "CloudWatch log retention for scanning results"
  type        = number
  default     = 30

  validation {
    condition     = contains([0, 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.scanning_logs_retention_days)
    error_message = "Scanning logs retention must be a valid CloudWatch Logs retention period."
  }
}
