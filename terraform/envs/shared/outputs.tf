output "producer_repository_url" {
  description = "ECR repository URL for producer"
  value       = module.ecr.producer_repository_url
}

output "consumer_repository_url" {
  description = "ECR repository URL for consumer"
  value       = module.ecr.consumer_repository_url
}
