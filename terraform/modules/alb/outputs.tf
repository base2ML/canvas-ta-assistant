# ALB Module Outputs

# ============================================================================
# Load Balancer Outputs
# ============================================================================

output "alb_id" {
  description = "ID of the Application Load Balancer"
  value       = aws_lb.main.id
}

output "alb_arn" {
  description = "ARN of the Application Load Balancer"
  value       = aws_lb.main.arn
}

output "alb_arn_suffix" {
  description = "ARN suffix for use with CloudWatch Metrics"
  value       = aws_lb.main.arn_suffix
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Zone ID of the Application Load Balancer"
  value       = aws_lb.main.zone_id
}

output "alb_url" {
  description = "URL of the Application Load Balancer"
  value       = var.enable_https ? "https://${aws_lb.main.dns_name}" : "http://${aws_lb.main.dns_name}"
}

# ============================================================================
# Security Group Outputs
# ============================================================================

output "alb_security_group_id" {
  description = "ID of the ALB security group"
  value       = aws_security_group.alb.id
}

# ============================================================================
# Target Group Outputs
# ============================================================================

output "target_group_id" {
  description = "ID of the target group"
  value       = aws_lb_target_group.main.id
}

output "target_group_arn" {
  description = "ARN of the target group"
  value       = aws_lb_target_group.main.arn
}

output "target_group_arn_suffix" {
  description = "ARN suffix for use with CloudWatch Metrics"
  value       = aws_lb_target_group.main.arn_suffix
}

output "target_group_name" {
  description = "Name of the target group"
  value       = aws_lb_target_group.main.name
}

# ============================================================================
# Listener Outputs
# ============================================================================

output "http_listener_arn" {
  description = "ARN of the HTTP listener"
  value       = aws_lb_listener.http.arn
}

output "https_listener_arn" {
  description = "ARN of the HTTPS listener"
  value       = var.enable_https ? aws_lb_listener.https[0].arn : null
}
