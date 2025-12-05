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
