#!/bin/bash
set -e

echo "WARNING: This script will delete dev environment resources to allow a clean Terraform deployment."
echo "Resources to be deleted:"
echo "- S3 Bucket: canvas-ta-dashboard-frontend-dev"
echo "- IAM Roles: canvas-ta-dashboard-lambda-api-role-dev, canvas-ta-dashboard-lambda-role-dev"
echo "- Secrets Manager: canvas-ta-dashboard-canvas-api-token-dev"
echo "- CloudFront OAC: canvas-ta-dashboard-oac-dev"
echo ""
read -p "Are you sure you want to proceed? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

REGION="us-east-1"

echo "Deleting S3 bucket..."
aws s3 rb s3://canvas-ta-dashboard-frontend-dev --force --region $REGION || echo "Bucket not found or already deleted"

echo "Deleting IAM roles..."
# Detach policies first
for role in "canvas-ta-dashboard-lambda-api-role-dev" "canvas-ta-dashboard-lambda-role-dev"; do
    echo "Processing role: $role"
    policies=$(aws iam list-attached-role-policies --role-name $role --query 'AttachedPolicies[*].PolicyArn' --output text 2>/dev/null || echo "")
    for policy in $policies; do
        echo "Detaching policy $policy from $role"
        aws iam detach-role-policy --role-name $role --policy-arn $policy
    done

    # Delete inline policies
    inline_policies=$(aws iam list-role-policies --role-name $role --query 'PolicyNames[*]' --output text 2>/dev/null || echo "")
    for policy in $inline_policies; do
        echo "Deleting inline policy $policy from $role"
        aws iam delete-role-policy --role-name $role --policy-name $policy
    done

    aws iam delete-role --role-name $role || echo "Role $role not found or already deleted"
done

echo "Deleting Lambda functions..."
for func in "canvas-ta-dashboard-canvas-data-fetcher-dev" "canvas-ta-dashboard-api-dev"; do
    echo "Deleting function: $func"
    aws lambda delete-function --function-name $func --region $REGION || echo "Function $func not found or already deleted"
done

echo "Deleting Secrets Manager secret..."
aws secretsmanager delete-secret --secret-id canvas-ta-dashboard-canvas-api-token-dev --force-delete-without-recovery --region $REGION || echo "Secret not found or already deleted"

echo "Deleting CloudFront Origin Access Control..."
OAC_ID=$(aws cloudfront list-origin-access-controls --query "OriginAccessControlList.Items[?Name=='canvas-ta-dashboard-oac-dev'].Id" --output text)
if [ -n "$OAC_ID" ]; then
    ETAG=$(aws cloudfront get-origin-access-control --id $OAC_ID --query "ETag" --output text)
    aws cloudfront delete-origin-access-control --id $OAC_ID --if-match $ETAG
    echo "Deleted OAC: $OAC_ID"
else
    echo "OAC not found"
fi

echo "Cleanup complete. You can now retry the deployment."
