# Outputs for Lambda Module

output "function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.canvas_data_fetcher.function_name
}

output "function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.canvas_data_fetcher.arn
}

output "function_invoke_arn" {
  description = "Invoke ARN of the Lambda function"
  value       = aws_lambda_function.canvas_data_fetcher.invoke_arn
}

output "role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_role.arn
}

output "secret_arn" {
  description = "ARN of the Canvas API token secret"
  value       = aws_secretsmanager_secret.canvas_api_token.arn
}

output "secret_name" {
  description = "Name of the Canvas API token secret"
  value       = aws_secretsmanager_secret.canvas_api_token.name
}