#!/bin/bash
# Manage Email Whitelist
# Quick commands to view, add, or remove emails from the whitelist

set -e

LAMBDA_NAME="canvas-ta-dashboard-prod-presignup"
REGION="us-east-1"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Get current allowed emails
get_current_emails() {
    aws lambda get-function-configuration \
        --function-name $LAMBDA_NAME \
        --region $REGION \
        --query 'Environment.Variables.ALLOWED_EMAILS' \
        --output text 2>/dev/null || echo ""
}

# Show usage
usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  list                    - Show current allowed emails"
    echo "  add <email>             - Add an email to the whitelist"
    echo "  remove <email>          - Remove an email from the whitelist"
    echo "  set <email1,email2,...> - Replace entire whitelist"
    echo ""
    echo "Examples:"
    echo "  $0 list"
    echo "  $0 add newta@gatech.edu"
    echo "  $0 remove oldta@gatech.edu"
    echo "  $0 set admin@base2ml.com,ta1@gatech.edu,ta2@gatech.edu"
    exit 1
}

# List current emails
list_emails() {
    CURRENT=$(get_current_emails)
    if [ -z "$CURRENT" ]; then
        echo -e "${YELLOW}No whitelist configured or Lambda function not found${NC}"
        exit 0
    fi

    echo "=========================================="
    echo "Current Allowed Emails:"
    echo "=========================================="
    echo "$CURRENT" | tr ',' '\n' | sed 's/^/  ✓ /'
    echo "=========================================="
    echo "Total: $(echo $CURRENT | tr ',' '\n' | wc -l | tr -d ' ') email(s)"
}

# Add email
add_email() {
    NEW_EMAIL=$(echo "$1" | tr '[:upper:]' '[:lower:]' | xargs)

    if [ -z "$NEW_EMAIL" ]; then
        echo -e "${RED}Error: No email provided${NC}"
        exit 1
    fi

    CURRENT=$(get_current_emails)

    # Check if already exists
    if echo "$CURRENT" | grep -q "$NEW_EMAIL"; then
        echo -e "${YELLOW}Email $NEW_EMAIL is already in the whitelist${NC}"
        exit 0
    fi

    # Add to list
    if [ -z "$CURRENT" ]; then
        UPDATED="$NEW_EMAIL"
    else
        UPDATED="$CURRENT,$NEW_EMAIL"
    fi

    # Update Lambda using JSON format to handle special characters
    aws lambda update-function-configuration \
        --function-name $LAMBDA_NAME \
        --environment "{\"Variables\":{\"ALLOWED_EMAILS\":\"$UPDATED\"}}" \
        --region $REGION \
        --output json > /dev/null

    echo -e "${GREEN}✓ Added: $NEW_EMAIL${NC}"
    echo ""
    list_emails
}

# Remove email
remove_email() {
    REMOVE_EMAIL=$(echo "$1" | tr '[:upper:]' '[:lower:]' | xargs)

    if [ -z "$REMOVE_EMAIL" ]; then
        echo -e "${RED}Error: No email provided${NC}"
        exit 1
    fi

    CURRENT=$(get_current_emails)

    # Check if exists
    if ! echo "$CURRENT" | grep -q "$REMOVE_EMAIL"; then
        echo -e "${YELLOW}Email $REMOVE_EMAIL is not in the whitelist${NC}"
        exit 0
    fi

    # Remove from list
    UPDATED=$(echo "$CURRENT" | tr ',' '\n' | grep -v "^$REMOVE_EMAIL$" | paste -sd ',' -)

    # Update Lambda using JSON format to handle special characters
    aws lambda update-function-configuration \
        --function-name $LAMBDA_NAME \
        --environment "{\"Variables\":{\"ALLOWED_EMAILS\":\"$UPDATED\"}}" \
        --region $REGION \
        --output json > /dev/null

    echo -e "${GREEN}✓ Removed: $REMOVE_EMAIL${NC}"
    echo ""
    list_emails
}

# Set entire list
set_emails() {
    NEW_LIST="$1"

    if [ -z "$NEW_LIST" ]; then
        echo -e "${RED}Error: No emails provided${NC}"
        exit 1
    fi

    # Normalize (lowercase and trim)
    UPDATED=$(echo "$NEW_LIST" | tr '[:upper:]' '[:lower:]' | tr ' ' '\n' | tr ',' '\n' | xargs | tr ' ' ',')

    # Update Lambda using JSON format to handle special characters
    aws lambda update-function-configuration \
        --function-name $LAMBDA_NAME \
        --environment "{\"Variables\":{\"ALLOWED_EMAILS\":\"$UPDATED\"}}" \
        --region $REGION \
        --output json > /dev/null

    echo -e "${GREEN}✓ Whitelist updated${NC}"
    echo ""
    list_emails
}

# Main
case "$1" in
    list)
        list_emails
        ;;
    add)
        add_email "$2"
        ;;
    remove)
        remove_email "$2"
        ;;
    set)
        set_emails "$2"
        ;;
    *)
        usage
        ;;
esac
