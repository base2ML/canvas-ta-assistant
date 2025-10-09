#!/bin/bash

# Quick script to build and run Vibey Canvas Docker container locally
# Usage: ./docker-build-and-run.sh

set -e

echo "🐳 Building Vibey Canvas Docker image..."
docker build -t vibey-canvas:local .

echo ""
echo "✅ Build complete!"
echo ""
echo "🚀 Starting container on port 8000..."
echo ""

docker run -it --rm \
  -p 8000:8000 \
  -e PORT=8000 \
  -e CORS_ORIGINS='["http://localhost:8000"]' \
  --name vibey-canvas-dev \
  vibey-canvas:local

echo ""
echo "🛑 Container stopped"
