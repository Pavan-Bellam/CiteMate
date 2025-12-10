variable "project_name" {
  description = "The name of the project"
  type        = string
}

variable "aws_region" {
  description = "The AWS region to deploy the infrastructure"
  type        = string
}

variable "bucket_name" {
  description = "The name of the S3 bucket"
  type        = string
}

variable "storage_folders" {
  description = "List of folders to create in the S3 bucket"
  type        = list(string)
  default     = ["papers"]
}

variable "redis_primary_region" {
  description = "Primary region for the global Redis database"
  type        = string
  default     = "us-east-1"
}

variable "redis_tls" {
  description = "Enable TLS for Redis connections"
  type        = bool
  default     = true
}
