resource "aws_ecr_repository" "producer" {
  name                 = "${var.repository_name}-producer"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration {
    scan_on_push = false
  }
}

resource "aws_ecr_repository" "consumer" {
  name                 = "${var.repository_name}-consumer"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = false
  }
}

