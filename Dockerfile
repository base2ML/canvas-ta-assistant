# Multi-stage Dockerfile for Vibey Canvas
# Stage 1: Build React frontend
# Stage 2: Python backend + serve static files

# ============================================
# Stage 1: Build React Frontend
# ============================================
FROM node:20-alpine AS frontend-builder

WORKDIR /canvas-react

# Copy package files
COPY canvas-react/package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY canvas-react/ ./

# Build production bundle
RUN npm run build

# ============================================
# Stage 2: Python Backend + Static Serving
# ============================================
FROM python:3.11-slim

WORKDIR /backend-canvas-fastapi

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy backend dependency files
COPY backend-canvas-fastapi/pyproject.toml backend-canvas-fastapi/uv.lock* ./

# Install Python dependencies using uv
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy backend application code (all Python modules, routers, and services)
COPY backend-canvas-fastapi/main.py ./
COPY backend-canvas-fastapi/config.py ./
COPY backend-canvas-fastapi/dependencies.py ./
COPY backend-canvas-fastapi/models.py ./
COPY backend-canvas-fastapi/routers ./routers
COPY backend-canvas-fastapi/services ./services

# Copy React build from frontend stage
COPY --from=frontend-builder /canvas-react/dist ./static

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
