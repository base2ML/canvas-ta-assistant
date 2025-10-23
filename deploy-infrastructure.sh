#!/bin/bash

# Canvas TA Dashboard Infrastructure Deployment Script
# This script deploys the complete infrastructure using Terraform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_dependencies() {
    print_status "Checking dependencies..."

    if ! command -v terraform &> /dev/null; then
        print_error "Terraform is not installed. Please install Terraform first."
        exit 1
    fi

    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install AWS CLI first."
        exit 1
    fi

    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    print_success "All dependencies are installed"
}

# Create ECR repository if it doesn't exist
create_ecr_repository() {
    print_status "Creating ECR repository..."

    aws ecr describe-repositories --repository-names canvas-ta-dashboard 2>/dev/null || {
        aws ecr create-repository --repository-name canvas-ta-dashboard
        print_success "ECR repository created"
    }

    # Get ECR repository URL
    ECR_URL=$(aws ecr describe-repositories --repository-names canvas-ta-dashboard --query 'repositories[0].repositoryUri' --output text)
    print_success "ECR repository URL: $ECR_URL"
}

# Build and push Docker image
build_and_push_image() {
    print_status "Building and pushing Docker image..."

    # Get AWS account ID and region
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    AWS_REGION=$(aws configure get region)

    # Login to ECR
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

    # Build image
    docker build --platform linux/amd64 -t canvas-ta-dashboard:latest .

    # Tag image
    docker tag canvas-ta-dashboard:latest $ECR_URL:latest

    # Push image
    docker push $ECR_URL:latest

    print_success "Docker image built and pushed"
}

# Deploy infrastructure with Terraform
deploy_infrastructure() {
    print_status "Deploying infrastructure with Terraform..."

    cd terraform

    # Initialize Terraform
    terraform init

    # Validate configuration
    terraform validate

    # Plan deployment
    terraform plan -var="ecr_repository_url=$ECR_URL"

    # Ask for confirmation
    echo
    print_warning "Do you want to proceed with the deployment? (yes/no)"
    read -r response

    if [[ "$response" == "yes" ]]; then
        # Apply configuration
        terraform apply -var="ecr_repository_url=$ECR_URL" -auto-approve

        print_success "Infrastructure deployed successfully!"

        # Output important information
        echo
        print_status "Deployment Information:"
        terraform output

    else
        print_warning "Deployment cancelled"
        exit 0
    fi

    cd ..
}

# Update Canvas API token in Secrets Manager
update_canvas_token() {
    print_status "Canvas API token setup..."

    SECRET_NAME=$(terraform -chdir=terraform output -raw lambda_function_name 2>/dev/null || echo "canvas-ta-dashboard-canvas-api-token-prod")

    echo
    print_warning "You need to update the Canvas API token in AWS Secrets Manager."
    print_status "Secret name: $SECRET_NAME"
    print_status "Run this command with your actual Canvas API token:"
    echo
    echo "aws secretsmanager put-secret-value --secret-id $SECRET_NAME --secret-string '{\"canvas_api_token\":\"YOUR_ACTUAL_TOKEN_HERE\"}'"
    echo
}

# Test the deployment
test_deployment() {
    print_status "Testing deployment..."

    cd terraform

    # Get the application URL
    APP_URL=$(terraform output -raw application_url 2>/dev/null || echo "")

    if [[ -n "$APP_URL" ]]; then
        print_status "Application URL: $APP_URL"

        # Test health endpoint
        if curl -f "$APP_URL/api/health" >/dev/null 2>&1; then
            print_success "Application is responding to health checks"
        else
            print_warning "Application health check failed - this is expected until the Canvas API token is configured"
        fi
    else
        print_warning "Could not retrieve application URL from Terraform output"
    fi

    cd ..
}

# Main deployment workflow
main() {
    print_status "Starting Canvas TA Dashboard infrastructure deployment..."

    check_dependencies
    create_ecr_repository
    build_and_push_image
    deploy_infrastructure
    update_canvas_token
    test_deployment

    print_success "Deployment completed!"
    print_status "Next steps:"
    echo "1. Update the Canvas API token in AWS Secrets Manager (command provided above)"
    echo "2. Test the Lambda function to ensure Canvas data is being fetched"
    echo "3. Access your application at the provided URL"
    echo "4. Create user accounts via the Cognito interface or API"
}

# Run main function
main "$@"