#!/bin/bash
set -e

echo "Building frontend..."
cd canvas-react
npm run build

echo "Deploying to S3..."
aws s3 sync dist/ s3://${FRONTEND_BUCKET}/ --delete

echo "Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
  --distribution-id ${CLOUDFRONT_DISTRIBUTION_ID} \
  --paths "/*"

echo "Frontend deployed successfully!"
