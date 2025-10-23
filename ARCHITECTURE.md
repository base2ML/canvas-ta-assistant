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
- **Serverless-First**: Lambda, API Gateway, DynamoDB instead of ECS/EC2
- **Event-Driven**: Decoupled microservices with EventBridge
- **Cost-Optimized**: Pay-per-use pricing model (~$20-50/month for low traffic)
- **Infrastructure-as-Code**: 100% Terraform-managed
- **GitOps**: Automated deployments from GitHub via GitHub Actions

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         GitHub Repository                        │
│                  (base2ML/canvas-ta-assistant)                   │
└──────────────────┬──────────────────────────────────────────────┘
                   │ Git Push Trigger
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      GitHub Actions CI/CD                        │
│  • Build React Frontend • Build Python Backend                  │
│  • Run Tests • Security Scanning • Deploy to AWS                │
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
│  │              API Gateway (REST API)                     │    │
│  │  • HTTPS endpoints • Cognito auth • Rate limiting      │    │
│  └──────────────────┬─────────────────────────────────────┘    │
│                     │                                            │
│  ┌────────────────────────────────────────────────────────┐    │
│  │         Lambda Functions (Microservices)                │    │
│  │  ┌──────────────────────────────────────────────┐      │    │
│  │  │ API Handler Lambda                           │      │    │
│  │  │ • Course data • Assignments • Submissions    │      │    │
│  │  │ • TA grading • Dashboard endpoints           │      │    │
│  │  └──────────────────────────────────────────────┘      │    │
│  │  ┌──────────────────────────────────────────────┐      │    │
│  │  │ Canvas Data Fetcher Lambda                   │      │    │
│  │  │ • Scheduled Canvas API sync (15 min)         │      │    │
│  │  │ • Data transformation & storage              │      │    │
│  │  └──────────────────────────────────────────────┘      │    │
│  └─────────────────┬────────────────────┬──────────────────┘    │
│                    │                    │                        │
│  ┌────────────────────────────┐  ┌────────────────────────┐    │
│  │   S3 Bucket (Canvas Data)  │  │  DynamoDB Tables       │    │
│  │  • JSON data storage       │  │  • User sessions       │    │
│  │  • Lifecycle policies      │  │  • Cache data          │    │
│  │  • Versioning enabled      │  │  • TA assignments      │    │
│  └────────────────────────────┘  └────────────────────────┘    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │           Cognito User Pool (Auth)                      │    │
│  │  • User authentication • JWT tokens • MFA support      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │         EventBridge (Event Orchestration)               │    │
│  │  • Scheduled Canvas sync (rate(15 minutes))            │    │
│  │  • Event-driven workflows • Dead letter queue          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │         CloudWatch (Observability)                      │    │
│  │  • Logs • Metrics • Alarms • Dashboards                │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │      Secrets Manager (Credentials)                      │    │
│  │  • Canvas API token • Database credentials             │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Microservices Architecture

### 1. Frontend Service (Serverless Static Hosting)
**Technology**: React 19 SPA + CloudFront + S3
**Purpose**: User interface delivery

**Components**:
- S3 bucket for static hosting (versioned)
- CloudFront distribution with HTTPS
- Route 53 for custom domain (optional)

**Cost**: ~$1-5/month (based on traffic)

### 2. API Service (Lambda + API Gateway)
**Technology**: Python 3.11 Lambda functions + API Gateway REST API
**Purpose**: Backend API endpoints

**Endpoints**:
- `GET /api/health` - Health check
- `GET /api/canvas/courses` - List available courses
- `GET /api/canvas/data/{course_id}` - Get Canvas data
- `GET /api/canvas/assignments/{course_id}` - Get assignments
- `GET /api/canvas/submissions/{course_id}` - Get submissions
- `GET /api/dashboard/ta-grading/{course_id}` - TA grading dashboard

**Lambda Configuration**:
- Runtime: Python 3.11
- Memory: 512 MB
- Timeout: 30 seconds (API endpoints)
- Concurrency: 10 reserved (cost control)

**Cost**: ~$5-15/month (1M requests free tier, then $0.20/1M)

### 3. Canvas Data Sync Service (Lambda + EventBridge)
**Technology**: Python 3.11 Lambda + EventBridge scheduler
**Purpose**: Periodic Canvas API data synchronization

**Functionality**:
- Fetch Canvas data via CanvasAPI library
- Transform and store in S3 + DynamoDB
- Error handling and retry logic
- Dead letter queue for failed syncs

**Lambda Configuration**:
- Runtime: Python 3.11
- Memory: 1024 MB
- Timeout: 15 minutes
- Schedule: rate(15 minutes)

**Cost**: ~$3-8/month (based on execution time)

### 4. Authentication Service (Cognito)
**Technology**: AWS Cognito User Pool
**Purpose**: User authentication and authorization

**Features**:
- Email/password authentication
- JWT token generation
- Password policies and MFA
- User management

**Cost**: ~$0-5/month (50,000 MAU free tier)

### 5. Data Storage Services

#### S3 Buckets
1. **Frontend Assets Bucket**
   - Static React build files
   - CloudFront origin
   - Lifecycle: 90-day retention

2. **Canvas Data Bucket**
   - JSON data from Canvas API
   - Versioning enabled
   - Lifecycle: 30d Standard → 90d Glacier → 365d deletion

**Cost**: ~$1-3/month (first 5 GB free)

#### DynamoDB Tables
1. **UserSessions** - Session management
2. **TAAssignments** - TA to student mappings
3. **CacheMetadata** - Data freshness tracking

**Configuration**:
- On-demand pricing (serverless)
- Point-in-time recovery enabled
- Encryption at rest

**Cost**: ~$1-5/month (25 GB free tier)

## CI/CD Pipeline Design

### GitHub Actions Workflow

```yaml
# Triggered on: push to main, pull requests, manual dispatch
Stages:
1. Build & Test
   - Install dependencies (Python + Node.js)
   - Run unit tests (pytest, React test)
   - Security scanning (Ruff, npm audit)
   - Build Docker container (for Lambda layer)

2. Infrastructure Deployment (Terraform)
   - Initialize Terraform
   - Plan infrastructure changes
   - Apply infrastructure (auto-approve for main branch)

3. Frontend Deployment
   - Build React production bundle
   - Upload to S3 bucket
   - Invalidate CloudFront cache

4. Backend Deployment
   - Package Lambda functions
   - Update Lambda code via AWS CLI
   - Run smoke tests

5. Validation
   - Health check endpoints
   - Integration tests
   - Performance tests
```

### Deployment Strategy

**Development → Staging → Production**
- **Development**: Auto-deploy on feature branch push
- **Staging**: Auto-deploy on merge to develop
- **Production**: Manual approval required for main branch

**Rollback Strategy**:
- S3 versioning for frontend rollback
- Lambda versions with aliases for backend rollback
- Terraform state locking prevents concurrent modifications

## Infrastructure-as-Code Structure

```
terraform/
├── main.tf                    # Root module orchestration
├── variables.tf               # Input variables
├── outputs.tf                 # Output values
├── terraform.tfvars           # Environment-specific values
├── backend.tf                 # S3 backend for state
├── modules/
│   ├── frontend/              # CloudFront + S3 for React
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── api-gateway/           # API Gateway + Lambda integration
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── lambda/                # Lambda functions
│   │   ├── api-handler/
│   │   └── canvas-sync/
│   ├── data/                  # S3 + DynamoDB
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── cognito/               # Authentication
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── eventbridge/           # Scheduled events
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── monitoring/            # CloudWatch
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
```

## Security Architecture

### Network Security
- **API Gateway**: AWS WAF for DDoS protection
- **CloudFront**: HTTPS only, custom SSL certificate
- **Lambda**: VPC isolation (optional, not required for serverless)

### Authentication & Authorization
- **Cognito User Pool**: Centralized authentication
- **API Gateway Authorizer**: JWT validation
- **IAM Roles**: Least-privilege principle for all services

### Data Security
- **Encryption at Rest**: S3, DynamoDB, Secrets Manager
- **Encryption in Transit**: TLS 1.2+ everywhere
- **Secrets Management**: AWS Secrets Manager for Canvas API token

### Compliance
- **FERPA Compliance**: Student data protection
- **Audit Logging**: CloudTrail for all API calls
- **Data Retention**: Lifecycle policies for PII deletion

## Cost Optimization Strategies

### 1. Serverless-First Approach
- **No idle costs**: Pay only for actual usage
- **Auto-scaling**: Handles traffic spikes without over-provisioning
- **Free tiers**: Leverage AWS Free Tier (Lambda, API Gateway, S3)

### 2. Resource Right-Sizing
- **Lambda Memory**: 512 MB for API (reduces costs vs 1024 MB)
- **Lambda Timeout**: 30s for API, 15min for sync
- **DynamoDB**: On-demand pricing (no capacity planning)

### 3. Data Lifecycle Management
- **S3 Lifecycle Policies**:
  - 30 days: Standard → Standard-IA
  - 90 days: Standard-IA → Glacier
  - 365 days: Deletion
- **CloudWatch Logs**: 7-day retention for non-critical logs

### 4. Caching Strategy
- **CloudFront**: Edge caching reduces origin requests
- **API Gateway Caching**: Optional (adds cost, evaluate need)
- **DynamoDB**: Cache metadata to avoid redundant S3 reads

### 5. Reserved Capacity (Optional)
- Consider for production after usage patterns stabilize
- Lambda reserved concurrency for cost control

## Cost Breakdown Estimate

### Monthly Operating Costs (Low Traffic Scenario)

| Service | Configuration | Estimated Cost |
|---------|--------------|----------------|
| CloudFront | 100 GB data transfer | $8.50 |
| S3 | 10 GB storage + requests | $2.00 |
| API Gateway | 1M API calls | $3.50 |
| Lambda (API) | 1M requests, 512 MB, 1s avg | $5.00 |
| Lambda (Sync) | 2,880 runs/month, 1024 MB, 30s avg | $4.00 |
| DynamoDB | 5 GB storage, on-demand | $3.00 |
| Cognito | 1,000 MAU | $0.00 (free tier) |
| EventBridge | 2,880 events/month | $0.00 (free tier) |
| Secrets Manager | 1 secret | $0.40 |
| CloudWatch | Logs + metrics | $3.00 |
| Route 53 (optional) | Hosted zone + queries | $0.50 |
| **Total** | | **~$30/month** |

### Scaling Costs
- **10K monthly users**: ~$80-120/month
- **100K monthly users**: ~$400-600/month
- **1M monthly users**: ~$2,000-3,000/month

## Deployment Process

### One-Time Setup (5-10 minutes)
```bash
# 1. Configure AWS credentials
aws configure

# 2. Create S3 bucket for Terraform state
aws s3 mb s3://canvas-ta-terraform-state --region us-east-1

# 3. Set GitHub secrets
# AWS_ACCESS_KEY_ID
# AWS_SECRET_ACCESS_KEY
# CANVAS_API_TOKEN

# 4. Update terraform.tfvars with your values
```

### Single-Command Deployment
```bash
# Deploy everything to AWS
./deploy.sh
```

This script will:
1. Build React frontend
2. Package Lambda functions
3. Run Terraform apply
4. Upload frontend to S3
5. Invalidate CloudFront cache
6. Run health checks

### Continuous Deployment
```bash
# Push to GitHub main branch
git push origin main

# GitHub Actions automatically:
# - Runs tests
# - Deploys infrastructure
# - Deploys frontend
# - Deploys backend
# - Validates deployment
```

## Monitoring & Observability

### CloudWatch Dashboards
1. **API Performance**: Latency, error rates, throttling
2. **Lambda Metrics**: Invocations, duration, errors, cold starts
3. **Data Sync Health**: Success rate, data freshness, failures
4. **Cost Tracking**: Daily spend by service

### Alarms
- **Critical**: API 5xx errors > 5% (5 min window)
- **Warning**: Lambda duration > 25s (approaching timeout)
- **Info**: Data sync failures (retry exhausted)

### Logging Strategy
- **Application Logs**: JSON structured logging (Loguru)
- **Access Logs**: API Gateway access logs to S3
- **Audit Logs**: CloudTrail for infrastructure changes
- **Retention**: 7 days for debug, 30 days for access, 365 days for audit

## Disaster Recovery

### Backup Strategy
- **S3**: Versioning + Cross-region replication (optional)
- **DynamoDB**: Point-in-time recovery (7-day window)
- **Terraform State**: S3 versioning enabled
- **Secrets**: Automatic rotation with 7-day recovery window

### Recovery Procedures
1. **Data Loss**: Restore from S3 versions or DynamoDB PITR
2. **Infrastructure Failure**: Terraform re-apply from version control
3. **Region Outage**: Multi-region deployment (future enhancement)
4. **Code Rollback**: Lambda version rollback + S3 frontend version

### RTO/RPO Targets
- **Recovery Time Objective (RTO)**: < 1 hour
- **Recovery Point Objective (RPO)**: < 15 minutes (sync interval)

## Migration Path from Current Architecture

### Current State
- ECS Fargate containers (high cost ~$50-100/month idle)
- Application Load Balancer (high cost ~$20/month)
- Always-on infrastructure

### Migration Steps

1. **Phase 1: Parallel Deployment (Week 1)**
   - Deploy serverless architecture alongside ECS
   - Test with synthetic traffic
   - Validate data sync and API endpoints

2. **Phase 2: Traffic Migration (Week 2)**
   - Route 10% traffic to serverless (canary)
   - Monitor performance and errors
   - Gradual rollout: 25% → 50% → 100%

3. **Phase 3: Decommission Legacy (Week 3)**
   - Shut down ECS tasks
   - Delete ALB and target groups
   - Clean up VPC resources
   - **Cost Savings**: $70-120/month

4. **Phase 4: Optimization (Week 4)**
   - Fine-tune Lambda memory/timeout
   - Implement caching strategies
   - Review CloudWatch metrics
   - Adjust cost controls

## Future Enhancements

### Near-term (1-3 months)
- [ ] Multi-region deployment for HA
- [ ] GraphQL API via AppSync
- [ ] Real-time updates via WebSockets (API Gateway)
- [ ] Advanced analytics with Athena

### Medium-term (3-6 months)
- [ ] Mobile app (React Native)
- [ ] Slack/Teams integration
- [ ] AI-powered grading insights (Bedrock)
- [ ] Custom domain with ACM certificate

### Long-term (6-12 months)
- [ ] Multi-tenant architecture
- [ ] White-label deployment for other institutions
- [ ] Marketplace deployment (AWS Marketplace)
- [ ] Advanced ML features (SageMaker)

## Risk Assessment

### Technical Risks
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Lambda cold starts | Medium | Low | Provisioned concurrency for critical functions |
| API Gateway throttling | Low | Medium | Request caching + rate limiting |
| S3 eventual consistency | Low | Low | Use versioning + metadata validation |
| Cost overrun | Medium | Medium | CloudWatch billing alarms + Lambda concurrency limits |

### Operational Risks
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Canvas API changes | Medium | High | Version pinning + API contract tests |
| AWS service outage | Low | High | Multi-region deployment + CloudFront failover |
| Security breach | Low | Critical | WAF, encryption, audit logging, MFA |
| Data corruption | Low | High | S3 versioning + DynamoDB PITR |

## Success Metrics

### Performance
- API P95 latency < 500ms
- Frontend load time < 2s
- Data sync success rate > 99.5%
- Lambda cold start < 3s

### Cost
- Monthly AWS bill < $50 for < 1K users
- Cost per user < $0.10/month
- Infrastructure cost reduction > 60% vs ECS

### Reliability
- API uptime > 99.9%
- Mean time to recovery (MTTR) < 30 minutes
- Zero data loss incidents

### Developer Experience
- Deployment time < 10 minutes
- Zero-downtime deployments
- Rollback time < 5 minutes

## Conclusion

This serverless architecture provides:
- **60-70% cost reduction** compared to ECS Fargate
- **100% automated deployment** from GitHub
- **Production-grade security** with Cognito + WAF
- **Infinite scalability** with pay-per-use pricing
- **Operational simplicity** with managed services

The design balances affordability, scalability, and maintainability while maintaining professional quality standards for educational technology applications.
