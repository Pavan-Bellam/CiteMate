provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = "shared"
    }
  }
}

module "ecr" {
  source          = "../../modules/ecr"
  repository_name = var.project_name
}
