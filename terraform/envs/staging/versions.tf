terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.0.0"
    }

    upstash = {
      source  = "upstash/upstash"
      version = ">= 2.1.0"
    }
  }

  backend "s3" {}
}
