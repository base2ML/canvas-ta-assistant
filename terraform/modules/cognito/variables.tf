# Variables for Cognito Module

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "auto_verified_attributes" {
  description = "Attributes to be auto-verified"
  type        = list(string)
  default     = ["email"]
}

variable "username_attributes" {
  description = "Attributes to be used as username"
  type        = list(string)
  default     = ["email"]
}

variable "minimum_length" {
  description = "Minimum length for passwords"
  type        = number
  default     = 8
}

variable "require_lowercase" {
  description = "Require lowercase characters in passwords"
  type        = bool
  default     = true
}

variable "require_numbers" {
  description = "Require numbers in passwords"
  type        = bool
  default     = true
}

variable "require_symbols" {
  description = "Require symbols in passwords"
  type        = bool
  default     = false
}

variable "require_uppercase" {
  description = "Require uppercase characters in passwords"
  type        = bool
  default     = true
}

variable "email_sending_account" {
  description = "Email sending account configuration"
  type        = string
  default     = "COGNITO_DEFAULT"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}