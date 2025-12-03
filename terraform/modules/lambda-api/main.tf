resource "aws_iam_role" "lambda_exec" {
  name = "${var.project_name}-lambda-api-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "s3_access" {
  name = "${var.project_name}-s3-access-${var.environment}"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.s3_bucket_arn,
          "${var.s3_bucket_arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_invoke" {
  name = "${var.project_name}-lambda-invoke-${var.environment}"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          "arn:aws:lambda:*:*:function:${var.project_name}-canvas-data-fetcher-${var.environment}"
        ]
      }
    ]
  })
}

resource "aws_lambda_function" "api" {
  function_name = "${var.project_name}-api-${var.environment}"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "main.handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 1024

  # Use a dummy zip if file doesn't exist yet (for initial apply)
  filename         = fileexists("${path.root}/../lambda-api.zip") ? "${path.root}/../lambda-api.zip" : "${path.module}/dummy.zip"
  source_code_hash = fileexists("${path.root}/../lambda-api.zip") ? filebase64sha256("${path.root}/../lambda-api.zip") : null

  environment {
    variables = var.environment_variables
  }

  tags = var.tags
}

# Create a dummy zip file for initial deployment if needed
data "archive_file" "dummy" {
  type        = "zip"
  output_path = "${path.module}/dummy.zip"
  source {
    content  = "def handler(event, context): return 'hello'"
    filename = "main.py"
  }
}
