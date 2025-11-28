# CDA TA Dashboard

A Canvas LMS Teaching Assistant Dashboard application designed to streamline grading workflow and monitor assignment status across courses.

## Features

- **Assignment Tracking**: Monitor assignment status with due dates and direct Canvas links
- **TA Grading Management**: Specialized dashboard for workload distribution across TA groups
- **Course Filtering**: Efficient workflow with course and assignment filtering
- **Real-time Integration**: Direct Canvas API integration for up-to-date information
- **Dual View System**: Assignment List + TA Grading Management interfaces

## Architecture

### Backend (Serverless)
- **AWS Lambda**: Python 3.11 runtime (via Mangum adapter)
- **API Gateway**: HTTP API for REST endpoints
- **FastAPI**: Modern async web framework
- **canvasapi**: Official Canvas LMS Python library
- **Pydantic v2**: Data validation and settings management
- **Loguru**: Structured logging

### Frontend (Static Hosting)
- **AWS CloudFront**: Global CDN for content delivery
- **AWS S3**: Static website hosting
- **React 19.1.1**: Modern UI library with concurrent features
- **Vite**: Fast, modern build tool
- **Tailwind CSS v4**: Utility-first CSS framework

## Quick Start

### Prerequisites

- **Python 3.11+** (backend)
- **Node.js 18+** (frontend)
- **uv** package manager (recommended for Python)
- **Terraform 1.0+** (infrastructure)
- **AWS CLI** (configured with credentials)
- **Canvas LMS API Token** ([How to generate](SECURITY.md#generating-canvas-api-tokens))

### Local Development

#### Backend

```bash
# Install dependencies
uv pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env with your Canvas credentials
# CANVAS_API_TOKEN=your-token-here
# CANVAS_BASE_URL=https://your-school.instructure.com
# CANVAS_COURSE_ID=your-course-id

# Run development server
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Backend will be available at `http://localhost:8000`

#### Frontend

```bash
cd canvas-react

# Install dependencies
npm install

# Create .env file
cp .env.example .env
# Edit .env:
# VITE_API_ENDPOINT=http://localhost:8000/api

# Start development server
npm run dev
```

Frontend will be available at `http://localhost:5173`

## Local Testing

Before deploying to AWS, test locally to ensure everything works:

### Test Canvas Data Extraction

```bash
# Test Canvas API connection (quick)
python scripts/test-canvas-extraction.py --dry-run

# Full data extraction test (saves to test_output/)
python scripts/test-canvas-extraction.py
```

### Test Backend Locally

```bash
# Start backend server and run tests
./scripts/test-backend-local.sh

# Server runs on http://localhost:8000
# Press Ctrl+C to stop
```

### Test Frontend Locally

```bash
# Build and run frontend with local backend
./scripts/test-frontend-local.sh

# Opens browser to http://localhost:5173
```

### Run Full Integration Tests

```bash
# End-to-end test (backend + frontend + Canvas)
./scripts/test-integration.sh

# Tests:
# 1. Canvas API connectivity
# 2. Backend server startup
# 3. Health checks
# 4. Authentication
# 5. Frontend build
```

## Deployment

The application can be deployed manually or via GitHub Actions CI/CD.

### Option 1: GitHub Actions (Recommended)

Automated deployment via Git push:

```bash
# Push to main branch → deploys to production
git push origin main

# Push to development branch → deploys to dev
git push origin development
```

The GitHub Actions workflow will:
1. Run all tests (CI pipeline)
2. Deploy infrastructure with Terraform
3. Update Lambda function code
4. Deploy frontend to S3 + CloudFront
5. Run post-deployment health checks

**Required GitHub Secrets**:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `CANVAS_API_TOKEN` (optional, for Canvas data extraction tests)
- `CANVAS_API_URL`
- `CANVAS_COURSE_ID`

### Option 2: Manual Deployment

One-command deployment:

```bash
./deploy.sh
```

Or step-by-step:

1.  **Package Backend**:
    ```bash
    ./scripts/package-lambda-api.sh
    ```

2.  **Deploy Infrastructure**:
    ```bash
    cd terraform
    terraform init
    terraform apply
    ```

3.  **Deploy Frontend**:
    ```bash
    # Get outputs from Terraform first
    export FRONTEND_BUCKET=$(cd terraform && terraform output -raw frontend_bucket_name)
    export CLOUDFRONT_DISTRIBUTION_ID=$(cd terraform && terraform output -raw cloudfront_distribution_id)
    export VITE_API_ENDPOINT=$(cd terraform && terraform output -raw api_gateway_url)

    # Create env file
    echo "VITE_API_ENDPOINT=$VITE_API_ENDPOINT" > canvas-react/.env.production

    # Run deploy script
    ./scripts/deploy-frontend.sh
    ```

## Security

⚠️ **IMPORTANT**: This application handles sensitive student data and Canvas API credentials.

### Key Security Features
- **JWT Authentication**: Secure stateless authentication
- **Rate Limiting**: Protection against brute-force attacks
- **Environment Validation**: Strict checks for required secrets
- **CORS Protection**: Strict origin validation in production
- **Least Privilege**: IAM roles with minimal permissions

### Before Using

1. **Read [SECURITY.md](SECURITY.md)** for complete security guidelines
2. **Never commit** `.env` files or API tokens to version control
3. **Regenerate** Canvas API tokens before deploying to production
4. **Configure CORS** properly for production (not `*`)

## Project Structure

```
cda-ta-dashboard/
├── main.py                     # FastAPI application entry point
├── auth.py                     # Authentication logic
├── lambda/                     # Lambda functions
│   └── canvas_data_fetcher.py  # Data sync function
├── canvas-react/               # React frontend
│   ├── src/
│   │   ├── App.jsx             # Main TA dashboard
│   │   └── aws-config.js       # AWS configuration
│   └── vite.config.js          # Vite configuration
├── terraform/                  # Infrastructure as Code
│   ├── main.tf                 # Root module
│   └── modules/                # Terraform modules
│       ├── api-gateway/        # API Gateway configuration
│       ├── cloudfront/         # CloudFront + S3 configuration
│       ├── lambda-api/         # Backend Lambda configuration
│       └── s3/                 # Data storage S3 buckets
├── scripts/                    # Deployment scripts
│   ├── package-lambda-api.sh   # Backend packaging
│   └── deploy-frontend.sh      # Frontend deployment
└── README.md                   # This file
```

## API Endpoints

### Backend API

- `GET /api/health` - Health check
- `POST /api/auth/login` - User login (JWT)
- `GET /api/canvas/data/{course_id}` - Get cached course data
- `POST /api/canvas/refresh/{course_id}` - Trigger data refresh

Full API documentation available at `/docs` (Swagger UI) when running locally.

## Contributing

### Code Style

- **Python**: Ruff (formatting + linting)
- **JavaScript/React**: ESLint with React hooks rules
- **Commits**: Conventional commits preferred

## License

[Add license information here]

## Support

For security issues, see [SECURITY.md](SECURITY.md) for responsible disclosure.
For bugs and features, please open a GitHub issue.

---

**Maintained by**: CDA TA Dashboard Team
**Last Updated**: 2025-11-26
