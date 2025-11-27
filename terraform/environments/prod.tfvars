# Production Environment Configuration

# AWS Configuration
aws_region  = "us-east-1"
environment = "prod"

# Canvas Configuration
canvas_api_url   = "https://canvas.instructure.com"
canvas_course_id = "20960000000516212"

# CORS Configuration
cors_allowed_origins = [
  "https://ta-dashboard-isye6740.base2ml.com",
  "https://ta-dashboard-isye6740-prod.base2ml.com"
]

# Domain Configuration
domain_aliases      = ["ta-dashboard-isye6740-prod.base2ml.com"]
acm_certificate_arn = "arn:aws:acm:us-east-1:741783034843:certificate/ab17a163-4221-45b8-87e0-96409365a138"
