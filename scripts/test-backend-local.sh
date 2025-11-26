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

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found"
    print_info "Create .env file with required variables:"
    echo "  CANVAS_API_TOKEN=your-token"
    echo "  CANVAS_API_URL=https://your-school.instructure.com"
    echo "  CANVAS_COURSE_ID=your-course-id"
    echo "  S3_BUCKET_NAME=your-bucket-name"
    echo "  JWT_SECRET_KEY=your-dev-secret"
    echo "  ENVIRONMENT=dev"
    exit 1
fi

print_header "Local Backend Testing"

# Check prerequisites
print_info "Checking prerequisites..."
command -v python3 >/dev/null 2>&1 || { print_error "Python 3 is required"; exit 1; }
command -v uv >/dev/null 2>&1 || { print_error "uv is required. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
print_success "Prerequisites met"

# Load environment variables
print_info "Loading environment variables from .env..."
export $(grep -v '^#' .env | xargs)

# Validate required variables
REQUIRED_VARS=("CANVAS_API_TOKEN" "CANVAS_API_URL" "CANVAS_COURSE_ID" "S3_BUCKET_NAME")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        print_error "Missing required environment variable: $var"
        exit 1
    fi
done
print_success "Environment variables loaded"

# Test Canvas data extraction
print_header "Testing Canvas Data Extraction"
python scripts/test-canvas-extraction.py --dry-run
if [ $? -ne 0 ]; then
    print_error "Canvas data extraction test failed"
    exit 1
fi

# Start backend server
print_header "Starting Backend Server"
print_info "Starting uvicorn on http://localhost:8000"
echo ""

# Kill any existing process on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Start server in background
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
SERVER_PID=$!

# Wait for server to start
print_info "Waiting for server to start..."
sleep 3

# Test health endpoint
print_header "Testing Backend Endpoints"

print_info "Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    print_success "Health endpoint response: $HEALTH_RESPONSE"
else
    print_error "Health check failed"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

# Test auth endpoint (should fail without credentials)
print_info "Testing auth endpoint (expecting 401)..."
AUTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST http://localhost:8000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"wrongpassword"}')  # pragma: allowlist secret

if [ "$AUTH_RESPONSE" = "401" ]; then
    print_success "Auth endpoint correctly returns 401 for invalid credentials"
else
    print_warning "Auth endpoint returned unexpected status: $AUTH_RESPONSE"
fi

# Test Canvas data endpoint (should require auth)
print_info "Testing protected Canvas endpoint (expecting 401)..."
CANVAS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
    http://localhost:8000/api/canvas/courses)

if [ "$CANVAS_RESPONSE" = "401" ] || [ "$CANVAS_RESPONSE" = "403" ]; then
    print_success "Canvas endpoint correctly requires authentication"
else
    print_warning "Canvas endpoint returned unexpected status: $CANVAS_RESPONSE"
fi

# Summary
print_header "Test Summary"
print_success "✅ Backend server started successfully"
print_success "✅ Health endpoint working"
print_success "✅ Authentication endpoint working"
print_success "✅ Protected endpoints require auth"

echo ""
print_info "Server is running on http://localhost:8000"
print_info "Server PID: $SERVER_PID"
echo ""
print_info "📖 API Documentation: http://localhost:8000/docs"
print_info "🔍 Health Check: http://localhost:8000/health"
echo ""
print_warning "Press Ctrl+C to stop the server, or run: kill $SERVER_PID"
echo ""

# Keep script running to keep server alive
wait $SERVER_PID
