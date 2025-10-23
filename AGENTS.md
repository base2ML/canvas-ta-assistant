# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Canvas LMS TA Dashboard application with a FastAPI backend and React frontend, designed specifically for Teaching Assistants to manage grading workflow and monitor assignment status across courses.

**Backend**: FastAPI application with AWS S3/Lambda integration for Canvas data and Cognito authentication
**Frontend**: React 19.1.1 application built with Vite, styled with Tailwind CSS v4, integrated with AWS Cognito
**Infrastructure**: AWS-based deployment using Terraform with ECS Fargate, S3, Lambda, and Cognito

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
./deploy-infrastructure.sh

# Navigate to terraform directory for manual operations
cd terraform/
terraform plan
terraform apply
```

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

## Architecture

### Backend Structure (AWS-Integrated)
- **main.py**: Single FastAPI application with S3 data integration and Cognito authentication
- **Dependencies**: Uses boto3 for AWS services, FastAPI for REST API, Pydantic for data validation, PyJWT for Cognito token validation
- **Endpoints**:
  - `GET /health` - Health check (simple, no AWS dependencies)
  - `GET /api/canvas/courses` - Get available courses from S3 data
  - `POST /api/assignments` - Fetch assignments from S3 data (Canvas data refreshed via Lambda)
  - `POST /api/assignment/{id}/details` - Get detailed assignment information from S3
  - `POST /api/ta-groups/{course_id}` - Fetch TA groups from S3 data
  - `POST /api/ta-grading` - Get ungraded submissions with TA assignment information from S3
- **Authentication**: AWS Cognito JWT token validation for all API endpoints
- **Data Source**: S3 bucket with Canvas data refreshed every 15 minutes by Lambda function
- **Deployment**: ECS Fargate containers behind Application Load Balancer

### Frontend Structure (Cognito-Integrated)
- **React 19.1.1** with Vite build system
- **AWS Amplify** for Cognito authentication integration
- **Tailwind CSS v4** for styling (configured as dev dependency via @tailwindcss/vite)
- **Lucide React** for icons
- **Modern Hooks**: Uses useCallback, useEffect, useState with proper dependency arrays
- **ESLint**: Configured with react-hooks rules and modern JavaScript standards
- **Components**:
  - `App.jsx` - Main TA dashboard with Cognito authentication and S3 data integration
  - `AuthWrapper.jsx` - Cognito authentication wrapper component
  - `TAGradingDashboard.jsx` - Specialized TA grading management interface
  - `LateDaysTracking.jsx` - Late days tracking component
  - `PeerReviewTracking.jsx` - Peer review tracking component
- **Features**:
  - AWS Cognito user authentication with JWT tokens
  - Assignment status tracking with due dates and direct Canvas links
  - TA grading dashboard with workload distribution across TA groups
  - Course and assignment filtering for efficient workflow
  - S3-based Canvas data integration (no direct Canvas API calls)
  - Dual view system: Assignment List + TA Grading Management

### Data Models
The backend defines comprehensive Pydantic models for:
- AWS Cognito user information and JWT token validation
- Course and assignment information from S3 data
- Assignment status tracking (not_submitted, pending, graded, excused)
- TA groups and grading management (TAGroup, UngradedSubmission, TAGradingResponse)
- S3 data structures and API responses with error handling

### AWS Infrastructure Components
- **Cognito User Pool**: User authentication and JWT token management
- **S3 Bucket**: Canvas data storage with organized structure (course_data/, assignments/, etc.)
- **Lambda Function**: Scheduled Canvas API data refresh every 15 minutes
- **ECS Fargate**: Container hosting with auto-scaling
- **Application Load Balancer**: HTTP/HTTPS traffic routing
- **ECR Repository**: Docker image storage
- **Terraform**: Infrastructure as Code for reproducible deployments

## Package Management

- **Backend**: Uses `uv` package manager with pyproject.toml configuration
- **Frontend**: Uses npm with package.json
- **Backend Python version**: >=3.8.1

## Key Integration Points

- AWS Cognito authentication via JWT tokens
- S3-based Canvas data access with structured JSON storage
- Lambda-scheduled Canvas API data refresh (every 15 minutes)
- Assignment status determination based on S3-stored submission state
- ECS Fargate container orchestration with health checks
- Application Load Balancer for high availability
- Terraform-managed AWS infrastructure

## Environment Setup

### AWS Configuration
The application requires AWS infrastructure deployed via Terraform. Backend automatically detects AWS services via environment variables set by ECS.

### Frontend Environment Variables
The React frontend uses AWS Cognito for authentication. Create a `.env` file in the `canvas-react/` directory:

```bash
# AWS Cognito Configuration - From Terraform Output
VITE_COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
VITE_COGNITO_USER_POOL_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
VITE_API_ENDPOINT=https://your-alb-endpoint.us-east-1.elb.amazonaws.com
```

**Configuration Sources:**
1. **Terraform outputs** - Use `terraform output` to get Cognito User Pool IDs and API endpoints
2. **Environment variables** (.env file) - For local development
3. **aws-config.js** - Contains fallback defaults from deployed infrastructure

**Security Notes:**
- No Canvas API tokens stored in frontend (handled by Lambda function)
- Cognito User Pool IDs are safe to include in frontend code
- Use HTTPS endpoints for production deployments
- JWT tokens are managed automatically by AWS Amplify

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

1. **Configure Canvas API tokens in Lambda environment** (not in frontend)
2. **Use HTTPS ALB endpoints** (automatically configured by Terraform)
3. **Configure CORS** with specific allowed origins in main.py
4. **Enable ECS task security** with least-privilege IAM roles
5. **Use Cognito for all authentication** (no local credential storage)
6. **Review SECURITY.md** for complete deployment checklist
7. **Monitor CloudWatch logs** for security events

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