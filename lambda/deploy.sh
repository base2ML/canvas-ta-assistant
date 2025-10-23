#!/bin/bash

# Lambda deployment script for production
set -e

echo "Creating Lambda deployment package..."

# Create deployment directory
rm -rf deployment
mkdir -p deployment

# Install dependencies
pip install -r requirements.txt -t deployment/

# Copy Lambda function files
cp *.py deployment/

# Create deployment package
cd deployment
zip -r ../lambda-deployment.zip .
cd ..

# Upload to S3
aws s3 cp lambda-deployment.zip s3://canvas-ta-lambda-deploy-prod-741783034843/

# Update Lambda function
aws lambda update-function-code \
  --function-name canvas-ta-data-fetcher-prod \
  --s3-bucket canvas-ta-lambda-deploy-prod-741783034843 \
  --s3-key lambda-deployment.zip

echo "Lambda function deployed successfully!"

# Clean up
rm -rf deployment lambda-deployment.zip