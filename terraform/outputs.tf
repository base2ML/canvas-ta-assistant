# Outputs for Canvas TA Dashboard Infrastructure

output "frontend_url" {
  description = "URL of the CloudFront distribution"
  value       = module.cloudfront.cloudfront_domain_name
}

output "frontend_bucket_name" {
  description = "Name of the S3 bucket for frontend hosting"
  value       = module.cloudfront.bucket_name
}

output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution"
  value       = module.cloudfront.cloudfront_distribution_id
}

output "api_gateway_url" {
  description = "URL of the API Gateway"
  value       = module.api_gateway.api_endpoint
}

output "s3_bucket_name" {
  description = "S3 bucket name for Canvas data"
  value       = module.s3.bucket_name
}

output "lambda_function_name" {
  description = "Lambda function name for Canvas data fetcher"
  value       = module.lambda.function_name
}

output "lambda_api_function_name" {
  description = "Lambda function name for API handler"
  value       = module.lambda_api.function_name
}

output "eventbridge_rule_name" {
  description = "EventBridge rule name for Lambda scheduling"
  value       = module.eventbridge.rule_name
}
