# ECS Module Variables

variable "project_name" {
  description = "Name of the project, used for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where ECS resources will be created"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for ECS tasks"
  type        = list(string)
}

# ============================================================================
# IAM Role Variables
# ============================================================================

variable "task_execution_role_arn" {
  description = "ARN of the task execution role"
  type        = string
}

variable "task_role_arn" {
  description = "ARN of the task role"
  type        = string
}

# ============================================================================
# ALB Variables
# ============================================================================

variable "alb_security_group_id" {
  description = "Security group ID of the Application Load Balancer"
  type        = string
}

variable "target_group_arn" {
  description = "ARN of the target group"
  type        = string
}

variable "alb_listener_arn" {
  description = "ARN of the ALB listener (for dependency)"
  type        = string
}

# ============================================================================
# Container Configuration
# ============================================================================

variable "container_name" {
  description = "Name of the container"
  type        = string
  default     = "app"
}

variable "container_image" {
  description = "Docker image to run (will be overridden by CI/CD)"
  type        = string
  default     = "nginx:latest"
}

variable "container_port" {
  description = "Port exposed by the container"
  type        = number
  default     = 8000
}

variable "environment_variables" {
  description = "Environment variables for the container"
  type        = map(string)
  default     = {}
}

variable "secrets" {
  description = "Secrets from Secrets Manager or SSM Parameter Store"
  type        = map(string)
  default     = {}
}

# ============================================================================
# Task Definition Configuration
# ============================================================================

variable "task_cpu" {
  description = "Fargate task CPU units (256, 512, 1024, 2048, 4096)"
  type        = number
  default     = 512

  validation {
    condition     = contains([256, 512, 1024, 2048, 4096, 8192, 16384], var.task_cpu)
    error_message = "Task CPU must be a valid Fargate CPU value."
  }
}

variable "task_memory" {
  description = "Fargate task memory in MB (512, 1024, 2048, etc.)"
  type        = number
  default     = 1024

  validation {
    condition     = var.task_memory >= 512 && var.task_memory <= 30720
    error_message = "Task memory must be between 512 MB and 30720 MB."
  }
}

# ============================================================================
# ECS Service Configuration
# ============================================================================

variable "desired_count" {
  description = "Desired number of tasks"
  type        = number
  default     = 2

  validation {
    condition     = var.desired_count >= 0
    error_message = "Desired count must be a non-negative integer."
  }
}

variable "assign_public_ip" {
  description = "Assign public IP to tasks (required if using public subnets without NAT)"
  type        = bool
  default     = false
}

variable "deployment_maximum_percent" {
  description = "Maximum percentage of tasks during deployment"
  type        = number
  default     = 200

  validation {
    condition     = var.deployment_maximum_percent >= 100 && var.deployment_maximum_percent <= 200
    error_message = "Deployment maximum percent must be between 100 and 200."
  }
}

variable "deployment_minimum_healthy_percent" {
  description = "Minimum healthy percentage during deployment"
  type        = number
  default     = 100

  validation {
    condition     = var.deployment_minimum_healthy_percent >= 0 && var.deployment_minimum_healthy_percent <= 100
    error_message = "Deployment minimum healthy percent must be between 0 and 100."
  }
}

variable "enable_deployment_circuit_breaker" {
  description = "Enable deployment circuit breaker"
  type        = bool
  default     = true
}

variable "enable_deployment_rollback" {
  description = "Enable automatic rollback on deployment failure"
  type        = bool
  default     = true
}

variable "deployment_controller_type" {
  description = "Deployment controller type (ECS, CODE_DEPLOY, EXTERNAL)"
  type        = string
  default     = "ECS"

  validation {
    condition     = contains(["ECS", "CODE_DEPLOY", "EXTERNAL"], var.deployment_controller_type)
    error_message = "Deployment controller type must be ECS, CODE_DEPLOY, or EXTERNAL."
  }
}

# ============================================================================
# Fargate Configuration
# ============================================================================

variable "enable_fargate_spot" {
  description = "Enable Fargate Spot for cost savings"
  type        = bool
  default     = false
}

variable "fargate_weight" {
  description = "Weight for Fargate capacity provider"
  type        = number
  default     = 100
}

variable "fargate_spot_weight" {
  description = "Weight for Fargate Spot capacity provider"
  type        = number
  default     = 0
}

variable "fargate_base_capacity" {
  description = "Base capacity for Fargate"
  type        = number
  default     = 1
}

# ============================================================================
# Auto Scaling Configuration
# ============================================================================

variable "enable_autoscaling" {
  description = "Enable auto-scaling for ECS service"
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
  description = "Target CPU utilization for auto-scaling"
  type        = number
  default     = 70

  validation {
    condition     = var.autoscaling_cpu_target > 0 && var.autoscaling_cpu_target <= 100
    error_message = "CPU target must be between 1 and 100."
  }
}

variable "autoscaling_memory_target" {
  description = "Target memory utilization for auto-scaling"
  type        = number
  default     = 80

  validation {
    condition     = var.autoscaling_memory_target > 0 && var.autoscaling_memory_target <= 100
    error_message = "Memory target must be between 1 and 100."
  }
}

variable "autoscaling_scale_in_cooldown" {
  description = "Cooldown period for scale-in (seconds)"
  type        = number
  default     = 300
}

variable "autoscaling_scale_out_cooldown" {
  description = "Cooldown period for scale-out (seconds)"
  type        = number
  default     = 60
}

# ============================================================================
# Health Check Configuration
# ============================================================================

variable "enable_container_health_check" {
  description = "Enable container health check"
  type        = bool
  default     = true
}

variable "health_check_command" {
  description = "Health check command"
  type        = list(string)
  default     = ["CMD-SHELL", "curl -f http://localhost:8000/api/health || exit 1"]
}

variable "health_check_interval" {
  description = "Health check interval (seconds)"
  type        = number
  default     = 30
}

variable "health_check_timeout" {
  description = "Health check timeout (seconds)"
  type        = number
  default     = 5
}

variable "health_check_retries" {
  description = "Health check retries"
  type        = number
  default     = 3
}

variable "health_check_start_period" {
  description = "Health check start period (seconds)"
  type        = number
  default     = 60
}

# ============================================================================
# Logging Configuration
# ============================================================================

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30

  validation {
    condition     = contains([0, 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "Log retention must be a valid CloudWatch Logs retention period."
  }
}

# ============================================================================
# Monitoring Configuration
# ============================================================================

variable "enable_container_insights" {
  description = "Enable Container Insights for enhanced monitoring"
  type        = bool
  default     = true
}

variable "enable_cloudwatch_alarms" {
  description = "Enable CloudWatch alarms"
  type        = bool
  default     = true
}

variable "cpu_alarm_threshold" {
  description = "CPU utilization threshold for alarm"
  type        = number
  default     = 85
}

variable "memory_alarm_threshold" {
  description = "Memory utilization threshold for alarm"
  type        = number
  default     = 85
}

# ============================================================================
# Advanced Features
# ============================================================================

variable "enable_ecs_exec" {
  description = "Enable ECS Exec for debugging"
  type        = bool
  default     = false
}

variable "enable_service_discovery" {
  description = "Enable AWS Cloud Map service discovery"
  type        = bool
  default     = false
}

variable "service_discovery_name" {
  description = "Service discovery service name"
  type        = string
  default     = "app"
}
