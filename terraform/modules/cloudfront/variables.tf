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
