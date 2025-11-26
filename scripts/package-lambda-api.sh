#!/bin/bash
set -e

echo "Packaging Lambda function..."

# Create clean package directory
rm -rf lambda-package
mkdir -p lambda-package

# Install dependencies with uv
cd lambda-package
uv pip install --target . -r ../requirements.txt --no-deps

# Copy application code
cp ../main.py .
cp ../auth.py .

# Remove unnecessary files
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete

# Create ZIP
zip -r ../lambda-api.zip . -x "*.git*" "*.DS_Store"

cd ..
echo "Package created: lambda-api.zip ($(du -h lambda-api.zip | cut -f1))"
