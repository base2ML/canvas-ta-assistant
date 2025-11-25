#!/bin/bash
set -e

echo "🚀 Canvas TA Dashboard - Lambda Migration Deployment"
echo "======================================================"
echo ""

# Configuration
FUNCTION_NAME="canvas-ta-dashboard-lambda"
RUNTIME="python3.11"
HANDLER="lambda_handler.handler"
MEMORY="512"
TIMEOUT="30"
REGION="us-east-1"
S3_BUCKET="canvas-ta-dashboard-canvas-data-prod-fauigkaq"
JWT_SECRET="${JWT_SECRET_KEY:-change-this-secret-key-in-production}"

echo "📦 Step 1: Install mangum dependency"
uv sync

echo "📦 Step 2: Build React frontend"
cd canvas-react
npm run build
cd ..

echo "📦 Step 3: Create Lambda deployment package"
rm -rf lambda-package lambda-package.zip
mkdir -p lambda-package

# Copy application code
cp main.py auth.py lambda_handler.py lambda-package/

# Install dependencies to lambda-package
echo "Installing Python dependencies..."
# Use pip with Lambda-compatible platform
pip install --platform manylinux2014_x86_64 --target=lambda-package --implementation cp --python-version 3.11 --only-binary=:all: --upgrade \
    fastapi canvasapi pydantic pydantic-settings python-multipart python-dateutil pandas loguru numpy httpx boto3 PyJWT bcrypt email-validator mangum uvicorn

# Create zip file
cd lambda-package
zip -r ../lambda-package.zip . -q
cd ..

echo "📦 Package size: $(du -h lambda-package.zip | cut -f1)"

echo "☁️  Step 4: Upload package to S3"
S3_KEY="lambda-deployments/canvas-ta-dashboard-lambda-$(date +%Y%m%d-%H%M%S).zip"
aws s3 cp lambda-package.zip "s3://$S3_BUCKET/$S3_KEY"

echo "☁️  Step 5: Check if Lambda function exists"
if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" 2>/dev/null; then
    echo "✅ Function exists - updating code from S3..."
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --s3-bucket "$S3_BUCKET" \
        --s3-key "$S3_KEY" \
        --region "$REGION" \
        --no-cli-pager

    echo "⚙️  Updating function configuration..."
    aws lambda update-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --runtime "$RUNTIME" \
        --handler "$HANDLER" \
        --memory-size "$MEMORY" \
        --timeout "$TIMEOUT" \
        --environment "Variables={S3_BUCKET_NAME=$S3_BUCKET,JWT_SECRET_KEY=$JWT_SECRET,ENVIRONMENT=prod}" \
        --region "$REGION" \
        --no-cli-pager
else
    echo "Creating new Lambda function..."

    # Create IAM role for Lambda if it doesn't exist
    ROLE_NAME="canvas-ta-dashboard-lambda-role"

    if ! aws iam get-role --role-name "$ROLE_NAME" 2>/dev/null; then
        echo "Creating IAM role..."
        aws iam create-role \
            --role-name "$ROLE_NAME" \
            --assume-role-policy-document '{
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }]
            }' \
            --no-cli-pager

        # Attach basic Lambda execution policy
        aws iam attach-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

        # Create and attach S3 access policy
        aws iam put-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-name "S3AccessPolicy" \
            --policy-document "{
                \"Version\": \"2012-10-17\",
                \"Statement\": [{
                    \"Effect\": \"Allow\",
                    \"Action\": [
                        \"s3:GetObject\",
                        \"s3:ListBucket\"
                    ],
                    \"Resource\": [
                        \"arn:aws:s3:::$S3_BUCKET\",
                        \"arn:aws:s3:::$S3_BUCKET/*\"
                    ]
                }]
            }"

        echo "Waiting 10 seconds for IAM role to propagate..."
        sleep 10
    fi

    ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)

    echo "Creating Lambda function from S3..."
    aws lambda create-function \
        --function-name "$FUNCTION_NAME" \
        --runtime "$RUNTIME" \
        --role "$ROLE_ARN" \
        --handler "$HANDLER" \
        --code "S3Bucket=$S3_BUCKET,S3Key=$S3_KEY" \
        --memory-size "$MEMORY" \
        --timeout "$TIMEOUT" \
        --environment "Variables={S3_BUCKET_NAME=$S3_BUCKET,JWT_SECRET_KEY=$JWT_SECRET,ENVIRONMENT=prod}" \
        --region "$REGION" \
        --no-cli-pager
fi

echo "🌐 Step 6: Create/Update Lambda Function URL"
FUNCTION_URL=$(aws lambda get-function-url-config --function-name "$FUNCTION_NAME" --region "$REGION" 2>/dev/null | jq -r '.FunctionUrl' || echo "")

if [ -z "$FUNCTION_URL" ]; then
    echo "Creating Function URL..."
    FUNCTION_URL=$(aws lambda create-function-url-config \
        --function-name "$FUNCTION_NAME" \
        --auth-type NONE \
        --cors '{
            "AllowOrigins": ["*"],
            "AllowMethods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "AllowHeaders": ["*"],
            "MaxAge": 86400
        }' \
        --region "$REGION" \
        --query 'FunctionUrl' \
        --output text)

    # Add resource-based policy to allow public invocation
    aws lambda add-permission \
        --function-name "$FUNCTION_NAME" \
        --statement-id FunctionURLAllowPublicAccess \
        --action lambda:InvokeFunctionUrl \
        --principal "*" \
        --function-url-auth-type NONE \
        --region "$REGION" \
        --no-cli-pager 2>/dev/null || true
else
    echo "Function URL already exists"
fi

echo ""
echo "✅ Lambda Deployment Complete!"
echo "======================================================"
echo "Function URL: $FUNCTION_URL"
echo "Function Name: $FUNCTION_NAME"
echo "Region: $REGION"
echo ""
echo "🧪 Test the function:"
echo "curl ${FUNCTION_URL}health"
echo ""
echo "📋 Next steps:"
echo "1. Test the Lambda function URL"
echo "2. Upload React build to S3 for static hosting"
echo "3. Configure CloudFront distribution"
echo "4. Update DNS to point to CloudFront"
echo ""

# Cleanup
rm -rf lambda-package lambda-package.zip
