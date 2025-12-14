variable "project_name" {
  description = "The name of the project"
  type = string
  default = "ras"
  validation {
    condition = length(var.project_name) > 0
    error_message = "Project name must be at least 1 character long"
  }
}

variable "aws_region" {
  description = "The AWS region to deploy the infrastructure"
  type = string
  default = "us-east-1"
}

variable "aws_account_id" {
  description = "The AWS account ID"
  type = string
}

variable "bucket_name" {
  description = "The name of the S3 bucket"
  type = string
}


variable "github_org" {
  description = "The GitHub organization"
  type = string
}

variable "github_repository" {
  description = "The GitHub repository"
  type = string
}

variable "main_branch" {
  description = "The main branch"
  type = string
}

variable "prod_branch" {
  description = "The production branch"
  type = string
}