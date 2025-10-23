# EventBridge Module for Lambda Scheduling

# EventBridge rule for Lambda scheduling
resource "aws_cloudwatch_event_rule" "lambda_schedule" {
  name                = "${var.project_name}-lambda-schedule-${var.environment}"
  description         = "Trigger Lambda function every 15 minutes"
  schedule_expression = var.schedule_expression

  tags = var.tags
}

# EventBridge target (Lambda function)
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.lambda_schedule.name
  target_id = "CanvasDataFetcherTarget"
  arn       = var.lambda_function_arn
}

# Lambda permission for EventBridge
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.lambda_schedule.arn
}