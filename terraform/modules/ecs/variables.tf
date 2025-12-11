variable "project_name" {
  description = "Name of the project"
}

variable "environment" {
  description = "Environment of this project"
}

variable "bucket_name" {
  description = "Name of the S3 bucket"
}

variable "producer_image" {
  description = "Docker image for the producer task"
}

variable "consumer_image" {
  description = "Docker image for the consumer task"
}

variable "sqs_queue_name" {
  description = "Name of the SQS queue for paper processing"
  type        = string
}

variable "ssm_parameter_arns" {
  description = "List of SSM parameter ARNs that ECS tasks can access"
  type        = list(string)
  default     = []
}

variable "ssm_parameters" {
  description = "Map of SSM parameter names for secrets"
  type = object({
    unstructured_api_key = string
    upstash_email        = string
    upstash_api_key      = string
    pinecone_api_key     = string
    redis_url            = string
    openai_api_key       = string
  })
}

variable "sqs_queue_url" {
  description = "URL of the SQS queue"
  type        = string
}

# Producer environment variables
variable "producer_env" {
  description = "Environment variables for producer task"
  type = object({
    arxiv_category = string
    max_results    = number
    max_pages      = number
  })
}

# Consumer environment variables
variable "consumer_env" {
  description = "Environment variables for consumer task"
  type = object({
    mode                        = string
    chunk_max_characters        = number
    chunk_new_after_n_chars     = number
    chunk_combine_under_n_chars = number
    embedding_model             = string
    embedding_token_threshold   = number
    pinecone_index_name         = string
    embedding_dimension         = string
  })
}

