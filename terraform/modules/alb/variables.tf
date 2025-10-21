# ALB Module Variables

variable "project_name" {
  description = "Name of the project, used for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where the ALB will be created"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for the ALB (must be in at least 2 AZs)"
  type        = list(string)

  validation {
    condition     = length(var.subnet_ids) >= 2
    error_message = "ALB requires at least 2 subnets in different availability zones."
  }
}

# ============================================================================
# ALB Configuration
# ============================================================================

variable "internal" {
  description = "Whether the load balancer is internal or internet-facing"
  type        = bool
  default     = false
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection for the load balancer"
  type        = bool
  default     = false
}

variable "enable_http2" {
  description = "Enable HTTP/2 protocol"
  type        = bool
  default     = true
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the ALB"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "enable_access_logs" {
  description = "Enable access logs for the ALB"
  type        = bool
  default     = false
}

variable "access_logs_bucket" {
  description = "S3 bucket for ALB access logs (required if enable_access_logs is true)"
  type        = string
  default     = ""
}

variable "access_logs_prefix" {
  description = "S3 prefix for ALB access logs"
  type        = string
  default     = "alb-logs"
}

# ============================================================================
# Target Group Configuration
# ============================================================================

variable "target_port" {
  description = "Port on which targets receive traffic"
  type        = number
  default     = 8000
}

variable "target_protocol" {
  description = "Protocol to use for routing traffic to targets"
  type        = string
  default     = "HTTP"

  validation {
    condition     = contains(["HTTP", "HTTPS"], var.target_protocol)
    error_message = "Target protocol must be HTTP or HTTPS."
  }
}

variable "target_type" {
  description = "Type of target (instance, ip, or lambda)"
  type        = string
  default     = "ip"

  validation {
    condition     = contains(["instance", "ip", "lambda"], var.target_type)
    error_message = "Target type must be instance, ip, or lambda."
  }
}

variable "deregistration_delay" {
  description = "Time to wait before deregistering a target"
  type        = number
  default     = 30

  validation {
    condition     = var.deregistration_delay >= 0 && var.deregistration_delay <= 3600
    error_message = "Deregistration delay must be between 0 and 3600 seconds."
  }
}

# ============================================================================
# Health Check Configuration
# ============================================================================

variable "health_check_path" {
  description = "Path for health check requests"
  type        = string
  default     = "/api/health"
}

variable "health_check_protocol" {
  description = "Protocol for health checks"
  type        = string
  default     = "HTTP"

  validation {
    condition     = contains(["HTTP", "HTTPS"], var.health_check_protocol)
    error_message = "Health check protocol must be HTTP or HTTPS."
  }
}

variable "health_check_matcher" {
  description = "HTTP codes to use when checking for a successful response"
  type        = string
  default     = "200"
}

variable "health_check_interval" {
  description = "Interval between health checks (seconds)"
  type        = number
  default     = 30

  validation {
    condition     = var.health_check_interval >= 5 && var.health_check_interval <= 300
    error_message = "Health check interval must be between 5 and 300 seconds."
  }
}

variable "health_check_timeout" {
  description = "Timeout for health check requests (seconds)"
  type        = number
  default     = 5

  validation {
    condition     = var.health_check_timeout >= 2 && var.health_check_timeout <= 120
    error_message = "Health check timeout must be between 2 and 120 seconds."
  }
}

variable "health_check_healthy_threshold" {
  description = "Number of consecutive successful health checks required"
  type        = number
  default     = 2

  validation {
    condition     = var.health_check_healthy_threshold >= 2 && var.health_check_healthy_threshold <= 10
    error_message = "Healthy threshold must be between 2 and 10."
  }
}

variable "health_check_unhealthy_threshold" {
  description = "Number of consecutive failed health checks required"
  type        = number
  default     = 3

  validation {
    condition     = var.health_check_unhealthy_threshold >= 2 && var.health_check_unhealthy_threshold <= 10
    error_message = "Unhealthy threshold must be between 2 and 10."
  }
}

# ============================================================================
# HTTPS Configuration
# ============================================================================

variable "enable_https" {
  description = "Enable HTTPS listener"
  type        = bool
  default     = false
}

variable "enable_https_redirect" {
  description = "Redirect HTTP traffic to HTTPS"
  type        = bool
  default     = false
}

variable "certificate_arn" {
  description = "ARN of ACM certificate for HTTPS (required if enable_https is true)"
  type        = string
  default     = ""
}

variable "ssl_policy" {
  description = "SSL policy for HTTPS listener"
  type        = string
  default     = "ELBSecurityPolicy-TLS13-1-2-2021-06"
}

# ============================================================================
# Stickiness Configuration
# ============================================================================

variable "enable_stickiness" {
  description = "Enable session stickiness (session affinity)"
  type        = bool
  default     = false
}

variable "stickiness_duration" {
  description = "Duration of stickiness in seconds"
  type        = number
  default     = 86400

  validation {
    condition     = var.stickiness_duration >= 1 && var.stickiness_duration <= 604800
    error_message = "Stickiness duration must be between 1 and 604800 seconds (7 days)."
  }
}

# ============================================================================
# CloudWatch Alarms
# ============================================================================

variable "enable_cloudwatch_alarms" {
  description = "Enable CloudWatch alarms for ALB monitoring"
  type        = bool
  default     = true
}

variable "response_time_threshold" {
  description = "Threshold for target response time alarm (seconds)"
  type        = number
  default     = 1.0
}

variable "error_5xx_threshold" {
  description = "Threshold for 5xx error count alarm"
  type        = number
  default     = 10
}
