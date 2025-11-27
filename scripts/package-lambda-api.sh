#!/bin/bash
set -e

echo "Packaging Lambda function..."

# Create clean package directory
rm -rf lambda-package
mkdir -p lambda-package

# Install dependencies using AWS-recommended approach for Lambda Python 3.11
# https://repost.aws/knowledge-center/lambda-python-package-compatible
echo "Installing dependencies for Lambda runtime (manylinux2014_x86_64)..."
pip install \
    --platform manylinux2014_x86_64 \
    --target=lambda-package \
    --implementation cp \
    --python-version 3.11 \
    --only-binary=:all: \
    --upgrade \
    -r <(uv pip compile pyproject.toml)

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
