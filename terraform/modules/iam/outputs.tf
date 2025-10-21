# IAM Module Outputs

# ============================================================================
# ECS Task Execution Role Outputs
# ============================================================================

output "ecs_task_execution_role_arn" {
  description = "ARN of the ECS task execution role"
  value       = aws_iam_role.ecs_task_execution.arn
}

output "ecs_task_execution_role_name" {
  description = "Name of the ECS task execution role"
  value       = aws_iam_role.ecs_task_execution.name
}

output "ecs_task_execution_role_id" {
  description = "ID of the ECS task execution role"
  value       = aws_iam_role.ecs_task_execution.id
}

# ============================================================================
# ECS Task Role Outputs
# ============================================================================

output "ecs_task_role_arn" {
  description = "ARN of the ECS task role"
  value       = aws_iam_role.ecs_task.arn
}

output "ecs_task_role_name" {
  description = "Name of the ECS task role"
  value       = aws_iam_role.ecs_task.name
}

output "ecs_task_role_id" {
  description = "ID of the ECS task role"
  value       = aws_iam_role.ecs_task.id
}

# ============================================================================
# GitHub Actions Role Outputs
# ============================================================================

output "github_actions_role_arn" {
  description = "ARN of the GitHub Actions role"
  value       = var.enable_github_actions_role ? aws_iam_role.github_actions[0].arn : ""
}

output "github_actions_role_name" {
  description = "Name of the GitHub Actions role"
  value       = var.enable_github_actions_role ? aws_iam_role.github_actions[0].name : ""
}
