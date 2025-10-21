# ALB Module

This module creates an Application Load Balancer (ALB) with target groups, listeners, and health checks for distributing traffic to ECS tasks.

## Features

- **Multi-AZ Load Balancing**: Distributes traffic across availability zones
- **Health Checks**: Configurable health monitoring for targets
- **HTTPS Support**: Optional SSL/TLS termination with ACM certificates
- **HTTP to HTTPS Redirect**: Automatic redirect for secure connections
- **Session Stickiness**: Optional sticky sessions for stateful applications
- **CloudWatch Alarms**: Automated monitoring for unhealthy targets and errors
- **Access Logs**: Optional S3-based access logging
- **Security Groups**: Managed ingress/egress rules

## Architecture

```
                    ┌──────────────────────┐
                    │   Internet Gateway   │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  Application Load    │
                    │     Balancer         │
                    │  (Public Subnets)    │
                    │                      │
                    │  • HTTP (80)         │
                    │  • HTTPS (443)       │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Target Group       │
                    │   Health Checks      │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼─────┐ ┌────────▼────────┐ ┌────▼─────────┐
    │  ECS Task 1   │ │  ECS Task 2     │ │  ECS Task 3  │
    │  (AZ-1)       │ │  (AZ-2)         │ │  (AZ-1)      │
    │  Port 8000    │ │  Port 8000      │ │  Port 8000   │
    └───────────────┘ └─────────────────┘ └──────────────┘
         (Private Subnets)
```

## Usage

### Basic HTTP Configuration

```hcl
module "alb" {
  source = "./modules/alb"

  project_name = "canvas-ta"
  environment  = "production"
  vpc_id       = module.vpc.vpc_id
  subnet_ids   = module.vpc.public_subnet_ids

  # Target configuration
  target_port     = 8000
  target_protocol = "HTTP"
  target_type     = "ip"

  # Health check
  health_check_path     = "/api/health"
  health_check_interval = 30
  health_check_timeout  = 5

  # Monitoring
  enable_cloudwatch_alarms = true
}
```

### HTTPS with Certificate

```hcl
module "alb" {
  source = "./modules/alb"

  project_name = "canvas-ta"
  environment  = "production"
  vpc_id       = module.vpc.vpc_id
  subnet_ids   = module.vpc.public_subnet_ids

  # Enable HTTPS
  enable_https         = true
  enable_https_redirect = true
  certificate_arn      = "arn:aws:acm:us-east-1:123456789012:certificate/abc123"
  ssl_policy           = "ELBSecurityPolicy-TLS13-1-2-2021-06"

  # Target configuration
  target_port = 8000

  # Health check
  health_check_path = "/api/health"
}
```

### With Access Logs

```hcl
module "alb" {
  source = "./modules/alb"

  project_name = "canvas-ta"
  environment  = "production"
  vpc_id       = module.vpc.vpc_id
  subnet_ids   = module.vpc.public_subnet_ids

  # Enable access logs
  enable_access_logs   = true
  access_logs_bucket   = "my-alb-logs-bucket"
  access_logs_prefix   = "canvas-ta/production"

  # Target configuration
  target_port = 8000
  health_check_path = "/api/health"
}
```

### Internal Load Balancer

```hcl
module "alb" {
  source = "./modules/alb"

  project_name = "canvas-ta"
  environment  = "production"
  vpc_id       = module.vpc.vpc_id
  subnet_ids   = module.vpc.private_subnet_ids

  # Make ALB internal (not internet-facing)
  internal = true

  # Restrict access to VPC CIDR
  allowed_cidr_blocks = ["10.0.0.0/16"]

  # Target configuration
  target_port = 8000
  health_check_path = "/api/health"
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| project_name | Name of the project | string | - | yes |
| environment | Environment name | string | - | yes |
| vpc_id | VPC ID | string | - | yes |
| subnet_ids | Subnet IDs (min 2) | list(string) | - | yes |
| internal | Internal or internet-facing | bool | false | no |
| enable_deletion_protection | Deletion protection | bool | false | no |
| allowed_cidr_blocks | Allowed CIDR blocks | list(string) | ["0.0.0.0/0"] | no |
| target_port | Target port | number | 8000 | no |
| target_protocol | Target protocol | string | "HTTP" | no |
| target_type | Target type (ip/instance/lambda) | string | "ip" | no |
| health_check_path | Health check path | string | "/api/health" | no |
| health_check_interval | Health check interval (sec) | number | 30 | no |
| health_check_timeout | Health check timeout (sec) | number | 5 | no |
| enable_https | Enable HTTPS listener | bool | false | no |
| enable_https_redirect | Redirect HTTP to HTTPS | bool | false | no |
| certificate_arn | ACM certificate ARN | string | "" | no |
| enable_stickiness | Enable sticky sessions | bool | false | no |
| enable_cloudwatch_alarms | Enable CloudWatch alarms | bool | true | no |

## Outputs

| Name | Description |
|------|-------------|
| alb_id | ALB ID |
| alb_arn | ALB ARN |
| alb_dns_name | ALB DNS name |
| alb_url | Full ALB URL (http/https) |
| alb_security_group_id | Security group ID |
| target_group_id | Target group ID |
| target_group_arn | Target group ARN |
| http_listener_arn | HTTP listener ARN |
| https_listener_arn | HTTPS listener ARN |

## Health Checks

The ALB performs health checks to ensure targets are healthy before routing traffic.

### Health Check Settings

| Setting | Default | Description |
|---------|---------|-------------|
| Path | `/api/health` | Endpoint to check |
| Interval | 30 seconds | Time between checks |
| Timeout | 5 seconds | Max wait time |
| Healthy Threshold | 2 | Consecutive successes needed |
| Unhealthy Threshold | 3 | Consecutive failures needed |
| Matcher | 200 | Expected HTTP status code |

### Example Health Check Endpoint

```python
# FastAPI health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}
```

## HTTPS Configuration

### Step 1: Request ACM Certificate

```bash
aws acm request-certificate \
  --domain-name canvas-ta.example.com \
  --validation-method DNS \
  --region us-east-1
```

### Step 2: Validate Certificate

Follow the DNS validation instructions in the ACM console.

### Step 3: Use Certificate ARN

```hcl
enable_https    = true
certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/abc123"
```

### Step 4: Configure DNS

Create a CNAME record pointing to the ALB DNS name:

```
canvas-ta.example.com -> canvas-ta-production-alb-123456789.us-east-1.elb.amazonaws.com
```

## SSL/TLS Policies

Available SSL policies (ordered from most to least secure):

1. **ELBSecurityPolicy-TLS13-1-2-2021-06** (Recommended, default)
   - TLS 1.3 and TLS 1.2
   - Modern cipher suites
   - Best security

2. **ELBSecurityPolicy-2016-08**
   - TLS 1.2 and TLS 1.1
   - Wider compatibility
   - Legacy browser support

3. **ELBSecurityPolicy-FS-1-2-Res-2020-10**
   - Forward secrecy required
   - High security for regulated industries

## CloudWatch Alarms

The module creates three alarms by default:

### 1. Unhealthy Targets

- **Metric**: UnHealthyHostCount
- **Threshold**: > 0
- **Action**: Investigate application health

### 2. High Response Time

- **Metric**: TargetResponseTime
- **Threshold**: > 1.0 seconds (configurable)
- **Action**: Optimize application or scale up

### 3. 5xx Errors

- **Metric**: HTTPCode_Target_5XX_Count
- **Threshold**: > 10 errors (configurable)
- **Action**: Check application logs for errors

## Access Logs

Enable access logs to track all requests:

```hcl
enable_access_logs = true
access_logs_bucket = "my-alb-logs"
access_logs_prefix = "canvas-ta/production"
```

### Create S3 Bucket for Logs

```bash
aws s3api create-bucket \
  --bucket my-alb-logs \
  --region us-east-1

# Enable bucket policy for ALB to write logs
aws s3api put-bucket-policy \
  --bucket my-alb-logs \
  --policy file://alb-logs-policy.json
```

## Session Stickiness

Enable sticky sessions for stateful applications:

```hcl
enable_stickiness    = true
stickiness_duration  = 86400  # 24 hours
```

**Use Cases**:
- WebSocket connections
- Session-based authentication
- Stateful applications

**Note**: For stateless applications (like this FastAPI app), stickiness is not required.

## Security Best Practices

1. **HTTPS Only**: Always use HTTPS in production
2. **Restrict CIDR**: Limit `allowed_cidr_blocks` to known IPs when possible
3. **Enable Deletion Protection**: Set to `true` for production
4. **Monitor Alarms**: Set up SNS notifications for CloudWatch alarms
5. **Access Logs**: Enable for audit and troubleshooting
6. **Modern SSL Policy**: Use TLS 1.3 for best security

## Cost Considerations

- **ALB**: ~$0.0225/hour (~$16/month) + LCU charges
- **LCU (Load Balancer Capacity Unit)**: Based on traffic
  - New connections/sec
  - Active connections
  - Bandwidth
  - Rule evaluations
- **Data Transfer**: Standard AWS data transfer rates
- **Access Logs**: S3 storage costs

### Typical Cost Estimate

- Small app (<1M requests/month): ~$20-30/month
- Medium app (10M requests/month): ~$50-100/month
- Large app (100M requests/month): ~$200-500/month

## Troubleshooting

### Targets Not Becoming Healthy

1. Check security group allows ALB → ECS traffic
2. Verify health check path returns 200
3. Check ECS task logs for errors
4. Ensure container is listening on correct port

### 502 Bad Gateway

- Target is not responding
- Health check is failing
- Security group blocks ALB → target traffic

### 504 Gateway Timeout

- Target response is too slow
- Increase `health_check_timeout`
- Optimize application performance

## Integration with ECS

The ALB integrates with ECS service:

```hcl
resource "aws_ecs_service" "main" {
  # ... other configuration ...

  load_balancer {
    target_group_arn = module.alb.target_group_arn
    container_name   = "app"
    container_port   = 8000
  }
}
```

ECS automatically registers/deregisters tasks with the target group.
