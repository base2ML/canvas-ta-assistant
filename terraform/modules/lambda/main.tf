# Lambda Function Module for Canvas API Data Fetching

# Create Lambda function package
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_function"
  output_path = "${path.module}/lambda_function.zip"
}

# Lambda function
resource "aws_lambda_function" "canvas_data_fetcher" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "${var.project_name}-${var.function_name}-${var.environment}"
  role            = aws_iam_role.lambda_role.arn
  handler         = "lambda_function.lambda_handler"
  runtime         = var.runtime
  timeout         = var.timeout
  memory_size     = var.memory_size

  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = var.environment_variables
  }

  tags = var.tags
}

# IAM role for Lambda function
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# IAM policy for Lambda function
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.project_name}-lambda-policy-${var.environment}"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.s3_bucket_arn,
          "${var.s3_bucket_arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "arn:aws:secretsmanager:*:*:secret:${var.project_name}-canvas-api-token-${var.environment}-*"
      }
    ]
  })
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.canvas_data_fetcher.function_name}"
  retention_in_days = 30

  tags = var.tags
}

# Secrets Manager secret for Canvas API token
resource "aws_secretsmanager_secret" "canvas_api_token" {
  name                    = "${var.project_name}-canvas-api-token-${var.environment}"
  description             = "Canvas API token for data fetching"
  recovery_window_in_days = 7

  lifecycle {
    ignore_changes = [name]
  }

  tags = var.tags
}

# Secrets Manager secret version (placeholder - will be updated after deployment)
resource "aws_secretsmanager_secret_version" "canvas_api_token" {
  secret_id     = aws_secretsmanager_secret.canvas_api_token.id
  secret_string = jsonencode({
    canvas_api_token = "PLACEHOLDER_TOKEN_UPDATE_AFTER_DEPLOYMENT"
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}
