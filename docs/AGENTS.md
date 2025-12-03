# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Canvas LMS TA Dashboard application with a FastAPI backend and React frontend, designed specifically for Teaching Assistants to manage grading workflow and monitor assignment status across courses.

**Backend**: FastAPI application with AWS S3/Lambda integration for Canvas data and custom JWT authentication
**Frontend**: React 19.1.1 application built with Vite 7.1.2, styled with Tailwind CSS v4, deployed to CloudFront
**Infrastructure**: Fully serverless AWS deployment using Terraform with Lambda, API Gateway, CloudFront, S3, Secrets Manager, and CloudWatch

## Modern Development Stack

- **Frontend Build Tool**: Vite (fast, modern build tool replacing Create React App)
- **CSS Framework**: Tailwind CSS v4 (latest version with modern features)
- **React**: 19.1.1 with modern hooks and concurrent features
- **Icons**: Lucide React for consistent iconography
- **Linting**: ESLint 9.x with modern configuration

## Development Commands

### Backend (FastAPI)
Run from project root directory:

```bash
# Install dependencies using uv
uv sync

# Run development server locally
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Run with Python directly
uv run python main.py

# Code formatting and linting with Ruff
uv run ruff check .           # Lint code
uv run ruff check . --fix     # Lint and auto-fix
uv run ruff format .          # Format code
uv run mypy .                 # Type checking

# Testing
uv run pytest
```

### Infrastructure Deployment
```bash
# Deploy complete AWS infrastructure with Terraform
./deploy.sh

# Navigate to terraform directory for manual operations
cd terraform/
terraform plan
terraform apply
```

### CI/CD Pipeline (GitHub Actions)
The project includes automated CI/CD workflows:

- **ci.yml**: Continuous integration with linting, testing, and code quality checks
- **deploy.yml**: Full deployment pipeline for infrastructure and application
- **deploy-lambda.yml**: Specialized Lambda function deployment workflow

**Automated Deployments:**
- Triggered on push to `dev-*` and `main` branches
- Runs tests, builds frontend, packages Lambda functions
- Deploys Terraform infrastructure changes
- Updates Lambda function code and CloudFront distributions
- Runs post-deployment validation tests

### Utility Scripts (scripts/ directory)

**Deployment Scripts:**
- `package-lambda-api.sh` - Package main FastAPI application for Lambda deployment
- `package-lambda-refresh.sh` - Package Canvas data fetcher Lambda function
- `deploy-frontend.sh` - Deploy frontend to S3/CloudFront (if applicable)
- `setup-backend.sh` - Initialize backend development environment

**Testing Scripts:**
- `test-backend-local.sh` - Run backend tests locally with coverage
- `test-frontend-local.sh` - Run frontend tests locally
- `test-integration.sh` - Run end-to-end integration tests
- `test-canvas-extraction.py` - Test Canvas API data extraction logic

**Management Scripts:**
- `manage_users.py` - User management utilities (create, delete, update users)
- `cleanup-dev-resources.sh` - Clean up development AWS resources

### Frontend (React + Vite)
Navigate to `canvas-react/` directory:

```bash
# Install dependencies
npm install

# Start Vite development server (http://localhost:5173)
npm run dev

# Build for production (outputs to dist/)
npm run build

# Preview production build
npm run preview

# Run ESLint
npm run lint

# Run tests (if configured)
npm test
```

## Project Structure

```
cda-ta-dashboard/
├── canvas-react/              # Frontend React application
│   ├── src/
│   │   ├── components/        # Reusable UI components
│   │   ├── hooks/             # Custom React hooks
│   │   ├── EnhancedTADashboard.jsx
│   │   ├── SimpleDashboard.jsx
│   │   ├── TAGradingDashboard.jsx
│   │   ├── LateDaysTracking.jsx
│   │   └── PeerReviewTracking.jsx
│   └── package.json           # Frontend dependencies
├── lambda/                    # Lambda function code
│   ├── canvas_data_fetcher.py # Canvas API data refresh Lambda
│   ├── lambda_function.py     # Lambda entry point
│   └── requirements.txt       # Lambda dependencies
├── scripts/                   # Utility and deployment scripts
├── terraform/                 # Infrastructure as Code
│   ├── modules/               # Terraform modules
│   ├── environments/          # Environment-specific configs
│   ├── main.tf                # Main Terraform configuration
│   ├── variables.tf           # Terraform variables
│   └── outputs.tf             # Terraform outputs
├── .github/workflows/         # GitHub Actions CI/CD pipelines
├── main.py                    # FastAPI backend application
├── auth.py                    # Authentication module
├── sync_canvas_data.py        # Canvas data sync script (local dev)
├── pyproject.toml             # Backend dependencies (uv)
├── deploy.sh                  # Main deployment script
└── AGENTS.md                  # This file - Claude Code documentation
```

## Architecture

### Backend Structure (AWS-Integrated)
- **main.py**: Single FastAPI application with S3 data integration and custom authentication
- **auth.py**: Custom authentication module with JWT token validation
- **Dependencies**: Uses boto3 for AWS services, FastAPI for REST API, Pydantic for data validation, PyJWT for token validation, bcrypt for password hashing
- **Endpoints**:
  - `GET /health` - Health check (simple, no AWS dependencies)
  - `GET /api/health` - Detailed health check with response model
  - **Authentication endpoints**:
    - `POST /api/auth/login` - User authentication with JWT token generation
    - `POST /api/auth/logout` - User logout
    - `GET /api/auth/me` - Get current authenticated user information
  - **Canvas data endpoints**:
    - `GET /api/canvas/courses` - Get available courses from S3 data
    - `GET /api/canvas/data/{course_id}` - Get complete course data from S3
    - `GET /api/canvas/assignments/{course_id}` - Fetch assignments from S3 data
    - `GET /api/canvas/submissions/{course_id}` - Get submissions for a course
    - `GET /api/canvas/users/{course_id}` - Get users enrolled in a course
    - `GET /api/canvas/groups/{course_id}` - Get TA groups from S3 data
    - `POST /api/canvas/sync` - Trigger Canvas data synchronization
  - **Dashboard endpoints**:
    - `GET /api/dashboard/submission-status/{course_id}` - Get submission status breakdown
    - `GET /api/dashboard/ta-grading/{course_id}` - Get ungraded submissions with TA assignment information
  - **User and configuration**:
    - `GET /api/user/profile` - Get user profile information
    - `GET /api/config` - Get application configuration
    - `GET /api/courses` - Get list of available courses
- **Authentication**: Custom JWT token-based authentication with bcrypt password hashing
- **Data Source**: S3 bucket with Canvas data refreshed every 15 minutes by Lambda function
- **Deployment**: Serverless deployment with AWS Lambda behind API Gateway

### Frontend Structure (Authentication-Integrated)
- **React 19.1.1** with Vite 7.1.2 build system
- **Custom Authentication** using JWT tokens (no AWS Amplify dependency)
- **Tailwind CSS v4** for styling (configured as dev dependency via @tailwindcss/vite)
- **Lucide React** for icons
- **Modern Hooks**: Uses useCallback, useEffect, useState with proper dependency arrays
- **ESLint 9.x**: Configured with react-hooks rules and modern JavaScript standards
- **Main Dashboard Views**:
  - `App.jsx` - Basic TA dashboard entry point
  - `EnhancedTADashboard.jsx` - Advanced TA dashboard with enhanced features
  - `SimpleDashboard.jsx` - Simplified dashboard view
  - `TAGradingDashboard.jsx` - Specialized TA grading management interface
- **Tracking Components**:
  - `LateDaysTracking.jsx` - Late days tracking component
  - `PeerReviewTracking.jsx` - Peer review tracking component
- **Authentication Components** (in components/):
  - `AuthWrapper.jsx` - Full authentication wrapper with login/logout
  - `SimpleAuthWrapper.jsx` - Simplified authentication wrapper
  - `LoginForm.jsx` - Login form component
- **UI Components** (in components/):
  - `AssignmentStatusBreakdown.jsx` - Assignment status visualization
  - `SubmissionStatusCards.jsx` - Submission status card components
- **Features**:
  - Custom JWT-based user authentication
  - Assignment status tracking with due dates and direct Canvas links
  - TA grading dashboard with workload distribution across TA groups
  - Course and assignment filtering for efficient workflow
  - S3-based Canvas data integration (no direct Canvas API calls)
  - Multiple dashboard views: Basic, Enhanced, Simple, and TA Grading

### Data Models
The backend defines comprehensive Pydantic models for:
- User authentication and JWT token validation (LoginRequest, LoginResponse, UserProfile)
- Health check responses (HealthResponse)
- Course and assignment information from S3 data
- Assignment status tracking (not_submitted, pending, graded, excused)
- TA groups and grading management (TAGroup, UngradedSubmission, TAGradingResponse)
- S3 data structures and API responses with error handling
- Configuration models for application settings

### AWS Infrastructure Components
- **Lambda Functions**:
  - Main API backend (main.py) - FastAPI application handling all API endpoints
  - Canvas data fetcher (canvas_data_fetcher.py) - Scheduled Canvas API data refresh every 15 minutes
- **API Gateway**: REST API endpoint routing with custom domain support
- **CloudFront**: CDN for frontend React application with HTTPS support
- **S3 Buckets**:
  - Canvas data storage with organized structure (course_data/, assignments/, etc.)
  - Frontend static asset hosting
- **Secrets Manager**: Secure storage for Canvas API tokens, JWT secrets, and credentials
- **CloudWatch**:
  - Lambda function logs and metrics
  - EventBridge rules for scheduled Lambda executions
- **Route 53**: DNS management and custom domain routing (optional)
- **Terraform**: Infrastructure as Code for reproducible deployments with modular structure

## Package Management

- **Backend**: Uses `uv` package manager with pyproject.toml configuration
- **Frontend**: Uses npm with package.json
- **Backend Python version**: >=3.8.1

## Key Integration Points

- Custom JWT-based authentication with bcrypt password hashing
- S3-based Canvas data access with structured JSON storage
- Lambda-scheduled Canvas API data refresh (every 15 minutes via canvas_data_fetcher.py)
- Assignment status determination based on S3-stored submission state
- Fully serverless architecture: Lambda + API Gateway + CloudFront
- Health check endpoints for monitoring Lambda functions
- Terraform-managed AWS infrastructure with modular design
- AWS Secrets Manager for secure credential storage
- CloudWatch EventBridge for scheduled Canvas data synchronization

## Environment Setup

### AWS Configuration
The application requires AWS infrastructure deployed via Terraform. Backend Lambda functions automatically detect AWS services via environment variables set by Lambda execution environment.

### Frontend Environment Variables
The React frontend uses custom JWT authentication. Create a `.env` file in the `canvas-react/` directory:

```bash
# API Configuration - From Terraform Output or Local Development
VITE_API_ENDPOINT=https://your-api-endpoint.amazonaws.com
# For local development:
# VITE_API_ENDPOINT=http://localhost:8000
```

**Configuration Sources:**
1. **Terraform outputs** - Use `terraform output` to get API endpoints
2. **Environment variables** (.env file) - For local development
3. **aws-config.js** - Contains fallback defaults from deployed infrastructure

**Security Notes:**
- No Canvas API tokens stored in frontend (handled by Lambda function)
- User credentials handled via POST /api/auth/login endpoint
- Use HTTPS endpoints for production deployments
- JWT tokens are stored in browser localStorage and included in API request headers

### Deployed Environments

The application is deployed to two environments with automated CI/CD from GitHub:

**Development Environment:**
- **URL**: https://ta-dashboard-isye6740-dev.base2ml.com/
- **Branch**: `dev-*` branches
- **Purpose**: Testing and development features before production
- **Auto-deploy**: Triggered on push to any `dev-*` branch

**Production Environment:**
- **URL**: https://ta-dashboard-isye6740-prod.base2ml.com/
- **Branch**: `main`
- **Purpose**: Stable production deployment for end users
- **Auto-deploy**: Triggered on push to `main` branch

**Deployment Pipeline:**
- GitHub Actions workflows handle automated deployment
- Frontend built with Vite and deployed to CloudFront
- Backend Lambda functions updated automatically
- See `.github/workflows/deploy.yml` for pipeline details

## Security Best Practices

**CRITICAL**: This application handles sensitive student data (names, grades, submissions) and Canvas API credentials. Always follow security best practices.

### Pre-commit Hooks (REQUIRED)

Before making any commits, install pre-commit hooks to prevent accidental secret exposure:

```bash
# Install pre-commit package
pip install pre-commit

# Install hooks in repository
pre-commit install

# Test hooks (optional)
pre-commit run --all-files
```

### Security Checklist for Development

- [ ] **Never commit `.env` files** - they contain Canvas API tokens
- [ ] **Never commit Jupyter notebooks** with real Canvas data
- [ ] **Install pre-commit hooks** before first commit
- [ ] **Use placeholder data** in examples and documentation
- [ ] **Regenerate Canvas API tokens** before making repository public
- [ ] **Check git status** before commits to verify no sensitive files staged
- [ ] **Review SECURITY.md** for complete guidelines

### What NOT to Commit

❌ **Files:**
- `.env`, `.env.local`, `.env.production` (any environment files with real credentials)
- `Canvas_API.ipynb` or any notebooks with real Canvas data
- Screenshots with student names, IDs, or grades
- API tokens, passwords, or private keys
- Database dumps or backups with real data

❌ **In Code:**
- Hardcoded API tokens or credentials
- Student names, IDs, or email addresses in comments
- Real course IDs or assignment IDs in examples
- Debug statements that log sensitive data

✅ **Always Use:**
- `.env.example` files with placeholder values
- Generic examples (e.g., "your-token-here", "12345")
- Anonymized data for testing and documentation
- Environment variables for all credentials

### Data Privacy

This application accesses protected student data under FERPA:
- **Student names and IDs**: Personally identifiable information
- **Grades and submissions**: Educational records
- **Course enrollment**: Student status information

When developing:
- Use test courses with fake students when possible
- Never share screenshots or logs with real student data
- Anonymize data in bug reports and documentation
- Minimize data caching (follow TTL settings in `config.py`)

### Production Deployment Security

Before deploying to production:

1. **Configure Canvas API tokens in Lambda environment via Secrets Manager** (not in frontend)
2. **Use HTTPS endpoints** via API Gateway custom domain with CloudFront
3. **Configure CORS** with specific allowed origins in main.py Lambda handler
4. **Enable least-privilege IAM roles** for Lambda functions with minimal permissions
5. **Use JWT token authentication** with secure secret keys stored in Secrets Manager
6. **Configure bcrypt password hashing** for user credentials
7. **Enable API Gateway throttling** to prevent abuse and DDoS attacks
8. **Configure CloudFront WAF** for web application firewall protection (optional)
9. **Review SECURITY.md** for complete deployment checklist
10. **Monitor CloudWatch logs** for security events, authentication failures, and Lambda errors

### Security Resources

- **[SECURITY.md](SECURITY.md)**: Complete security guidelines and policies
- **[README.md](README.md)**: Quick start and setup instructions
- **Canvas API Docs**: https://canvas.instructure.com/doc/api/
- **FERPA Guidelines**: https://www2.ed.gov/policy/gen/guid/fpco/ferpa/index.html

## Development Guidelines

### Using Context7 MCP Server for Modern Coding Practices

When working with this codebase, leverage the Context7 MCP server to ensure modern, up-to-date coding practices:

#### For React/Frontend Development
Use Context7 to get the latest documentation and best practices for:
- **React 19.1.1**: `resolve-library-id "react"` then `get-library-docs` for latest hooks, concurrent features, and patterns
- **Vite**: `resolve-library-id "vite"` for modern build configuration and optimization
- **Tailwind CSS v4**: `resolve-library-id "tailwindcss"` for latest utility classes and configuration
- **Lucide React**: `resolve-library-id "lucide-react"` for icon usage and best practices

#### For Backend Development  
Use Context7 to get current documentation for:
- **FastAPI**: `resolve-library-id "fastapi"` for latest async patterns, dependency injection, and API design
- **Pydantic**: `resolve-library-id "pydantic"` for v2 models, validation, and serialization
- **Python AsyncIO**: `resolve-library-id "asyncio"` for modern concurrent programming patterns

#### Key Areas to Validate with Context7
1. **React Hooks**: Ensure proper useCallback, useEffect dependency arrays, and modern patterns
2. **Vite Configuration**: Verify build optimizations and plugin usage
3. **Tailwind v4**: Check for latest utility classes and configuration options
4. **FastAPI Async**: Confirm modern async/await patterns and error handling
5. **TypeScript/ESLint**: Validate modern linting rules and type safety

#### Best Practices to Follow
- Always use Context7 before implementing new features to get latest syntax
- Check for deprecation warnings and modern alternatives
- Validate dependency management and security practices
- Ensure accessibility and performance best practices

#### Example Context7 Usage
```bash
# Before adding new React features
resolve-library-id "react"
get-library-docs "/facebook/react" topic:"hooks"

# Before modifying Vite config
resolve-library-id "vite"
get-library-docs "/vitejs/vite" topic:"configuration"

# Before styling changes
resolve-library-id "tailwindcss"
get-library-docs "/tailwindlabs/tailwindcss" topic:"utilities"
```
- Ensure that any logging is done via Loguru following all best practices. Do not use print statements directly in code
- Canvas API integration is handled by the Lambda function, not directly in the main application
- The full documentation for CanvasAPI can be found here: https://canvasapi.readthedocs.io/en/stable/
- AWS SDK documentation for Python: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
- Terraform AWS Provider documentation: https://registry.terraform.io/providers/hashicorp/aws/latest/docs
