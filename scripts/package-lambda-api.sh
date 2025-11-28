#!/bin/bash
set -e

echo "Packaging Lambda function..."

# Create clean package directory
rm -rf lambda-package
mkdir -p lambda-package

# Install dependencies using AWS-recommended approach for Lambda Python 3.11
# https://repost.aws/knowledge-center/lambda-python-package-compatible
echo "Installing dependencies for Lambda runtime (manylinux2014_x86_64)..."

# Generate requirements without version pinning that might not have manylinux wheels
echo "Generating requirements from pyproject.toml..."
python3 -c "
import tomllib
with open('pyproject.toml', 'rb') as f:
    data = tomllib.load(f)
    deps = data['project']['dependencies']
    # Remove version specifiers that might not have manylinux wheels
    for dep in deps:
        print(dep.split('[')[0].split('>')[0].split('=')[0].split('<')[0])
" > requirements-lambda.txt

pip install \
    --platform manylinux2014_x86_64 \
    --target=lambda-package \
    --implementation cp \
    --python-version 3.11 \
    --only-binary=:all: \
    --upgrade \
    -r requirements-lambda.txt

# Clean up temporary requirements
rm -f requirements-lambda.txt

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
