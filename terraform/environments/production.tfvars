# Production Environment Configuration

environment = "production"

# VPC - High availability
single_nat_gateway       = false  # NAT per AZ for redundancy
enable_vpc_flow_logs     = true
flow_logs_retention_days = 30

# ECR - Extended retention
ecr_max_image_count     = 30
ecr_untagged_image_days = 7

# ALB - Production configuration
alb_enable_deletion_protection = true  # Prevent accidental deletion
enable_https                   = true  # Always use HTTPS
enable_https_redirect          = true
enable_alb_cloudwatch_alarms   = true
enable_alb_access_logs         = true  # Enable access logs

# ECS - Production resources
task_cpu    = 512   # 0.5 vCPU (adjust based on load)
task_memory = 1024  # 1 GB (adjust based on load)

desired_count = 3  # High availability

# Regular Fargate (no Spot in production for reliability)
enable_fargate_spot   = false
fargate_weight        = 100
fargate_spot_weight   = 0
fargate_base_capacity = 3

# Auto scaling - Aggressive
enable_autoscaling       = true
autoscaling_min_capacity = 2
autoscaling_max_capacity = 20
autoscaling_cpu_target   = 70
autoscaling_memory_target = 80

# Monitoring - Full monitoring
enable_container_insights    = true
enable_ecs_cloudwatch_alarms = true
log_retention_days           = 30

# Deployment - Conservative
deployment_minimum_healthy_percent = 100
deployment_maximum_percent         = 200
enable_deployment_circuit_breaker  = true
enable_deployment_rollback         = true

# Environment variables
environment_variables = {
  ENVIRONMENT = "production"
  LOG_LEVEL   = "INFO"
  PORT        = "8000"
}

# Disable ECS Exec in production for security
enable_ecs_exec = false
