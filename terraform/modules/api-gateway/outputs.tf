output "api_endpoint" {
  description = "The URI of the API"
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "api_id" {
  description = "The API identifier"
  value       = aws_apigatewayv2_api.main.id
}

output "stage_id" {
  description = "The stage identifier"
  value       = aws_apigatewayv2_stage.default.id
}
