variable "redis_db_name" {
  description = "Name of the Upstash Redis database"
  type        = string
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
