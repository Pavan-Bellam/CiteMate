variable "bucket_name" {
  description = "The name of the S3 bucket"
  type        = string
}

variable "prefix" {
  description = "The prefix path in the bucket (e.g., development/username)"
  type        = string
}

variable "folders" {
  description = "List of folder keys to create in the bucket"
  type        = list(string)
}
