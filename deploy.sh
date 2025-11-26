#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
print_header "Checking Prerequisites"
command -v aws >/dev/null 2>&1 || { print_error "AWS CLI is required but not installed."; exit 1; }
command -v terraform >/dev/null 2>&1 || { print_error "Terraform is required but not installed."; exit 1; }
command -v npm >/dev/null 2>&1 || { print_error "npm is required but not installed."; exit 1; }
command -v uv >/dev/null 2>&1 || { print_error "uv is required but not installed."; exit 1; }
print_success "All prerequisites met."

# 1. Package Lambda
print_header "Step 1: Packaging Lambda Backend"
./scripts/package-lambda-api.sh

# 2. Apply Terraform
print_header "Step 2: Deploying Infrastructure with Terraform"
cd terraform
terraform init
terraform apply -auto-approve

# Capture outputs for frontend deployment
print_header "Step 3: Capturing Infrastructure Outputs"
FRONTEND_BUCKET=$(terraform output -raw frontend_bucket_name)
CLOUDFRONT_ID=$(terraform output -raw cloudfront_distribution_id)
API_ENDPOINT=$(terraform output -raw api_gateway_url)

if [ -z "$FRONTEND_BUCKET" ] || [ -z "$CLOUDFRONT_ID" ]; then
    print_error "Failed to get necessary Terraform outputs."
    exit 1
fi

echo "Frontend Bucket: $FRONTEND_BUCKET"
echo "CloudFront ID: $CLOUDFRONT_ID"
echo "API Endpoint: $API_ENDPOINT"

cd ..

# 3. Deploy Frontend
print_header "Step 4: Deploying Frontend"

# Export variables for the frontend script
export FRONTEND_BUCKET=$FRONTEND_BUCKET
export CLOUDFRONT_DISTRIBUTION_ID=$CLOUDFRONT_ID
export VITE_API_ENDPOINT=$API_ENDPOINT

# Create a temporary .env.production for the build
echo "VITE_API_ENDPOINT=$API_ENDPOINT" > canvas-react/.env.production

./scripts/deploy-frontend.sh

# Cleanup
rm canvas-react/.env.production

print_header "Deployment Complete!"
print_success "Backend deployed to: $API_ENDPOINT"
print_success "Frontend deployed to: https://$(aws cloudfront get-distribution --id $CLOUDFRONT_ID --query 'Distribution.DomainName' --output text)"
