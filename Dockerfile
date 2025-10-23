# Enhanced Dockerfile for Canvas TA Dashboard with S3 and Cognito integration
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

# Copy React app files
COPY canvas-react/package*.json ./
RUN npm ci

COPY canvas-react/ ./
RUN npm run build

# Python backend stage
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster Python package management
RUN pip install --no-cache-dir uv

# Copy Python dependencies
COPY pyproject.toml uv.lock* ./

# Install Python dependencies
RUN uv pip install --system --no-cache -r pyproject.toml

# Install additional dependencies for S3 and Cognito integration
RUN uv pip install --system --no-cache boto3 PyJWT cryptography

# Copy backend application code
COPY main.py ./

# Copy static files from frontend build
COPY --from=frontend-builder /frontend/dist ./static

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]