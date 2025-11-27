#!/bin/bash
set -e

# Log output to file
LOG_FILE="cleanup.log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "Starting cleanup at $(date)"


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

echo "Deleting CloudWatch Log Groups..."
for group in "/aws/lambda/canvas-ta-dashboard-canvas-data-fetcher-dev" "/aws/lambda/canvas-ta-dashboard-api-dev" "/aws/api-gateway/canvas-ta-dashboard-api-dev"; do
    echo "Deleting log group: $group"
    aws logs delete-log-group --log-group-name $group --region $REGION || echo "Log group $group not found or already deleted"
done

echo "Deleting Secrets Manager secret..."
aws secretsmanager delete-secret --secret-id canvas-ta-dashboard-canvas-api-token-dev --force-delete-without-recovery --region $REGION || echo "Secret not found or already deleted"

echo "Deleting CloudFront Distribution..."
# Find distribution using the OAC
DIST_ID=$(aws cloudfront list-distributions --query "DistributionList.Items[?Origins.Items[0].OriginAccessControlId=='$OAC_IDS'].Id" --output text)

if [ "$DIST_ID" != "None" ] && [ -n "$DIST_ID" ]; then
    echo "Found Distribution: $DIST_ID"
    ETAG=$(aws cloudfront get-distribution --id $DIST_ID --query "ETag" --output text)

    echo "Disabling Distribution..."
    aws cloudfront update-distribution --id $DIST_ID --if-match $ETAG --distribution-config "{\"Enabled\":false}" >/dev/null 2>&1 || echo "Could not disable distribution (might need full config)"

    # Wait for disabled state (simplified)
    echo "Waiting for distribution to be disabled (this might take a while)..."
    sleep 10

    echo "Deleting Distribution..."
    aws cloudfront delete-distribution --id $DIST_ID --if-match $ETAG || echo "Could not delete distribution (might not be disabled yet)"
fi

echo "Deleting CloudFront Origin Access Control..."
# Get all OAC IDs with the matching name
OAC_IDS=$(aws cloudfront list-origin-access-controls --query "OriginAccessControlList.Items[?Name=='canvas-ta-dashboard-oac-dev'].Id" --output text)

if [ "$OAC_IDS" == "None" ] || [ -z "$OAC_IDS" ]; then
    echo "No OAC found with name 'canvas-ta-dashboard-oac-dev'"
else
    for OAC_ID in $OAC_IDS; do
        echo "Found OAC: $OAC_ID"
        ETAG=$(aws cloudfront get-origin-access-control --id $OAC_ID --query "ETag" --output text)
        aws cloudfront delete-origin-access-control --id $OAC_ID --if-match $ETAG
        echo "Deleted OAC: $OAC_ID"
    done
fi

echo "Cleanup complete. You can now retry the deployment."
