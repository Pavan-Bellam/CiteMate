output "folder_keys" {
  description = "List of created folder keys"
  value       = [for obj in aws_s3_object.folders : obj.key]
}

output "bucket_name" {
  description = "The bucket name being used"
  value       = var.bucket_name
}
