# Outputs for Canvas TA Dashboard Infrastructure

output "application_url" {
  description = "URL of the application load balancer"
  value       = module.ecs.load_balancer_dns_name
}

# Cognito outputs removed - now using simple JWT authentication

output "s3_bucket_name" {
  description = "S3 bucket name for Canvas data"
  value       = module.s3.bucket_name
}

output "lambda_function_name" {
  description = "Lambda function name for Canvas data fetcher"
  value       = module.lambda.function_name
}

output "eventbridge_rule_name" {
  description = "EventBridge rule name for Lambda scheduling"
  value       = module.eventbridge.rule_name
}

# Configuration for frontend
output "frontend_config" {
  description = "Configuration object for frontend application"
  value = {
    aws_region              = var.aws_region
    application_url         = "http://${module.ecs.load_balancer_dns_name}"
    s3_bucket_name         = module.s3.bucket_name
  }
}