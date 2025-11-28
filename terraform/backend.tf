terraform {
  backend "s3" {
    bucket         = "canvas-ta-dashboard-terraform-state"
    # Key will be set dynamically via -backend-config in the workflow
    # Dev: env:/dev/terraform.tfstate
    # Prod: env:/prod/terraform.tfstate
    region         = "us-east-1"
    dynamodb_table = "canvas-ta-dashboard-terraform-lock"
    encrypt        = true
  }
}
