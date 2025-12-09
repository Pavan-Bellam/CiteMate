provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = "development"
      Developer   = var.developer
    }
  }
}

provider "upstash"{
  #set env variables 
  #$ export UPSTASH_EMAIL=<UPSTASH_EMAIL>
  #$ export UPSTASH_API_KEY=<UPSTASH_API_KEY>
}

module "storage" {
  source      = "../../modules/storage"
  bucket_name = var.bucket_name
  prefix      = "development/${var.developer}"
  folders     = var.storage_folders
}

module "sqs" {
  source     = "../../modules/sqs"
  queue_name = "${var.project_name}-dev-${var.developer}-papers"
}

module "redis" {
  source               = "../../modules/redis"
  redis_db_name        = var.redis_db_name
  redis_primary_region = var.redis_primary_region
  redis_tls            = var.redis_tls
}

