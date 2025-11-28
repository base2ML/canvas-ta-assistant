# S3 Bucket Module for Canvas Data Storage

# S3 Bucket
resource "aws_s3_bucket" "canvas_data" {
  bucket = "${var.project_name}-canvas-data-${var.environment}-${random_string.bucket_suffix.result}"

  tags = var.tags
}

# Random string for unique bucket name
resource "random_string" "bucket_suffix" {
  length  = 8
  lower   = true
  upper   = false
  special = false
  numeric = true
}

# S3 Bucket Versioning
resource "aws_s3_bucket_versioning" "canvas_data" {
  bucket = aws_s3_bucket.canvas_data.id

  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Disabled"
  }
}

# S3 Bucket Server Side Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "canvas_data" {
  count  = var.enable_encryption ? 1 : 0
  bucket = aws_s3_bucket.canvas_data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# S3 Bucket Public Access Block (Security)
resource "aws_s3_bucket_public_access_block" "canvas_data" {
  bucket = aws_s3_bucket.canvas_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket CORS Configuration
resource "aws_s3_bucket_cors_configuration" "canvas_data" {
  bucket = aws_s3_bucket.canvas_data.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = var.cors_allowed_origins
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}


# S3 Bucket Lifecycle Configuration
resource "aws_s3_bucket_lifecycle_configuration" "canvas_data" {
  count      = length(var.lifecycle_rules) > 0 ? 1 : 0
  depends_on = [aws_s3_bucket_versioning.canvas_data]

  bucket = aws_s3_bucket.canvas_data.id

  dynamic "rule" {
    for_each = var.lifecycle_rules
    content {
      id     = rule.value.id
      status = rule.value.status

      filter {
        prefix = ""
      }

      dynamic "transition" {
        for_each = rule.value.transitions
        content {
          days          = transition.value.days
          storage_class = transition.value.storage_class
        }
      }

      dynamic "expiration" {
        for_each = rule.value.expiration != null ? [rule.value.expiration] : []
        content {
          days = expiration.value.days
        }
      }
    }
  }
}

# S3 Bucket Policy for Lambda access
resource "aws_s3_bucket_policy" "canvas_data" {
  bucket = aws_s3_bucket.canvas_data.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowLambdaAccess"
        Effect = "Allow"
        Principal = {
          AWS = [
            "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project_name}-lambda-role-${var.environment}",
            "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project_name}-lambda-api-role-${var.environment}"
          ]
        }
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.canvas_data.arn,
          "${aws_s3_bucket.canvas_data.arn}/*"
        ]
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.canvas_data]
}

# Data source for current AWS account ID
data "aws_caller_identity" "current" {}
