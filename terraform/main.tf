# Canvas TA Assistant - Main Terraform Configuration
# This file orchestrates all infrastructure modules for the application

locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Repository  = "canvas-ta-assistant"
    Owner       = var.owner_email
  }
}

# ============================================================================
# VPC Module - Networking Infrastructure
# ============================================================================

module "vpc" {
  source = "./modules/vpc"

  project_name         = var.project_name
  environment          = var.environment
  vpc_cidr             = var.vpc_cidr
  public_subnet_count  = var.public_subnet_count
  private_subnet_count = var.private_subnet_count

  # NAT Gateway configuration
  enable_nat_gateway = var.enable_nat_gateway
  single_nat_gateway = var.single_nat_gateway

  # VPC Flow Logs
  enable_flow_logs         = var.enable_vpc_flow_logs
  flow_logs_retention_days = var.flow_logs_retention_days
}

# ============================================================================
# ECR Module - Container Registry
# ============================================================================

module "ecr" {
  source = "./modules/ecr"

  project_name    = var.project_name
  environment     = var.environment
  repository_name = var.ecr_repository_name

  # Image scanning and security
  enable_image_scanning = var.enable_ecr_image_scanning
  image_tag_mutability  = var.ecr_image_tag_mutability
  encryption_type       = var.ecr_encryption_type

  # Lifecycle policy
  enable_lifecycle_policy = var.enable_ecr_lifecycle_policy
  max_image_count         = var.ecr_max_image_count
  untagged_image_days     = var.ecr_untagged_image_days
}

# ============================================================================
# IAM Module - Roles and Policies
# ============================================================================

module "iam" {
  source = "./modules/iam"

  project_name = var.project_name
  environment  = var.environment

  # ECS task execution permissions
  enable_secrets_access = var.enable_secrets_access
  secrets_arns          = var.secrets_arns
  ssm_parameter_arns    = var.ssm_parameter_arns

  # Application permissions
  enable_s3_access          = var.enable_s3_access
  s3_bucket_arns            = var.s3_bucket_arns
  enable_dynamodb_access    = var.enable_dynamodb_access
  dynamodb_table_arns       = var.dynamodb_table_arns
  enable_cloudwatch_metrics = var.enable_cloudwatch_metrics
  enable_ses_access         = var.enable_ses_access

  # GitHub Actions OIDC
  enable_github_actions_role = var.enable_github_actions_role
  github_oidc_provider_arn   = var.github_oidc_provider_arn
  github_repository          = var.github_repository
}

# ============================================================================
# ALB Module - Application Load Balancer
# ============================================================================

module "alb" {
  source = "./modules/alb"

  project_name = var.project_name
  environment  = var.environment
  vpc_id       = module.vpc.vpc_id
  subnet_ids   = module.vpc.public_subnet_ids

  # ALB configuration
  internal                   = var.alb_internal
  enable_deletion_protection = var.alb_enable_deletion_protection
  allowed_cidr_blocks        = var.alb_allowed_cidr_blocks

  # Target group
  target_port     = var.container_port
  target_protocol = "HTTP"
  target_type     = "ip"

  # Health check
  health_check_path              = var.alb_health_check_path
  health_check_interval          = var.alb_health_check_interval
  health_check_timeout           = var.alb_health_check_timeout
  health_check_healthy_threshold = var.alb_health_check_healthy_threshold

  # HTTPS configuration
  enable_https          = var.enable_https
  enable_https_redirect = var.enable_https_redirect
  certificate_arn       = var.certificate_arn
  ssl_policy            = var.ssl_policy

  # Monitoring
  enable_cloudwatch_alarms = var.enable_alb_cloudwatch_alarms
  response_time_threshold  = var.alb_response_time_threshold
  error_5xx_threshold      = var.alb_error_5xx_threshold

  # Access logs
  enable_access_logs = var.enable_alb_access_logs
  access_logs_bucket = var.alb_access_logs_bucket
  access_logs_prefix = var.alb_access_logs_prefix
}

# ============================================================================
# ECS Module - Container Orchestration
# ============================================================================

module "ecs" {
  source = "./modules/ecs"

  project_name       = var.project_name
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids

  # IAM roles
  task_execution_role_arn = module.iam.ecs_task_execution_role_arn
  task_role_arn           = module.iam.ecs_task_role_arn

  # ALB integration
  alb_security_group_id = module.alb.alb_security_group_id
  target_group_arn      = module.alb.target_group_arn
  alb_listener_arn      = module.alb.http_listener_arn

  # Container configuration
  container_name  = var.container_name
  container_image = var.container_image != "" ? var.container_image : "${module.ecr.repository_url}:latest"
  container_port  = var.container_port

  # Environment variables and secrets
  environment_variables = var.environment_variables
  secrets               = var.ecs_secrets

  # Task sizing
  task_cpu    = var.task_cpu
  task_memory = var.task_memory

  # Service configuration
  desired_count                       = var.desired_count
  deployment_minimum_healthy_percent  = var.deployment_minimum_healthy_percent
  deployment_maximum_percent          = var.deployment_maximum_percent
  enable_deployment_circuit_breaker   = var.enable_deployment_circuit_breaker
  enable_deployment_rollback          = var.enable_deployment_rollback

  # Fargate configuration
  enable_fargate_spot   = var.enable_fargate_spot
  fargate_weight        = var.fargate_weight
  fargate_spot_weight   = var.fargate_spot_weight
  fargate_base_capacity = var.fargate_base_capacity

  # Auto scaling
  enable_autoscaling         = var.enable_autoscaling
  autoscaling_min_capacity   = var.autoscaling_min_capacity
  autoscaling_max_capacity   = var.autoscaling_max_capacity
  autoscaling_cpu_target     = var.autoscaling_cpu_target
  autoscaling_memory_target  = var.autoscaling_memory_target
  autoscaling_scale_in_cooldown  = var.autoscaling_scale_in_cooldown
  autoscaling_scale_out_cooldown = var.autoscaling_scale_out_cooldown

  # Health checks
  enable_container_health_check = var.enable_container_health_check
  health_check_command          = var.ecs_health_check_command

  # Monitoring
  enable_container_insights = var.enable_container_insights
  enable_cloudwatch_alarms  = var.enable_ecs_cloudwatch_alarms
  cpu_alarm_threshold       = var.ecs_cpu_alarm_threshold
  memory_alarm_threshold    = var.ecs_memory_alarm_threshold

  # Logging
  log_retention_days = var.log_retention_days

  # Advanced features
  enable_ecs_exec         = var.enable_ecs_exec
  enable_service_discovery = var.enable_service_discovery
  service_discovery_name   = var.service_discovery_name

  depends_on = [module.alb]
}
