#!/bin/bash
set -e

REGION="us-east-1"
BUCKET_NAME="canvas-ta-dashboard-terraform-state"
TABLE_NAME="canvas-ta-dashboard-terraform-lock"

echo "Creating Terraform backend resources..."

# Create S3 bucket
if aws s3 ls "s3://$BUCKET_NAME" 2>&1 | grep -q 'NoSuchBucket'; then
    echo "Creating S3 bucket: $BUCKET_NAME"
    aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$REGION"
    aws s3api put-bucket-versioning --bucket "$BUCKET_NAME" --versioning-configuration Status=Enabled
else
    echo "S3 bucket $BUCKET_NAME already exists"
fi

# Create DynamoDB table
if ! aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$REGION" >/dev/null 2>&1; then
    echo "Creating DynamoDB table: $TABLE_NAME"
    aws dynamodb create-table \
        --table-name "$TABLE_NAME" \
        --attribute-definitions AttributeName=LockID,AttributeType=S \
        --key-schema AttributeName=LockID,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --region "$REGION"
else
    echo "DynamoDB table $TABLE_NAME already exists"
fi

echo "Backend resources ready."
