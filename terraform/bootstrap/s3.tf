resource "aws_s3_bucket" "state_bucket" {
    bucket = "${var.bucket_name}"
    force_destroy = true

    tags = {
        Project = var.project_name
        service = "bootstrap"
    }
}

resource "aws_s3_bucket_versioning" "state_bucket_versioning" {
    bucket = aws_s3_bucket.state_bucket.id
    versioning_configuration {
      status = "Enabled"
    }
  }