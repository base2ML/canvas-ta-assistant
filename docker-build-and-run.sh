#!/bin/bash

# Quick script to build and run CDA TA Dashboard Docker container locally
# Usage: ./docker-build-and-run.sh

set -e

echo "🐳 Building CDA TA Dashboard Docker image..."
docker build -t cda-ta-dashboard:local .

echo ""
echo "✅ Build complete!"
echo ""
echo "🚀 Starting container on port 8000..."
echo ""

docker run -it --rm \
  -p 8000:8000 \
  -e PORT=8000 \
  -e CORS_ORIGINS='["http://localhost:8000"]' \
  --name cda-ta-dashboard-dev \
  cda-ta-dashboard:local

echo ""
echo "🛑 Container stopped"
