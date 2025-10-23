# Production Environment Configuration
# Canvas TA Dashboard Infrastructure

aws_region = "us-east-1"
environment = "prod"
project_name = "canvas-ta-dashboard"

# Canvas Configuration
canvas_api_url = "https://your-institution.instructure.com"
canvas_course_id = "12345"

# ECR Configuration (will be updated by deployment script)
ecr_repository_url = ""

# Optional: Canvas API token (will be set via Secrets Manager after deployment)
# canvas_api_token = ""