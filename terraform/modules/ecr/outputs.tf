# ECR Module Outputs

output "repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.main.repository_url
}

output "repository_arn" {
  description = "ARN of the ECR repository"
  value       = aws_ecr_repository.main.arn
}

output "repository_name" {
  description = "Name of the ECR repository"
  value       = aws_ecr_repository.main.name
}

output "registry_id" {
  description = "Registry ID where the repository is created"
  value       = aws_ecr_repository.main.registry_id
}

output "repository_registry_url" {
  description = "The registry URL for pulling/pushing images"
  value       = "${aws_ecr_repository.main.registry_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com"
}

data "aws_region" "current" {}
