#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Deploying TA Dashboard with Sandbox Course ===${NC}\n"

# Verify .env.test exists
if [ ! -f ".env.test" ]; then
    echo -e "${RED}❌ .env.test file not found${NC}"
    echo "Create .env.test with sandbox configuration:"
    echo "  CANVAS_COURSE_ID=20960000000447574"
    exit 1
fi

# Show which course ID is being used
echo -e "${BLUE}ℹ️  Using configuration from .env.test${NC}"
echo -e "${BLUE}   Course ID: $(grep CANVAS_COURSE_ID .env.test | cut -d= -f2)${NC}\n"

# Optional: Reset data volume for clean slate
if [ "$1" == "--clean" ]; then
    echo -e "${YELLOW}⚠️  Cleaning data volume for fresh start...${NC}"
    docker-compose down -v 2>/dev/null || true
fi

# Deploy with sandbox configuration
echo -e "${BLUE}🚀 Starting Docker Compose with sandbox config...${NC}\n"
docker-compose --env-file .env.test up --build

# This line runs after docker-compose stops
echo -e "\n${GREEN}✅ Sandbox deployment stopped${NC}"
