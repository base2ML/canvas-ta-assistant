# ALB Module - Application Load Balancer
# Creates an Application Load Balancer with target groups and listeners

# ============================================================================
# Security Group for ALB
# ============================================================================

resource "aws_security_group" "alb" {
  name        = "${var.project_name}-${var.environment}-alb-sg"
  description = "Security group for Application Load Balancer"
  vpc_id      = var.vpc_id

  # Inbound HTTP
  ingress {
    description = "Allow HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  # Inbound HTTPS
  ingress {
    description = "Allow HTTPS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  # Outbound - Allow all
  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-alb-sg"
  }
}

# ============================================================================
# Application Load Balancer
# ============================================================================

resource "aws_lb" "main" {
  name               = "${var.project_name}-${var.environment}-alb"
  internal           = var.internal
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.subnet_ids

  enable_deletion_protection = var.enable_deletion_protection
  enable_http2              = var.enable_http2
  enable_cross_zone_load_balancing = true

  # Access logs (optional)
  dynamic "access_logs" {
    for_each = var.enable_access_logs ? [1] : []
    content {
      bucket  = var.access_logs_bucket
      prefix  = var.access_logs_prefix
      enabled = true
    }
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-alb"
  }
}

# ============================================================================
# Target Group
# ============================================================================

resource "aws_lb_target_group" "main" {
  name                 = "${var.project_name}-${var.environment}-tg"
  port                 = var.target_port
  protocol             = var.target_protocol
  vpc_id               = var.vpc_id
  target_type          = var.target_type
  deregistration_delay = var.deregistration_delay

  # Health check configuration
  health_check {
    enabled             = true
    healthy_threshold   = var.health_check_healthy_threshold
    unhealthy_threshold = var.health_check_unhealthy_threshold
    timeout             = var.health_check_timeout
    interval            = var.health_check_interval
    path                = var.health_check_path
    protocol            = var.health_check_protocol
    matcher             = var.health_check_matcher
  }

  # Stickiness (session affinity)
  dynamic "stickiness" {
    for_each = var.enable_stickiness ? [1] : []
    content {
      type            = "lb_cookie"
      cookie_duration = var.stickiness_duration
      enabled         = true
    }
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-tg"
  }

  # Ensure new target group is created before destroying old one
  lifecycle {
    create_before_destroy = true
  }
}

# ============================================================================
# HTTP Listener
# ============================================================================

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  # Default action: Forward to target group or redirect to HTTPS
  dynamic "default_action" {
    for_each = var.enable_https_redirect ? [1] : []
    content {
      type = "redirect"
      redirect {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }

  dynamic "default_action" {
    for_each = var.enable_https_redirect ? [] : [1]
    content {
      type             = "forward"
      target_group_arn = aws_lb_target_group.main.arn
    }
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-http-listener"
  }
}

# ============================================================================
# HTTPS Listener (Optional)
# ============================================================================

resource "aws_lb_listener" "https" {
  count             = var.enable_https ? 1 : 0
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = var.ssl_policy
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main.arn
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-https-listener"
  }
}

# ============================================================================
# CloudWatch Alarms for Monitoring
# ============================================================================

# Alarm for unhealthy target count
resource "aws_cloudwatch_metric_alarm" "unhealthy_targets" {
  count               = var.enable_cloudwatch_alarms ? 1 : 0
  alarm_name          = "${var.project_name}-${var.environment}-alb-unhealthy-targets"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "UnHealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Average"
  threshold           = 0
  alarm_description   = "This metric monitors unhealthy targets"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TargetGroup  = aws_lb_target_group.main.arn_suffix
    LoadBalancer = aws_lb.main.arn_suffix
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-unhealthy-targets-alarm"
  }
}

# Alarm for high response time
resource "aws_cloudwatch_metric_alarm" "high_response_time" {
  count               = var.enable_cloudwatch_alarms ? 1 : 0
  alarm_name          = "${var.project_name}-${var.environment}-alb-high-response-time"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Average"
  threshold           = var.response_time_threshold
  alarm_description   = "This metric monitors target response time"
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-high-response-time-alarm"
  }
}

# Alarm for 5xx errors
resource "aws_cloudwatch_metric_alarm" "target_5xx_errors" {
  count               = var.enable_cloudwatch_alarms ? 1 : 0
  alarm_name          = "${var.project_name}-${var.environment}-alb-target-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Sum"
  threshold           = var.error_5xx_threshold
  alarm_description   = "This metric monitors 5xx errors from targets"
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-5xx-errors-alarm"
  }
}
