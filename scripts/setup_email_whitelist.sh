#!/bin/bash
# Setup Email Whitelist for Cognito User Pool
# This script deploys a Lambda function to restrict signups to approved emails

set -e

# Configuration
LAMBDA_NAME="canvas-ta-dashboard-prod-presignup"
USER_POOL_ID="us-east-1_tWkVeJFdB"
REGION="us-east-1"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Canvas TA Dashboard - Email Whitelist Setup"
echo "=========================================="
echo ""

# Prompt for allowed emails
echo -e "${YELLOW}Enter allowed email addresses (comma-separated):${NC}"
echo "Example: admin@base2ml.com,ta1@gatech.edu,ta2@gatech.edu"
read -p "Allowed emails: " ALLOWED_EMAILS

if [ -z "$ALLOWED_EMAILS" ]; then
    echo -e "${RED}Error: No emails provided${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Creating Lambda deployment package...${NC}"

# Create deployment package
cd lambda
zip -q cognito_presignup.zip cognito_presignup.py
cd ..

echo -e "${GREEN}Checking if Lambda function exists...${NC}"

# Check if Lambda exists
if aws lambda get-function --function-name $LAMBDA_NAME --region $REGION >/dev/null 2>&1; then
    echo -e "${YELLOW}Lambda function exists, updating...${NC}"

    # Update function code
    aws lambda update-function-code \
        --function-name $LAMBDA_NAME \
        --zip-file fileb://lambda/cognito_presignup.zip \
        --region $REGION \
        --output json > /dev/null

    # Update environment variables using JSON format
    aws lambda update-function-configuration \
        --function-name $LAMBDA_NAME \
        --environment "{\"Variables\":{\"ALLOWED_EMAILS\":\"$ALLOWED_EMAILS\"}}" \
        --region $REGION \
        --output json > /dev/null

    echo -e "${GREEN}✓ Lambda function updated${NC}"
else
    echo -e "${YELLOW}Lambda function doesn't exist, creating...${NC}"

    # Create execution role if it doesn't exist
    ROLE_NAME="canvas-ta-dashboard-cognito-presignup-role"

    if ! aws iam get-role --role-name $ROLE_NAME >/dev/null 2>&1; then
        echo "Creating IAM role..."

        cat > /tmp/trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

        aws iam create-role \
            --role-name $ROLE_NAME \
            --assume-role-policy-document file:///tmp/trust-policy.json \
            --output json > /dev/null

        # Attach basic Lambda execution policy
        aws iam attach-role-policy \
            --role-name $ROLE_NAME \
            --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

        echo "Waiting for IAM role to propagate..."
        sleep 10
    fi

    ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)

    # Create Lambda function using JSON format for environment variables
    aws lambda create-function \
        --function-name $LAMBDA_NAME \
        --runtime python3.11 \
        --role $ROLE_ARN \
        --handler cognito_presignup.lambda_handler \
        --zip-file fileb://lambda/cognito_presignup.zip \
        --timeout 10 \
        --memory-size 128 \
        --environment "{\"Variables\":{\"ALLOWED_EMAILS\":\"$ALLOWED_EMAILS\"}}" \
        --region $REGION \
        --output json > /dev/null

    echo -e "${GREEN}✓ Lambda function created${NC}"
fi

# Get Lambda ARN
LAMBDA_ARN=$(aws lambda get-function --function-name $LAMBDA_NAME --region $REGION --query 'Configuration.FunctionArn' --output text)

echo -e "${GREEN}Lambda ARN: $LAMBDA_ARN${NC}"

# Grant Cognito permission to invoke Lambda
echo -e "${GREEN}Granting Cognito permission to invoke Lambda...${NC}"

# Remove existing permission if it exists
aws lambda remove-permission \
    --function-name $LAMBDA_NAME \
    --statement-id CognitoPreSignupPermission \
    --region $REGION 2>/dev/null || true

# Add new permission
aws lambda add-permission \
    --function-name $LAMBDA_NAME \
    --statement-id CognitoPreSignupPermission \
    --action lambda:InvokeFunction \
    --principal cognito-idp.amazonaws.com \
    --source-arn arn:aws:cognito-idp:$REGION:$(aws sts get-caller-identity --query Account --output text):userpool/$USER_POOL_ID \
    --region $REGION \
    --output json > /dev/null

echo -e "${GREEN}✓ Permission granted${NC}"

# Update Cognito User Pool with Lambda trigger
echo -e "${GREEN}Configuring Cognito User Pool trigger...${NC}"

aws cognito-idp update-user-pool \
    --user-pool-id $USER_POOL_ID \
    --lambda-config "PreSignUp=$LAMBDA_ARN" \
    --region $REGION

echo -e "${GREEN}✓ Cognito trigger configured${NC}"

# Cleanup
rm -f lambda/cognito_presignup.zip

echo ""
echo "=========================================="
echo -e "${GREEN}✓ Email Whitelist Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Allowed emails:"
echo "$ALLOWED_EMAILS" | tr ',' '\n' | sed 's/^/  - /'
echo ""
echo "Only these email addresses can create accounts."
echo ""
echo "To update the allowed list, run this script again."
echo "=========================================="
