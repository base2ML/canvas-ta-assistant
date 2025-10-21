# Development Environment Configuration

environment = "dev"

# VPC - Cost optimized
single_nat_gateway       = true  # Single NAT for cost savings
enable_vpc_flow_logs     = false # Disable flow logs in dev
flow_logs_retention_days = 7

# ECR - Reduced retention
ecr_max_image_count     = 10
ecr_untagged_image_days = 3

# ALB - Basic configuration
alb_enable_deletion_protection = false
enable_https                   = false
enable_https_redirect          = false
enable_alb_cloudwatch_alarms   = false
enable_alb_access_logs         = false

# ECS - Minimal resources
task_cpu    = 256  # 0.25 vCPU
task_memory = 512  # 512 MB

desired_count = 1

# Fargate Spot for 70% cost savings in dev
enable_fargate_spot   = true
fargate_weight        = 1
fargate_spot_weight   = 3
fargate_base_capacity = 0

# Auto scaling - Disabled in dev
enable_autoscaling       = false
autoscaling_min_capacity = 1
autoscaling_max_capacity = 3

# Monitoring - Reduced in dev
enable_container_insights    = false
enable_ecs_cloudwatch_alarms = false
log_retention_days           = 7

# Environment variables
environment_variables = {
  ENVIRONMENT = "dev"
  LOG_LEVEL   = "DEBUG"
  PORT        = "8000"
}

# Enable ECS Exec for debugging
enable_ecs_exec = true
