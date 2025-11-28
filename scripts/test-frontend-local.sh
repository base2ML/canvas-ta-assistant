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

print_header "Local Frontend Testing"

# Check prerequisites
print_info "Checking prerequisites..."
command -v npm >/dev/null 2>&1 || { print_error "npm is required"; exit 1; }
command -v node >/dev/null 2>&1 || { print_error "Node.js is required"; exit 1; }
print_success "Prerequisites met"

# Check if backend is running
print_info "Checking if backend is running..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    print_success "Backend is running on http://localhost:8000"
    BACKEND_URL="http://localhost:8000"
else
    print_warning "Backend is not running on port 8000"
    print_info "Frontend will use mock API endpoint"
    print_info "To start the backend, run: ./scripts/test-backend-local.sh"
    BACKEND_URL="http://localhost:8000"  # Still point to local, user can start later
fi

# Navigate to frontend directory
cd canvas-react

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    print_info "Installing dependencies..."
    npm install
    print_success "Dependencies installed"
else
    print_success "Dependencies already installed"
fi

# Create temporary .env.local for development
print_info "Creating .env.local with local API endpoint..."
cat > .env.local << EOF
VITE_API_ENDPOINT=${BACKEND_URL}
EOF

# Build frontend
print_header "Building Frontend"
npm run build
if [ $? -ne 0 ]; then
    print_error "Frontend build failed"
    exit 1
fi
print_success "Frontend built successfully"

# Start dev server
print_header "Starting Frontend Dev Server"
print_info "Starting Vite dev server on http://localhost:5173"
echo ""
print_info "📖 API Endpoint: ${BACKEND_URL}"
print_info "🌐 Frontend: http://localhost:5173"
echo ""

if [  "$BACKEND_URL" = "http://localhost:8000" ] && ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    print_warning "Remember to start the backend first:"
    print_warning "  ./scripts/test-backend-local.sh"
    echo ""
fi

# Open browser (macOS only)
if [[ "$OSTYPE" == "darwin"* ]]; then
    print_info "Opening browser..."
    sleep 2 && open http://localhost:5173 &
fi

# Start dev server
npm run dev
