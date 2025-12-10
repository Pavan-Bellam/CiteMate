output "producer_repository_url" {
  description = "ECR repository URL for producer"
  value       = module.ecr.producer_repository_url
}

output "consumer_repository_url" {
  description = "ECR repository URL for consumer"
  value       = module.ecr.consumer_repository_url
}

output "ecr_push_policy_arn" {
  description = "IAM policy ARN for pushing to ECR (attach to OIDC role)"
  value       = module.ecr.push_policy_arn
}
