# Canvas TA Assistant - Root Terraform Outputs

# ============================================================================
# VPC Outputs
# ============================================================================

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "vpc_cidr" {
  description = "CIDR block of the VPC"
  value       = module.vpc.vpc_cidr
}

output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = module.vpc.private_subnet_ids
}

# ============================================================================
# ECR Outputs
# ============================================================================

output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = module.ecr.repository_url
}

output "ecr_repository_arn" {
  description = "ARN of the ECR repository"
  value       = module.ecr.repository_arn
}

output "ecr_repository_name" {
  description = "Name of the ECR repository"
  value       = module.ecr.repository_name
}

# ============================================================================
# IAM Outputs
# ============================================================================

output "ecs_task_execution_role_arn" {
  description = "ARN of the ECS task execution role"
  value       = module.iam.ecs_task_execution_role_arn
}

output "ecs_task_role_arn" {
  description = "ARN of the ECS task role"
  value       = module.iam.ecs_task_role_arn
}

output "github_actions_role_arn" {
  description = "ARN of the GitHub Actions role"
  value       = module.iam.github_actions_role_arn
}

# ============================================================================
# ALB Outputs
# ============================================================================

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = module.alb.alb_dns_name
}

output "alb_url" {
  description = "URL of the Application Load Balancer"
  value       = module.alb.alb_url
}

output "alb_zone_id" {
  description = "Zone ID of the ALB (for Route53)"
  value       = module.alb.alb_zone_id
}

output "alb_arn" {
  description = "ARN of the Application Load Balancer"
  value       = module.alb.alb_arn
}

output "target_group_arn" {
  description = "ARN of the target group"
  value       = module.alb.target_group_arn
}

# ============================================================================
# ECS Outputs
# ============================================================================

output "ecs_cluster_id" {
  description = "ID of the ECS cluster"
  value       = module.ecs.cluster_id
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = module.ecs.cluster_name
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = module.ecs.service_name
}

output "ecs_task_definition_arn" {
  description = "ARN of the task definition"
  value       = module.ecs.task_definition_arn
}

output "ecs_log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = module.ecs.log_group_name
}

# ============================================================================
# Deployment Information
# ============================================================================

output "deployment_instructions" {
  description = "Instructions for deploying the application"
  value = <<-EOT

    ====================================================================
    Canvas TA Assistant - Deployment Information
    ====================================================================

    Application URL: ${module.alb.alb_url}

    ECR Repository: ${module.ecr.repository_url}

    ECS Cluster: ${module.ecs.cluster_name}
    ECS Service: ${module.ecs.service_name}

    CloudWatch Logs: ${module.ecs.log_group_name}

    ====================================================================
    Next Steps:
    ====================================================================

    1. Build and push Docker image:

       aws ecr get-login-password --region ${var.aws_region} | \
         docker login --username AWS --password-stdin ${module.ecr.repository_url}

       docker build -t ${module.ecr.repository_url}:latest .
       docker push ${module.ecr.repository_url}:latest

    2. Update ECS service to use new image:

       aws ecs update-service \
         --cluster ${module.ecs.cluster_name} \
         --service ${module.ecs.service_name} \
         --force-new-deployment

    3. View logs:

       aws logs tail ${module.ecs.log_group_name} --follow

    4. Monitor deployment:

       aws ecs describe-services \
         --cluster ${module.ecs.cluster_name} \
         --services ${module.ecs.service_name}

    ====================================================================

  EOT
}
