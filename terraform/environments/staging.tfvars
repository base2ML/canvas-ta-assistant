# Staging Environment Configuration

environment = "staging"

# VPC - Balanced configuration
single_nat_gateway       = true  # Single NAT for cost savings
enable_vpc_flow_logs     = true
flow_logs_retention_days = 14

# ECR - Moderate retention
ecr_max_image_count     = 20
ecr_untagged_image_days = 5

# ALB - Standard configuration
alb_enable_deletion_protection = false
enable_https                   = true  # Use HTTPS in staging
enable_https_redirect          = true
enable_alb_cloudwatch_alarms   = true
enable_alb_access_logs         = false

# ECS - Moderate resources
task_cpu    = 512   # 0.5 vCPU
task_memory = 1024  # 1 GB

desired_count = 2

# Fargate Spot for cost savings
enable_fargate_spot   = true
fargate_weight        = 1
fargate_spot_weight   = 1
fargate_base_capacity = 1

# Auto scaling - Enabled but conservative
enable_autoscaling       = true
autoscaling_min_capacity = 1
autoscaling_max_capacity = 5

# Monitoring - Enabled
enable_container_insights    = true
enable_ecs_cloudwatch_alarms = true
log_retention_days           = 14

# Environment variables
environment_variables = {
  ENVIRONMENT = "staging"
  LOG_LEVEL   = "INFO"
  PORT        = "8000"
}

# Disable ECS Exec in staging
enable_ecs_exec = false
