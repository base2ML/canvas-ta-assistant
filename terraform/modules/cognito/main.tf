# Cognito User Pool Module for Canvas TA Dashboard

# Cognito User Pool
resource "aws_cognito_user_pool" "main" {
  name = "${var.project_name}-user-pool-${var.environment}"

  # User attributes
  username_attributes      = var.username_attributes
  auto_verified_attributes = var.auto_verified_attributes

  # Password policy
  password_policy {
    minimum_length                   = var.minimum_length
    require_lowercase               = var.require_lowercase
    require_numbers                 = var.require_numbers
    require_symbols                 = var.require_symbols
    require_uppercase               = var.require_uppercase
    temporary_password_validity_days = 7
  }

  # Email configuration
  email_configuration {
    email_sending_account = var.email_sending_account
  }

  # Account recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # User pool add-ons
  user_pool_add_ons {
    advanced_security_mode = "OFF"  # Keep costs low for initial deployment
  }

  # Verification message templates
  verification_message_template {
    default_email_option = "CONFIRM_WITH_LINK"
    email_subject        = "Welcome to Canvas TA Dashboard - Verify your email"
    email_message        = "Welcome to Canvas TA Dashboard! Please verify your email with code: {####}"
  }

  tags = var.tags
}

# Cognito User Pool Client
resource "aws_cognito_user_pool_client" "main" {
  name         = "${var.project_name}-client-${var.environment}"
  user_pool_id = aws_cognito_user_pool.main.id

  # Client configuration
  generate_secret = false  # For frontend applications

  # Authentication flows
  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_PASSWORD_AUTH"
  ]

  # Token validity
  access_token_validity  = 1   # 1 hour
  id_token_validity     = 1   # 1 hour
  refresh_token_validity = 30  # 30 days

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  # Prevent user existence errors
  prevent_user_existence_errors = "ENABLED"
}

# Cognito User Pool Domain
resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${var.project_name}-auth-${var.environment}-${random_string.domain_suffix.result}"
  user_pool_id = aws_cognito_user_pool.main.id
}

# Random string for unique domain
resource "random_string" "domain_suffix" {
  length  = 8
  lower   = true
  upper   = false
  special = false
  numeric = true
}