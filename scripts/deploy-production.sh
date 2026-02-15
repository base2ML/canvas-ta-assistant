#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Deploying TA Dashboard with Production Course ===${NC}\n"

# Verify .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found${NC}"
    echo "Create .env with production configuration"
    exit 1
fi

# Show which course ID is being used
echo -e "${BLUE}ℹ️  Using configuration from .env${NC}"
COURSE_ID=$(grep CANVAS_COURSE_ID .env | cut -d= -f2)
echo -e "${BLUE}   Course ID: ${COURSE_ID:-not set}${NC}\n"

# Optional: Reset data volume for clean slate
if [ "$1" == "--clean" ]; then
    echo -e "${YELLOW}⚠️  Cleaning data volume for fresh start...${NC}"
    docker-compose down -v 2>/dev/null || true
fi

# Deploy with production configuration
echo -e "${BLUE}🚀 Starting Docker Compose with production config...${NC}\n"
docker-compose --env-file .env up --build

# This line runs after docker-compose stops
echo -e "\n${GREEN}✅ Production deployment stopped${NC}"
