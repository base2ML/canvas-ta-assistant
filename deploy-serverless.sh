#!/bin/bash

# Canvas TA Dashboard - Serverless Deployment Script
# One-command deployment to AWS with Lambda, API Gateway, CloudFront, and Cognito

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not found. Please install: https://aws.amazon.com/cli/"
        exit 1
    fi
    print_success "AWS CLI installed"

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Run: aws configure"
        exit 1
    fi
    print_success "AWS credentials configured"

    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform not found. Please install: https://www.terraform.io/downloads"
        exit 1
    fi
    print_success "Terraform installed ($(terraform version | head -n1))"

    # Check Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js not found. Please install: https://nodejs.org/"
        exit 1
    fi
    print_success "Node.js installed ($(node --version))"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found. Please install: https://www.python.org/"
        exit 1
    fi
    print_success "Python 3 installed ($(python3 --version))"

    # Check uv
    if ! command -v uv &> /dev/null; then
        print_warning "uv not found. Installing..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
    fi
    print_success "uv package manager available"

    echo ""
}

# Setup Terraform backend
setup_terraform_backend() {
    print_header "Setting Up Terraform Backend"

    BUCKET_NAME="canvas-ta-terraform-state"
    TABLE_NAME="canvas-ta-terraform-lock"
    REGION="us-east-1"

    # Check if bucket exists
    if aws s3 ls "s3://${BUCKET_NAME}" 2>&1 | grep -q 'NoSuchBucket'; then
        print_info "Creating S3 bucket for Terraform state..."
        aws s3api create-bucket \
            --bucket "${BUCKET_NAME}" \
            --region "${REGION}"

        # Enable versioning
        aws s3api put-bucket-versioning \
            --bucket "${BUCKET_NAME}" \
            --versioning-configuration Status=Enabled

        # Enable encryption
        aws s3api put-bucket-encryption \
            --bucket "${BUCKET_NAME}" \
            --server-side-encryption-configuration '{
                "Rules": [{
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }]
            }'

        print_success "S3 bucket created and configured"
    else
        print_success "S3 bucket already exists"
    fi

    # Check if DynamoDB table exists
    if ! aws dynamodb describe-table --table-name "${TABLE_NAME}" --region "${REGION}" &> /dev/null; then
        print_info "Creating DynamoDB table for state locking..."
        aws dynamodb create-table \
            --table-name "${TABLE_NAME}" \
            --attribute-definitions AttributeName=LockID,AttributeType=S \
            --key-schema AttributeName=LockID,KeyType=HASH \
            --billing-mode PAY_PER_REQUEST \
            --region "${REGION}"

        print_success "DynamoDB table created"
    else
        print_success "DynamoDB table already exists"
    fi

    echo ""
}

# Build frontend
build_frontend() {
    print_header "Building React Frontend"

    cd canvas-react

    print_info "Installing dependencies..."
    npm ci --silent

    print_info "Running linter..."
    npm run lint || print_warning "Linting warnings found"

    print_info "Building production bundle..."
    npm run build

    print_success "Frontend build completed"

    cd ..
    echo ""
}

# Package Lambda functions
package_lambda() {
    print_header "Packaging Lambda Functions"

    # Create package directories
    mkdir -p lambda-packages/api-handler
    mkdir -p lambda-packages/canvas-sync

    # Package API handler
    print_info "Packaging API handler Lambda..."
    cp main.py lambda-packages/api-handler/
    uv pip install --target lambda-packages/api-handler -r pyproject.toml --quiet

    # Create zip
    cd lambda-packages/api-handler
    zip -r ../../api-handler.zip . -q
    cd ../..

    print_success "API handler packaged ($(du -h api-handler.zip | cut -f1))"

    # Package Canvas sync function
    print_info "Packaging Canvas sync Lambda..."
    cp lambda/canvas_data_fetcher.py lambda-packages/canvas-sync/lambda_function.py
    cp lambda/requirements.txt lambda-packages/canvas-sync/
    pip install --target lambda-packages/canvas-sync -r lambda/requirements.txt --quiet

    # Create zip
    cd lambda-packages/canvas-sync
    zip -r ../../canvas-sync.zip . -q
    cd ../..

    print_success "Canvas sync packaged ($(du -h canvas-sync.zip | cut -f1))"

    echo ""
}

# Deploy infrastructure
deploy_infrastructure() {
    print_header "Deploying AWS Infrastructure"

    cd terraform-serverless

    # Determine environment
    ENVIRONMENT="${1:-dev}"
    print_info "Deploying to environment: ${ENVIRONMENT}"

    # Initialize Terraform
    print_info "Initializing Terraform..."
    terraform init -upgrade

    # Validate configuration
    print_info "Validating Terraform configuration..."
    terraform validate

    # Check for Canvas API token
    if [ -z "${CANVAS_API_TOKEN}" ]; then
        print_warning "CANVAS_API_TOKEN not set"
        read -sp "Enter Canvas API Token: " CANVAS_API_TOKEN
        echo ""
    fi

    # Plan infrastructure changes
    print_info "Planning infrastructure changes..."
    terraform plan \
        -var-file="environments/${ENVIRONMENT}.tfvars" \
        -var="canvas_api_token=${CANVAS_API_TOKEN}" \
        -out=tfplan

    # Prompt for confirmation
    echo ""
    read -p "$(echo -e ${YELLOW}Apply these changes? [y/N]:${NC} )" -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Deployment cancelled"
        exit 0
    fi

    # Apply infrastructure changes
    print_info "Applying infrastructure changes..."
    terraform apply tfplan

    # Save outputs
    print_info "Saving Terraform outputs..."
    terraform output -json > ../outputs.json

    print_success "Infrastructure deployed successfully"

    cd ..
    echo ""
}

# Deploy frontend to S3
deploy_frontend() {
    print_header "Deploying Frontend to S3 + CloudFront"

    # Get S3 bucket name and CloudFront distribution ID from Terraform outputs
    S3_BUCKET=$(cat outputs.json | jq -r '.frontend_bucket_name.value')
    CLOUDFRONT_ID=$(cat outputs.json | jq -r '.cloudfront_distribution_id.value')
    API_URL=$(cat outputs.json | jq -r '.api_gateway_url.value')
    USER_POOL_ID=$(cat outputs.json | jq -r '.cognito_user_pool_id.value')
    CLIENT_ID=$(cat outputs.json | jq -r '.cognito_user_pool_client_id.value')

    print_info "Updating frontend configuration..."
    # Replace environment variables in built files
    find canvas-react/dist -type f -name "*.js" -exec sed -i.bak \
        -e "s|__API_ENDPOINT__|${API_URL}|g" \
        -e "s|__USER_POOL_ID__|${USER_POOL_ID}|g" \
        -e "s|__CLIENT_ID__|${CLIENT_ID}|g" {} \;

    # Clean up backup files
    find canvas-react/dist -name "*.bak" -delete

    print_info "Uploading to S3..."
    aws s3 sync canvas-react/dist/ "s3://${S3_BUCKET}/" \
        --delete \
        --cache-control "public, max-age=31536000, immutable" \
        --exclude "index.html"

    # Upload index.html with no-cache
    aws s3 cp canvas-react/dist/index.html "s3://${S3_BUCKET}/index.html" \
        --cache-control "no-cache, no-store, must-revalidate"

    print_success "Frontend uploaded to S3"

    print_info "Invalidating CloudFront cache..."
    INVALIDATION_ID=$(aws cloudfront create-invalidation \
        --distribution-id "${CLOUDFRONT_ID}" \
        --paths "/*" \
        --query 'Invalidation.Id' \
        --output text)

    print_success "CloudFront cache invalidated (ID: ${INVALIDATION_ID})"

    echo ""
}

# Deploy backend Lambda functions
deploy_backend() {
    print_header "Deploying Lambda Functions"

    # Get Lambda function names from Terraform outputs
    API_FUNCTION=$(cat outputs.json | jq -r '.api_lambda_function_name.value')
    SYNC_FUNCTION=$(cat outputs.json | jq -r '.sync_lambda_function_name.value')

    # Update API handler Lambda
    print_info "Updating API handler Lambda..."
    aws lambda update-function-code \
        --function-name "${API_FUNCTION}" \
        --zip-file fileb://api-handler.zip \
        --query 'LastModified' \
        --output text

    # Wait for update to complete
    aws lambda wait function-updated --function-name "${API_FUNCTION}"

    print_success "API handler Lambda updated"

    # Update Canvas sync Lambda
    print_info "Updating Canvas sync Lambda..."
    aws lambda update-function-code \
        --function-name "${SYNC_FUNCTION}" \
        --zip-file fileb://canvas-sync.zip \
        --query 'LastModified' \
        --output text

    # Wait for update to complete
    aws lambda wait function-updated --function-name "${SYNC_FUNCTION}"

    print_success "Canvas sync Lambda updated"

    # Publish new versions
    print_info "Publishing Lambda versions..."
    API_VERSION=$(aws lambda publish-version \
        --function-name "${API_FUNCTION}" \
        --description "Deployed via deploy-serverless.sh" \
        --query 'Version' \
        --output text)

    SYNC_VERSION=$(aws lambda publish-version \
        --function-name "${SYNC_FUNCTION}" \
        --description "Deployed via deploy-serverless.sh" \
        --query 'Version' \
        --output text)

    print_success "Published versions: API=${API_VERSION}, Sync=${SYNC_VERSION}"

    echo ""
}

# Run smoke tests
run_smoke_tests() {
    print_header "Running Smoke Tests"

    API_URL=$(cat outputs.json | jq -r '.api_gateway_url.value')

    # Test health endpoint
    print_info "Testing health endpoint..."
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/health")

    if [ "${HTTP_CODE}" -eq 200 ]; then
        print_success "Health check passed (HTTP ${HTTP_CODE})"
    else
        print_error "Health check failed (HTTP ${HTTP_CODE})"
        exit 1
    fi

    # Test config endpoint
    print_info "Testing config endpoint..."
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/api/config")

    if [ "${HTTP_CODE}" -eq 200 ]; then
        print_success "Config endpoint passed (HTTP ${HTTP_CODE})"
    else
        print_warning "Config endpoint returned HTTP ${HTTP_CODE}"
    fi

    # Test API response time
    print_info "Testing API response time..."
    START_TIME=$(date +%s%N)
    curl -s "${API_URL}/health" > /dev/null
    END_TIME=$(date +%s%N)
    DURATION=$(( (END_TIME - START_TIME) / 1000000 ))

    print_success "API response time: ${DURATION}ms"

    if [ ${DURATION} -gt 2000 ]; then
        print_warning "API response time > 2s"
    fi

    echo ""
}

# Display deployment summary
display_summary() {
    print_header "Deployment Summary"

    WEBSITE_URL=$(cat outputs.json | jq -r '.website_url.value')
    API_URL=$(cat outputs.json | jq -r '.api_gateway_url.value')
    CLOUDFRONT_DOMAIN=$(cat outputs.json | jq -r '.cloudfront_domain_name.value')
    DASHBOARD_URL=$(cat outputs.json | jq -r '.cloudwatch_dashboard_url.value')

    echo -e "${GREEN}🎉 Deployment Completed Successfully!${NC}"
    echo ""
    echo -e "${BLUE}Website URL:${NC}        ${WEBSITE_URL}"
    echo -e "${BLUE}API Base URL:${NC}       ${API_URL}"
    echo -e "${BLUE}CloudFront Domain:${NC}  ${CLOUDFRONT_DOMAIN}"
    echo ""
    echo -e "${BLUE}CloudWatch Dashboard:${NC} ${DASHBOARD_URL}"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "  1. Visit ${WEBSITE_URL} to access the dashboard"
    echo "  2. Create a Cognito user: aws cognito-idp admin-create-user --user-pool-id <pool-id> --username <email>"
    echo "  3. Monitor logs: aws logs tail /aws/lambda/<function-name> --follow"
    echo ""
    echo -e "${YELLOW}Cost Estimate:${NC} ~\$30-50/month for low traffic"
    echo ""
}

# Cleanup
cleanup() {
    print_info "Cleaning up temporary files..."
    rm -rf lambda-packages
    rm -f api-handler.zip canvas-sync.zip
    rm -f terraform-serverless/tfplan
    print_success "Cleanup complete"
}

# Main deployment flow
main() {
    ENVIRONMENT="${1:-dev}"

    print_header "Canvas TA Dashboard - Serverless Deployment"
    echo -e "${BLUE}Environment: ${ENVIRONMENT}${NC}"
    echo ""

    check_prerequisites
    setup_terraform_backend
    build_frontend
    package_lambda
    deploy_infrastructure "${ENVIRONMENT}"
    deploy_frontend
    deploy_backend
    run_smoke_tests
    display_summary
    cleanup

    print_success "All done! 🚀"
}

# Handle script arguments
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "Usage: $0 [environment]"
    echo ""
    echo "Arguments:"
    echo "  environment    Target environment (dev, staging, prod). Default: dev"
    echo ""
    echo "Examples:"
    echo "  $0           # Deploy to dev environment"
    echo "  $0 prod      # Deploy to production environment"
    echo ""
    echo "Environment Variables:"
    echo "  CANVAS_API_TOKEN    Canvas API token (required)"
    echo ""
    exit 0
fi

# Run main deployment
main "$@"
