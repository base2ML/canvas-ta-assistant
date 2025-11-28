variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment (dev, prod)"
  type        = string
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}

variable "api_gateway_domain" {
  description = "API Gateway domain for API proxy (optional for now)"
  type        = string
  default     = ""
}

variable "description" {
  description = "Description for the CloudFront distribution"
  type        = string
  default     = "CloudFront distribution for Canvas TA Dashboard"
}

variable "aliases" {
  description = "List of alternate domain names (CNAMEs)"
  type        = list(string)
  default     = []
}

variable "acm_certificate_arn" {
  description = "ARN of the ACM certificate for custom domains"
  type        = string
  default     = ""
}
