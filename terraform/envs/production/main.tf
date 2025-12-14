provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = "production"
    }
  }
}

provider "upstash" {
  #set env variables
  #$ export UPSTASH_EMAIL=<UPSTASH_EMAIL>
  #$ export UPSTASH_API_KEY=<UPSTASH_API_KEY>
}

module "sqs" {
  source     = "../../modules/sqs"
  queue_name = "${var.project_name}-production-papers"
}

module "redis" {
  source               = "../../modules/redis"
  redis_db_name        = "${var.project_name}-production"
  redis_primary_region = var.redis_primary_region
  redis_tls            = var.redis_tls
}

module "ssm" {
  source = "../../modules/ssm"

  project_name         = var.project_name
  environment          = "production"
  unstructured_api_key = var.unstructured_api_key
  upstash_email        = var.upstash_email
  upstash_api_key      = var.upstash_api_key
  pinecone_api_key     = var.pinecone_api_key
  redis_url            = module.redis.redis_url
  openai_api_key       = var.openai_api_key
}

module "ecs" {
  source = "../../modules/ecs"

  project_name       = var.project_name
  environment        = "production"
  bucket_name        = var.bucket_name
  producer_image     = var.producer_image
  consumer_image     = var.consumer_image
  sqs_queue_name     = module.sqs.queue_name
  sqs_queue_url      = module.sqs.queue_url
  ssm_parameter_arns = module.ssm.parameter_arns
  ssm_parameters     = module.ssm.parameter_names

  producer_env = {
    arxiv_category = var.producer_arxiv_category
    max_results    = var.producer_max_results
    max_pages      = var.producer_max_pages
  }

  consumer_env = {
    mode                        = var.consumer_mode
    chunk_max_characters        = var.consumer_chunk_max_characters
    chunk_new_after_n_chars     = var.consumer_chunk_new_after_n_chars
    chunk_combine_under_n_chars = var.consumer_chunk_combine_under_n_chars
    embedding_model             = var.consumer_embedding_model
    embedding_token_threshold   = var.consumer_embedding_token_threshold
    pinecone_index_name         = var.consumer_pinecone_index_name
    embedding_dimension         = var.consumer_embedding_dimension
  }
}


module "eventbridge" {
  source = "../../modules/eventbridge"

  project_name = var.project_name
  environment = "production"
  producer_task_arn = module.ecs.producer_task_arn
  consumer_task_arn = module.ecs.consumer_task_arn
  cluster_arn = module.ecs.cluster_arn
}
