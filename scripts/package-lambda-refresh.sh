#!/bin/bash
# Package Canvas Data Fetcher Lambda with dependencies

set -e

echo "📦 Packaging Canvas Data Fetcher Lambda..."

# Navigate to terraform directory
cd "$(dirname "$0")/../terraform/modules/lambda"

# Create a clean build directory
rm -rf build
mkdir -p build

# Copy Lambda function code
cp lambda_function/lambda_function.py build/

# Install dependencies into build directory
echo "Installing dependencies..."
pip install --target build -r lambda_function/requirements.txt --quiet

# Create ZIP file
echo "Creating deployment package..."
cd build
zip -r ../../lambda-refresh.zip . -q
cd ..

# Clean up
rm -rf build

echo "✅ Lambda package created: terraform/lambda-refresh.zip"
echo "📊 Package size: $(du -h ../lambda-refresh.zip | cut -f1)"
