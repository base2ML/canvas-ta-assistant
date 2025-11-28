#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Cleanup function
cleanup() {
    print_info "Cleaning up..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
        print_info "Stopped backend server (PID: $BACKEND_PID)"
    fi
    # Kill any process on port 8000
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
}

# Set trap to cleanup on exit
trap cleanup EXIT

print_header "Integration Test - Canvas TA Dashboard"

# Check prerequisites
print_info "Checking prerequisites..."
command -v python3 >/dev/null 2>&1 || { print_error "Python 3 is required"; exit 1; }
command -v uv >/dev/null 2>&1 || { print_error "uv is required"; exit 1; }
command -v npm >/dev/null 2>&1 || { print_error "npm is required"; exit 1; }
print_success "Prerequisites met"

# Check .env file
if [ ! -f ".env" ]; then
    print_error ".env file not found. Create it with required variables."
    exit 1
fi

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Test 1: Canvas Data Extraction
print_header "Test 1: Canvas Data Extraction"
python scripts/test-canvas-extraction.py --dry-run
if [ $? -ne 0 ]; then
    print_error "Canvas data extraction test failed"
    exit 1
fi
print_success "Canvas data extraction test passed"

# Test 2: Start Backend
print_header "Test 2: Backend Server"
print_info "Starting backend server..."

# Kill any existing process on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
sleep 1

# Start server in background
uv run uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for server to start
print_info "Waiting for server to start (PID: $BACKEND_PID)..."
MAX_WAIT=15
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Backend server started"
        break
    fi
    sleep 1
    WAITED=$((WAITED + 1))
done

if [ $WAITED -eq $MAX_WAIT ]; then
    print_error "Backend server failed to start within ${MAX_WAIT} seconds"
    exit 1
fi

# Test 3: Health Check
print_header "Test 3: Health Check"
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    print_success "Health check passed: $HEALTH_RESPONSE"
else
    print_error "Health check failed: $HEALTH_RESPONSE"
    exit 1
fi

# Test 4: Authentication Endpoint
print_header "Test 4: Authentication Endpoint"
print_info "Testing login endpoint (expecting 401 for invalid credentials)..."
AUTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST http://localhost:8000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"invalid"}')  # pragma: allowlist secret

if [ "$AUTH_CODE" = "401" ]; then
    print_success "Authentication endpoint working correctly (returns 401)"
else
    print_error "Authentication endpoint returned unexpected status: $AUTH_CODE"
    exit 1
fi

# Test 5: Protected Endpoints
print_header "Test 5: Protected Endpoints"
print_info "Testing protected endpoint (expecting 401/403)..."
PROTECTED_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    http://localhost:8000/api/canvas/courses)

if [ "$PROTECTED_CODE" = "401" ] || [ "$PROTECTED_CODE" = "403" ]; then
    print_success "Protected endpoints require authentication"
else
    print_error "Protected endpoint returned unexpected status: $PROTECTED_CODE"
    exit 1
fi

# Test 6: Frontend Build
print_header "Test 6: Frontend Build"
print_info "Building frontend..."
cd canvas-react

# Create .env.local
echo "VITE_API_ENDPOINT=http://localhost:8000" > .env.local

# Install if needed
if [ ! -d "node_modules" ]; then
    npm install
fi

npm run build
if [ $? -ne 0 ]; then
    print_error "Frontend build failed"
    cd ..
    exit 1
fi

# Verify build output
if [ ! -f "dist/index.html" ]; then
    print_error "Frontend build did not create dist/index.html"
    cd ..
    exit 1
fi

print_success "Frontend build successful"
cd ..

# Summary
print_header "Integration Test Summary"
echo ""
print_success "✅ Test 1: Canvas Data Extraction - PASSED"
print_success "✅ Test 2: Backend Server Startup - PASSED"
print_success "✅ Test 3: Health Check - PASSED"
print_success "✅ Test 4: Authentication Endpoint - PASSED"
print_success "✅ Test 5: Protected Endpoints - PASSED"
print_success "✅ Test 6: Frontend Build - PASSED"
echo ""
print_success "🎉 All integration tests passed!"
echo ""

exit 0
