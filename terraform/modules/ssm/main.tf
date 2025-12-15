
resource "aws_ssm_parameter" "unstructured_api_key" {
  name  = "${local.prefix}/unstructured-api-key"
  type  = "SecureString"
  value = var.unstructured_api_key
}

resource "aws_ssm_parameter" "upstash_email" {
  name  = "${local.prefix}/upstash-email"
  type  = "SecureString"
  value = var.upstash_email
}

resource "aws_ssm_parameter" "upstash_api_key" {
  name  = "${local.prefix}/upstash-api-key"
  type  = "SecureString"
  value = var.upstash_api_key
}

resource "aws_ssm_parameter" "pinecone_api_key" {
  name  = "${local.prefix}/pinecone-api-key"
  type  = "SecureString"
  value = var.pinecone_api_key
}

resource "aws_ssm_parameter" "redis_url" {
  name  = "${local.prefix}/redis-url"
  type  = "SecureString"
  value = var.redis_url
}

resource "aws_ssm_parameter" "openai_api_key" {
  name  = "${local.prefix}/openai-api-key"
  type  = "SecureString"
  value = var.openai_api_key
}
