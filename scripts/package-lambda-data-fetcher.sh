#!/bin/bash
#
# Package Canvas Data Fetcher Lambda function with dependencies
# Creates a deployment package with canvasapi and other dependencies
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}📦 Packaging Canvas Data Fetcher Lambda function...${NC}"

# Navigate to project root
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

# Create temporary directory for packaging
TEMP_DIR=$(mktemp -d)
echo -e "${YELLOW}Using temp directory: $TEMP_DIR${NC}"

# Copy Lambda function code
echo -e "${YELLOW}Copying Lambda function code...${NC}"
cp lambda/canvas_data_fetcher.py "$TEMP_DIR/lambda_function.py"
cp lambda/requirements.txt "$TEMP_DIR/"

# Install dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
cd "$TEMP_DIR"
pip install -r requirements.txt --target . --upgrade --quiet

# Remove unnecessary files to reduce package size
echo -e "${YELLOW}Cleaning up unnecessary files...${NC}"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

# Create ZIP file
echo -e "${YELLOW}Creating deployment package...${NC}"
cd "$TEMP_DIR"
zip -r "$PROJECT_ROOT/lambda-data-fetcher.zip" . -q

# Clean up
cd "$PROJECT_ROOT"
rm -rf "$TEMP_DIR"

# Get package size
PACKAGE_SIZE=$(du -h lambda-data-fetcher.zip | cut -f1)
echo -e "${GREEN}✓ Package created: lambda-data-fetcher.zip ($PACKAGE_SIZE)${NC}"

# Check if package is under Lambda limit (250MB uncompressed, 50MB compressed)
PACKAGE_SIZE_BYTES=$(stat -f%z lambda-data-fetcher.zip 2>/dev/null || stat -c%s lambda-data-fetcher.zip 2>/dev/null)
MAX_SIZE=$((50 * 1024 * 1024))  # 50MB in bytes

if [ "$PACKAGE_SIZE_BYTES" -gt "$MAX_SIZE" ]; then
    echo -e "${RED}⚠️  Warning: Package size ($PACKAGE_SIZE) exceeds AWS Lambda direct upload limit (50MB)${NC}"
    echo -e "${YELLOW}Consider using Lambda layers or S3 upload for deployment${NC}"
else
    echo -e "${GREEN}✓ Package size within AWS Lambda limits${NC}"
fi

echo -e "${GREEN}✓ Lambda package ready for deployment${NC}"
echo -e "${YELLOW}To deploy: aws lambda update-function-code --function-name canvas-ta-dashboard-canvas-data-fetcher-dev --zip-file fileb://lambda-data-fetcher.zip${NC}"
