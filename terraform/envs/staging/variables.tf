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

# ECR image URLs (from shared environment)
variable "producer_image" {
  description = "Docker image URL for the producer task"
  type        = string
}

variable "consumer_image" {
  description = "Docker image URL for the consumer task"
  type        = string
}

# Secrets (from CI/CD)
variable "unstructured_api_key" {
  description = "Unstructured API key"
  type        = string
  sensitive   = true
}

variable "upstash_email" {
  description = "Upstash email"
  type        = string
  sensitive   = true
}

variable "upstash_api_key" {
  description = "Upstash API key"
  type        = string
  sensitive   = true
}

variable "pinecone_api_key" {
  description = "Pinecone API key"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
}

# Producer environment variables
variable "producer_arxiv_category" {
  description = "ArXiv category to fetch papers from"
  type        = string
  default     = "cs.AI,cs.LG,cs.CL"
}

variable "producer_max_results" {
  description = "Maximum number of papers to fetch"
  type        = number
  default     = 10
}

variable "producer_max_pages" {
  description = "Skip papers exceeding this page count"
  type        = number
  default     = 20
}

# Consumer environment variables
variable "consumer_mode" {
  description = "Consumer mode: parse, process, or full"
  type        = string
  default     = "full"
}

variable "consumer_chunk_max_characters" {
  description = "Maximum chunk size in characters"
  type        = number
  default     = 1500
}

variable "consumer_chunk_new_after_n_chars" {
  description = "Soft limit for starting new chunk"
  type        = number
  default     = 1000
}

variable "consumer_chunk_combine_under_n_chars" {
  description = "Combine chunks smaller than this"
  type        = number
  default     = 500
}

variable "consumer_embedding_model" {
  description = "OpenAI embedding model"
  type        = string
  default     = "text-embedding-3-large"
}

variable "consumer_embedding_token_threshold" {
  description = "Token threshold before embedding batch"
  type        = number
  default     = 6000
}

variable "consumer_pinecone_index_name" {
  description = "Pinecone index name"
  type        = string
  default     = "ras-papers"
}

variable "consumer_embedding_dimension" {
  description = "Embedding vector dimension"
  type        = string
  default     = "3072"
}
