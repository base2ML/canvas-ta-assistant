# ECS Module

This module creates a complete AWS ECS (Elastic Container Service) infrastructure using Fargate for serverless container orchestration.

## Features

- **ECS Cluster**: Managed cluster with Container Insights
- **Fargate Tasks**: Serverless container execution
- **Auto Scaling**: CPU and memory-based scaling
- **Load Balancer Integration**: Seamless ALB integration
- **CloudWatch Logging**: Centralized log management
- **Health Checks**: Container and ALB health monitoring
- **Deployment Circuit Breaker**: Automatic rollback on failures
- **Service Discovery**: Optional AWS Cloud Map integration
- **Fargate Spot**: Cost optimization with Spot instances

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    ECS Cluster                             │
│                                                            │
│  ┌──────────────────────────────────────────────────┐     │
│  │  ECS Service                                     │     │
│  │  • Desired Count: 2                              │     │
│  │  • Auto Scaling: 1-10 tasks                      │     │
│  │  • Deployment: Rolling update with circuit      │     │
│  │    breaker                                        │     │
│  └──────────────┬───────────────────────────────────┘     │
│                 │                                          │
│     ┌───────────┼───────────┐                             │
│     │           │           │                             │
│  ┌──▼───┐   ┌──▼───┐   ┌──▼───┐                         │
│  │Task 1│   │Task 2│   │Task 3│                         │
│  │      │   │      │   │      │                         │
│  │ App  │   │ App  │   │ App  │                         │
│  │:8000 │   │:8000 │   │:8000 │                         │
│  └──┬───┘   └──┬───┘   └──┬───┘                         │
│     │          │          │                              │
│     └──────────┼──────────┘                              │
│                │                                          │
│           ┌────▼─────┐                                    │
│           │   ALB    │                                    │
│           │  Target  │                                    │
│           │  Group   │                                    │
│           └──────────┘                                    │
└────────────────────────────────────────────────────────────┘
                │
     ┌──────────▼──────────┐
     │  CloudWatch Logs    │
     │  /ecs/canvas-ta/... │
     └─────────────────────┘
```

## Usage

### Basic Configuration

```hcl
module "ecs" {
  source = "./modules/ecs"

  project_name        = "canvas-ta"
  environment         = "production"
  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_subnet_ids

  # IAM roles
  task_execution_role_arn = module.iam.ecs_task_execution_role_arn
  task_role_arn           = module.iam.ecs_task_role_arn

  # ALB integration
  alb_security_group_id = module.alb.alb_security_group_id
  target_group_arn      = module.alb.target_group_arn
  alb_listener_arn      = module.alb.http_listener_arn

  # Container configuration
  container_name  = "app"
  container_image = "123456789012.dkr.ecr.us-east-1.amazonaws.com/canvas-ta:latest"
  container_port  = 8000

  # Task sizing
  task_cpu    = 512   # 0.5 vCPU
  task_memory = 1024  # 1 GB

  # Service configuration
  desired_count = 2

  # Auto scaling
  enable_autoscaling      = true
  autoscaling_min_capacity = 1
  autoscaling_max_capacity = 10
  autoscaling_cpu_target   = 70
  autoscaling_memory_target = 80
}
```

### With Environment Variables and Secrets

```hcl
module "ecs" {
  source = "./modules/ecs"

  # ... basic configuration ...

  # Environment variables
  environment_variables = {
    ENVIRONMENT = "production"
    LOG_LEVEL   = "INFO"
    PORT        = "8000"
  }

  # Secrets from Secrets Manager
  secrets = {
    CANVAS_API_KEY = "arn:aws:secretsmanager:us-east-1:123456789012:secret:canvas-api-key-abc123"
    DATABASE_URL   = "arn:aws:secretsmanager:us-east-1:123456789012:secret:db-connection-xyz789"
  }
}
```

### With Fargate Spot for Cost Savings

```hcl
module "ecs" {
  source = "./modules/ecs"

  # ... basic configuration ...

  # Enable Fargate Spot (70% cost reduction)
  enable_fargate_spot   = true
  fargate_weight        = 1
  fargate_spot_weight   = 3  # 75% on Spot, 25% on regular Fargate
  fargate_base_capacity = 1  # Always keep 1 task on regular Fargate
}
```

### Production Configuration

```hcl
module "ecs" {
  source = "./modules/ecs"

  # ... basic configuration ...

  # Production settings
  desired_count                       = 3
  deployment_minimum_healthy_percent  = 100
  deployment_maximum_percent          = 200
  enable_deployment_circuit_breaker   = true
  enable_deployment_rollback          = true

  # Monitoring
  enable_container_insights = true
  enable_cloudwatch_alarms  = true
  cpu_alarm_threshold       = 85
  memory_alarm_threshold    = 85

  # Logging
  log_retention_days = 30

  # Auto scaling
  enable_autoscaling       = true
  autoscaling_min_capacity = 2
  autoscaling_max_capacity = 20
}
```

## Inputs

### Required Variables

| Name | Description | Type |
|------|-------------|------|
| project_name | Project name | string |
| environment | Environment (dev/staging/production) | string |
| vpc_id | VPC ID | string |
| private_subnet_ids | Private subnet IDs | list(string) |
| task_execution_role_arn | Task execution role ARN | string |
| task_role_arn | Task role ARN | string |
| alb_security_group_id | ALB security group ID | string |
| target_group_arn | Target group ARN | string |
| alb_listener_arn | ALB listener ARN | string |

### Optional Variables

| Name | Description | Type | Default |
|------|-------------|------|---------|
| container_name | Container name | string | "app" |
| container_image | Docker image | string | "nginx:latest" |
| container_port | Container port | number | 8000 |
| task_cpu | CPU units (256-16384) | number | 512 |
| task_memory | Memory in MB | number | 1024 |
| desired_count | Desired task count | number | 2 |
| enable_autoscaling | Enable auto-scaling | bool | true |
| autoscaling_min_capacity | Min tasks | number | 1 |
| autoscaling_max_capacity | Max tasks | number | 10 |
| enable_fargate_spot | Use Fargate Spot | bool | false |
| enable_container_insights | Enable Container Insights | bool | true |

See `variables.tf` for complete list of variables.

## Outputs

| Name | Description |
|------|-------------|
| cluster_id | ECS cluster ID |
| cluster_arn | ECS cluster ARN |
| cluster_name | ECS cluster name |
| service_id | ECS service ID |
| service_name | ECS service name |
| task_definition_arn | Task definition ARN |
| log_group_name | CloudWatch log group name |
| ecs_tasks_security_group_id | Tasks security group ID |

## Fargate Task Sizing

### CPU and Memory Combinations

| CPU (vCPU) | CPU Units | Valid Memory (GB) |
|------------|-----------|-------------------|
| 0.25 | 256 | 0.5, 1, 2 |
| 0.5 | 512 | 1, 2, 3, 4 |
| 1 | 1024 | 2, 3, 4, 5, 6, 7, 8 |
| 2 | 2048 | 4-16 (1 GB increments) |
| 4 | 4096 | 8-30 (1 GB increments) |

### Sizing Recommendations

**Small Application** (FastAPI, lightweight):
```hcl
task_cpu    = 256
task_memory = 512
```

**Medium Application** (Standard web app):
```hcl
task_cpu    = 512
task_memory = 1024
```

**Large Application** (Heavy processing):
```hcl
task_cpu    = 1024
task_memory = 2048
```

## Auto Scaling

Auto-scaling uses target tracking based on:

1. **CPU Utilization**: Scales when average CPU exceeds target (default 70%)
2. **Memory Utilization**: Scales when average memory exceeds target (default 80%)

### Scaling Behavior

- **Scale Out**: Adds tasks when metrics exceed targets
  - Cooldown: 60 seconds (configurable)
  - Rapid response to traffic spikes

- **Scale In**: Removes tasks when metrics drop below targets
  - Cooldown: 300 seconds (5 minutes, configurable)
  - Conservative to prevent thrashing

### Example Auto-Scaling Configuration

```hcl
enable_autoscaling         = true
autoscaling_min_capacity   = 2    # Always keep 2 tasks
autoscaling_max_capacity   = 20   # Never exceed 20 tasks
autoscaling_cpu_target     = 70   # Scale at 70% CPU
autoscaling_memory_target  = 80   # Scale at 80% memory
```

## Deployment Strategies

### Rolling Update (Default)

```hcl
deployment_minimum_healthy_percent = 100
deployment_maximum_percent         = 200
```

- Launches new tasks before stopping old ones
- Zero downtime deployments
- Requires 2x capacity during deployment

### Blue/Green Deployment

```hcl
deployment_controller_type = "CODE_DEPLOY"
```

- Requires AWS CodeDeploy setup
- Full traffic shift with rollback capability
- Requires additional configuration

## Health Checks

### Container Health Check

Runs inside the container:

```hcl
health_check_command = ["CMD-SHELL", "curl -f http://localhost:8000/api/health || exit 1"]
health_check_interval = 30
health_check_timeout = 5
health_check_retries = 3
health_check_start_period = 60
```

### ALB Health Check

Configured in ALB module, monitors from load balancer.

## Container Insights

When enabled, Container Insights provides:

- **Performance Metrics**: CPU, memory, disk, network
- **Task-Level Metrics**: Per-task resource utilization
- **Service Maps**: Visualize service dependencies
- **Anomaly Detection**: Automatic issue detection

**Cost**: ~$0.50-$2.00 per task per month

Enable with:
```hcl
enable_container_insights = true
```

## Fargate Spot

Fargate Spot offers up to 70% cost savings but can be interrupted.

### When to Use Spot

✅ **Good for**:
- Development/staging environments
- Stateless applications
- Fault-tolerant workloads
- Batch processing

❌ **Avoid for**:
- Production critical services
- Long-running stateful tasks
- Real-time applications

### Mixed Capacity Strategy

```hcl
enable_fargate_spot   = true
fargate_weight        = 1    # 25% regular Fargate
fargate_spot_weight   = 3    # 75% Fargate Spot
fargate_base_capacity = 1    # Keep 1 task on regular Fargate
```

## CloudWatch Logs

Logs are stored in CloudWatch Logs:

### Log Group

- **Name**: `/ecs/${project_name}-${environment}`
- **Retention**: Configurable (default 30 days)
- **Stream Prefix**: `ecs`

### Viewing Logs

```bash
# View latest logs
aws logs tail /ecs/canvas-ta-production --follow

# View specific task logs
aws logs tail /ecs/canvas-ta-production --follow --filter-pattern "ERROR"
```

## Troubleshooting

### Tasks Not Starting

1. Check CloudWatch logs for errors
2. Verify ECR image exists and is accessible
3. Check task execution role has ECR permissions
4. Ensure subnets have internet access (via NAT Gateway)

### Tasks Failing Health Checks

1. Verify health check endpoint is accessible
2. Check application is listening on correct port
3. Review health check timeout and interval settings
4. Check security group allows ALB → ECS traffic

### Auto-Scaling Not Working

1. Verify CloudWatch metrics are being published
2. Check auto-scaling target and policy configuration
3. Ensure min/max capacity allows scaling
4. Review CloudWatch alarms

### High Memory Usage

1. Check application for memory leaks
2. Increase task memory allocation
3. Review CloudWatch Container Insights
4. Consider horizontal scaling instead of vertical

## Cost Optimization

### 1. Right-Size Tasks

Start small and scale up:
```hcl
task_cpu    = 256   # Start with 0.25 vCPU
task_memory = 512   # Start with 512 MB
```

### 2. Use Fargate Spot

Save 70% in non-production:
```hcl
enable_fargate_spot = true
```

### 3. Optimize Auto-Scaling

Aggressive scale-in:
```hcl
autoscaling_scale_in_cooldown = 180  # 3 minutes
```

### 4. Reduce Log Retention

```hcl
log_retention_days = 7  # For dev/staging
```

### 5. Disable Container Insights in Dev

```hcl
enable_container_insights = false  # For dev only
```

## Security Best Practices

1. **Private Subnets**: Always run tasks in private subnets
2. **Security Groups**: Restrict ingress to ALB only
3. **Secrets Management**: Use Secrets Manager, never environment variables
4. **Task Role**: Grant minimal permissions required
5. **Image Scanning**: Enable ECR image scanning
6. **HTTPS Only**: Use HTTPS for all external traffic
7. **ECS Exec**: Disable in production unless needed for debugging

## Integration with CI/CD

The ECS service is configured to ignore `task_definition` changes:

```hcl
lifecycle {
  ignore_changes = [task_definition]
}
```

This allows CI/CD (GitHub Actions) to update task definitions without Terraform conflicts.

See `.github/workflows/deploy.yml` for CI/CD integration.

## Advanced Features

### ECS Exec (SSH into Running Tasks)

```hcl
enable_ecs_exec = true
```

Connect to running task:
```bash
aws ecs execute-command \
  --cluster canvas-ta-production-cluster \
  --task <task-id> \
  --container app \
  --interactive \
  --command "/bin/bash"
```

### Service Discovery

Enable private DNS for service-to-service communication:

```hcl
enable_service_discovery = true
service_discovery_name  = "app"
```

Access via: `app.canvas-ta-production.local`

## Monitoring and Alerting

The module creates CloudWatch alarms for:

1. **High CPU**: Alert when CPU > 85% (configurable)
2. **High Memory**: Alert when memory > 85% (configurable)

Configure SNS topic for notifications:

```hcl
# Add alarm actions manually or via Terraform
resource "aws_cloudwatch_metric_alarm" "custom" {
  alarm_actions = [aws_sns_topic.alerts.arn]
}
```

## Example: Complete Production Setup

```hcl
module "ecs" {
  source = "./modules/ecs"

  project_name       = "canvas-ta"
  environment        = "production"
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids

  task_execution_role_arn = module.iam.ecs_task_execution_role_arn
  task_role_arn           = module.iam.ecs_task_role_arn

  alb_security_group_id = module.alb.alb_security_group_id
  target_group_arn      = module.alb.target_group_arn
  alb_listener_arn      = module.alb.http_listener_arn

  container_name  = "app"
  container_image = "${module.ecr.repository_url}:latest"
  container_port  = 8000

  task_cpu    = 512
  task_memory = 1024

  desired_count = 3

  environment_variables = {
    ENVIRONMENT = "production"
    LOG_LEVEL   = "INFO"
  }

  secrets = {
    CANVAS_API_KEY = aws_secretsmanager_secret.canvas_api_key.arn
  }

  enable_autoscaling       = true
  autoscaling_min_capacity = 2
  autoscaling_max_capacity = 20

  enable_container_insights = true
  enable_cloudwatch_alarms  = true

  log_retention_days = 30
}
```
