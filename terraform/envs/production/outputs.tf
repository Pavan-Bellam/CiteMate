output "redis_url" {
  description = "Redis connection URL"
  value       = module.redis.redis_url
  sensitive   = true
}

output "sqs_queue_url" {
  description = "SQS queue URL"
  value       = module.sqs.queue_url
}
