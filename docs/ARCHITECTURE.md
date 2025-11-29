# Canvas TA Assistant - Serverless AWS Architecture Design

## Executive Summary

**Objective**: Deploy Canvas TA Assistant with lightweight, affordable serverless microservices architecture on AWS with automated CI/CD from GitHub.

**Key Requirements**:
- Serverless-first architecture for cost optimization
- Automated deployment from Git repository
- Single-command deployment capability
- Production-grade security and scalability
- Minimal operational overhead

## Architecture Overview

### Design Principles
- **Serverless-First**: Lambda, API Gateway, S3 instead of ECS/EC2
- **Event-Driven**: Decoupled microservices
- **Cost-Optimized**: Pay-per-use pricing model (~$15-25/month)
- **Infrastructure-as-Code**: 100% Terraform-managed
- **GitOps**: Automated deployments via scripts and CI/CD

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         GitHub Repository                        │
│                  (base2ML/canvas-ta-assistant)                   │
└──────────────────┬──────────────────────────────────────────────┘
                   │ Git Push Trigger
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Deployment Scripts                          │
│  • package-lambda-api.sh • deploy-frontend.sh                   │
│  • Terraform Apply                                              │
└──────────────────┬──────────────────────────────────────────────┘
                   │ Deploy
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                                │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              CloudFront CDN (Frontend)                  │    │
│  │  • React SPA delivery • Edge caching • HTTPS           │    │
│  └──────────────────┬─────────────────────────────────────┘    │
│                     │                                            │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              S3 Bucket (Static Assets)                  │    │
│  │  • React build artifacts • Versioned deployments       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              API Gateway (HTTP API)                     │    │
│  │  • HTTPS endpoints • Rate limiting • CORS              │    │
│  └──────────────────┬─────────────────────────────────────┘    │
│                     │                                            │
│  ┌────────────────────────────────────────────────────────┐    │
│  │         Lambda Functions (Microservices)                │    │
│  │  ┌──────────────────────────────────────────────┐      │    │
│  │  │ API Handler Lambda (FastAPI + Mangum)        │      │    │
│  │  │ • Auth • Course data • Assignments           │      │    │
│  │  └──────────────────────────────────────────────┘      │    │
│  │  ┌──────────────────────────────────────────────┐      │    │
│  │  │ Canvas Data Fetcher Lambda                   │      │    │
│  │  │ • Scheduled Canvas API sync                  │      │    │
│  │  └──────────────────────────────────────────────┘      │    │
│  └─────────────────┬────────────────────┬──────────────────┘    │
│                    │                    │                        │
│  ┌────────────────────────────┐  ┌────────────────────────┐    │
│  │   S3 Bucket (Canvas Data)  │  │      Secrets Manager   │    │
│  │  • JSON data storage       │  │  • Canvas API Token    │    │
│  │  • Lifecycle policies      │  │  • JWT Secret          │    │
│  └────────────────────────────┘  └────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Microservices Architecture

### 1. Frontend Service (Serverless Static Hosting)
**Technology**: React 19 SPA + CloudFront + S3
**Purpose**: User interface delivery

**Components**:
- S3 bucket for static hosting (versioned)
- CloudFront distribution with HTTPS and OAC (Origin Access Control)
- Global CDN for low latency

**Cost**: ~$1-5/month (based on traffic)

### 2. API Service (Lambda + API Gateway)
**Technology**: Python 3.11 Lambda functions + API Gateway HTTP API
**Purpose**: Backend API endpoints

**Endpoints**:
- `GET /api/health` - Health check
- `POST /api/auth/login` - JWT Authentication
- `GET /api/canvas/data/{course_id}` - Get Canvas data

**Lambda Configuration**:
- Runtime: Python 3.11
- Memory: 1024 MB
- Timeout: 30 seconds
- Adapter: Mangum (ASGI adapter)

**Cost**: ~$5-10/month (1M requests free tier, then $0.20/1M)

### 3. Canvas Data Sync Service (Lambda)
**Technology**: Python 3.11 Lambda
**Purpose**: Periodic Canvas API data synchronization

**Functionality**:
- Fetch Canvas data via CanvasAPI library
- Transform and store in S3 (JSON format)
- Error handling and retry logic

**Cost**: ~$1-3/month (based on execution time)

### 4. Data Storage Services

#### S3 Buckets
1. **Frontend Assets Bucket**
   - Static React build files
   - CloudFront origin

2. **Canvas Data Bucket**
   - JSON data from Canvas API
   - Versioning enabled
   - Lifecycle policies for cost optimization

**Cost**: ~$1-3/month

## Infrastructure-as-Code Structure

```
terraform/
├── main.tf                    # Root module orchestration
├── variables.tf               # Input variables
├── outputs.tf                 # Output values
├── modules/
│   ├── frontend/              # CloudFront + S3 for React
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── api-gateway/           # API Gateway + Lambda integration
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── lambda-api/            # Backend Lambda function
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── s3/                    # Data storage buckets
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
```

## Security Architecture

### Network Security
- **API Gateway**: Throttling and rate limiting
- **CloudFront**: HTTPS only, OAC for S3 security
- **CORS**: Strict origin validation in production

### Authentication & Authorization
- **JWT Authentication**: Stateless, secure token-based auth
- **IAM Roles**: Least-privilege principle for all services

### Data Security
- **Encryption at Rest**: S3 (SSE-S3), Secrets Manager
- **Encryption in Transit**: TLS 1.2+ everywhere
- **Secrets Management**: Environment variables injected securely

## Cost Optimization Strategies

### 1. Serverless-First Approach
- **No idle costs**: Pay only for actual usage
- **Auto-scaling**: Handles traffic spikes without over-provisioning
- **Free tiers**: Leverage AWS Free Tier (Lambda, API Gateway, S3)

### 2. Resource Right-Sizing
- **Lambda Memory**: Optimized for performance/cost ratio
- **S3 Lifecycle**: Move old data to cheaper storage classes

## Deployment Process

### 1. Package Backend
```bash
./scripts/package-lambda-api.sh
```

### 2. Deploy Infrastructure
```bash
cd terraform
terraform apply
```

### 3. Deploy Frontend
```bash
./scripts/deploy-frontend.sh
```

## Conclusion

This serverless architecture provides:
- **70-80% cost reduction** compared to ECS Fargate
- **Simplified operations** (no Docker management, no cluster patching)
- **Production-grade security** with JWT and AWS IAM
- **Infinite scalability** with pay-per-use pricing

The design balances affordability, scalability, and maintainability while maintaining professional quality standards for educational technology applications.
