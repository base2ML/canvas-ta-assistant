# Variables for EventBridge Module

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "schedule_expression" {
  description = "Schedule expression for the EventBridge rule"
  type        = string
  default     = "rate(15 minutes)"
}

variable "lambda_function_arn" {
  description = "ARN of the Lambda function to invoke"
  type        = string
}

variable "lambda_function_name" {
  description = "Name of the Lambda function to invoke"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}