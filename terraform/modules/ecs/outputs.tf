output "producer_task_arn" {
    value = aws_ecs_task_definition.producer.arn_without_revision
}

output "consumer_task_arn" {
    value = aws_ecs_task_definition.consumer.arn_without_revision
}

output "cluster_arn" {
    value = aws_ecs_cluster.this.arn
}