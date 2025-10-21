# VPC Module

This module creates a complete VPC infrastructure with public and private subnets across multiple availability zones.

## Features

- **Multi-AZ Deployment**: Subnets are distributed across availability zones for high availability
- **Public Subnets**: With Internet Gateway for external access
- **Private Subnets**: Isolated subnets with optional NAT Gateway for outbound internet access
- **NAT Gateway**: Configurable NAT Gateway (single or per-AZ) for private subnet internet access
- **VPC Flow Logs**: Optional CloudWatch-based flow logging for network monitoring and security
- **Cost Optimization**: Option for single NAT Gateway to reduce costs in non-production environments

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         VPC (10.0.0.0/16)                   │
│                                                             │
│  ┌──────────────────┐           ┌──────────────────┐      │
│  │  Public Subnet   │           │  Public Subnet   │      │
│  │  10.0.0.0/24     │           │  10.0.1.0/24     │      │
│  │  (AZ-1)          │           │  (AZ-2)          │      │
│  │                  │           │                  │      │
│  │  ┌────────────┐  │           │  ┌────────────┐  │      │
│  │  │    ALB     │  │           │  │    NAT     │  │      │
│  │  └────────────┘  │           │  │  Gateway   │  │      │
│  └────────┬─────────┘           └────────┬───────┘  │      │
│           │                              │                │
│           ▼ Internet Gateway             ▼                │
│  ┌──────────────────┐           ┌──────────────────┐      │
│  │ Private Subnet   │           │ Private Subnet   │      │
│  │ 10.0.2.0/24      │           │ 10.0.3.0/24      │      │
│  │ (AZ-1)           │           │ (AZ-2)           │      │
│  │                  │           │                  │      │
│  │ ┌────────────┐   │           │ ┌────────────┐   │      │
│  │ │ ECS Tasks  │   │           │ │ ECS Tasks  │   │      │
│  │ └────────────┘   │           │ └────────────┘   │      │
│  └──────────────────┘           └──────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Usage

```hcl
module "vpc" {
  source = "./modules/vpc"

  project_name         = "canvas-ta"
  environment          = "production"
  vpc_cidr             = "10.0.0.0/16"
  public_subnet_count  = 2
  private_subnet_count = 2

  # Enable NAT Gateway for private subnet internet access
  enable_nat_gateway = true

  # Use single NAT Gateway for cost savings (dev/staging)
  single_nat_gateway = false

  # Enable VPC Flow Logs for security monitoring
  enable_flow_logs           = true
  flow_logs_retention_days   = 30
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| project_name | Name of the project | string | - | yes |
| environment | Environment name | string | - | yes |
| vpc_cidr | CIDR block for VPC | string | "10.0.0.0/16" | no |
| public_subnet_count | Number of public subnets | number | 2 | no |
| private_subnet_count | Number of private subnets | number | 2 | no |
| enable_nat_gateway | Enable NAT Gateway | bool | true | no |
| single_nat_gateway | Use single NAT Gateway | bool | false | no |
| enable_flow_logs | Enable VPC Flow Logs | bool | true | no |
| flow_logs_retention_days | Flow logs retention | number | 30 | no |

## Outputs

| Name | Description |
|------|-------------|
| vpc_id | ID of the VPC |
| vpc_cidr | CIDR block of the VPC |
| public_subnet_ids | List of public subnet IDs |
| private_subnet_ids | List of private subnet IDs |
| internet_gateway_id | ID of the Internet Gateway |
| nat_gateway_ids | List of NAT Gateway IDs |

## Best Practices

1. **Multi-AZ**: Always use at least 2 availability zones for high availability
2. **NAT Gateway**:
   - Production: Use NAT Gateway per AZ for redundancy
   - Dev/Staging: Use single NAT Gateway to reduce costs
3. **Flow Logs**: Enable for security monitoring and troubleshooting
4. **CIDR Planning**: Plan subnet sizes based on expected resource count
5. **Tagging**: All resources are automatically tagged with project, environment, and Terraform metadata

## Cost Considerations

- **NAT Gateway**: $0.045/hour + data transfer costs
- **Single NAT Gateway**: ~$32/month (single AZ)
- **Multi-AZ NAT**: ~$64/month (2 AZs)
- **VPC Flow Logs**: CloudWatch Logs storage and data ingestion costs
- **Elastic IPs**: Free when associated with running NAT Gateways

## Security

- Private subnets have no direct internet access
- NAT Gateways provide outbound-only internet connectivity
- VPC Flow Logs capture network traffic for security analysis
- All resources tagged for compliance and cost tracking
