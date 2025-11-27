terraform {
  backend "s3" {
    bucket         = "canvas-ta-dashboard-terraform-state"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "canvas-ta-dashboard-terraform-lock"
    encrypt        = true
  }
}
