output "producer_repository_url" {
  description = "The URL of the producer ECR repository"
  value       = aws_ecr_repository.producer.repository_url
}

output "producer_repository_arn" {
  description = "The ARN of the producer ECR repository"
  value       = aws_ecr_repository.producer.arn
}

output "consumer_repository_url" {
  description = "The URL of the consumer ECR repository"
  value       = aws_ecr_repository.consumer.repository_url
}

output "consumer_repository_arn" {
  description = "The ARN of the consumer ECR repository"
  value       = aws_ecr_repository.consumer.arn
}

output "push_policy_arn" {
  description = "The ARN of the IAM policy for pushing images (attach to OIDC role)"
  value       = aws_iam_policy.ecr_push.arn
}
