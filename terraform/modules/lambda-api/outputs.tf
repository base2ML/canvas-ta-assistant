output "function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.api.arn
}

output "function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.api.function_name
}

output "role_arn" {
  description = "ARN of the IAM role"
  value       = aws_iam_role.lambda_exec.arn
}
