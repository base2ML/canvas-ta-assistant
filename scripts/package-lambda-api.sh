#!/bin/bash
set -e

echo "Packaging Lambda function..."

# Create clean package directory
rm -rf lambda-package
mkdir -p lambda-package

# Check if Docker is available for Lambda-compatible builds
if command -v docker &> /dev/null; then
    echo "Using Docker to build Lambda-compatible package..."
    # Use official AWS Lambda Python 3.11 base image to build dependencies
    docker run --rm --platform linux/amd64 -v "$PWD":/var/task public.ecr.aws/lambda/python:3.11 \
        bash -c "cd /var/task && pip install . --target /var/task/lambda-package --no-cache-dir"
else
    echo "Docker not available, building with uv (may have compatibility issues)..."
    cd lambda-package
    uv pip install --target . -r <(uv pip compile ../pyproject.toml)
    cd ..
fi

# Copy application code
cp main.py lambda-package/
cp auth.py lambda-package/

# Remove unnecessary files
cd lambda-package
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete

# Create ZIP
zip -r ../lambda-api.zip . -x "*.git*" "*.DS_Store"

cd ..
echo "Package created: lambda-api.zip ($(du -h lambda-api.zip | cut -f1))"
