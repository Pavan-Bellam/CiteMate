output "parameter_arns" {
  description = "ARNs of all SSM parameters"
  value = [
    aws_ssm_parameter.unstructured_api_key.arn,
    aws_ssm_parameter.upstash_email.arn,
    aws_ssm_parameter.upstash_api_key.arn,
    aws_ssm_parameter.pinecone_api_key.arn,
    aws_ssm_parameter.redis_url.arn,
    aws_ssm_parameter.openai_api_key.arn,
  ]
}

output "parameter_names" {
  description = "Names of all SSM parameters"
  value = {
    unstructured_api_key = aws_ssm_parameter.unstructured_api_key.name
    upstash_email        = aws_ssm_parameter.upstash_email.name
    upstash_api_key      = aws_ssm_parameter.upstash_api_key.name
    pinecone_api_key     = aws_ssm_parameter.pinecone_api_key.name
    redis_url            = aws_ssm_parameter.redis_url.name
    openai_api_key       = aws_ssm_parameter.openai_api_key.name
  }
}
