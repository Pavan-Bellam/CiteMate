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

# Policy for CI/CD to push images - attach to OIDC role later
resource "aws_iam_policy" "ecr_push" {
  name        = "${var.repository_name}-ecr-push-policy"
  description = "Policy for pushing Docker images to ${var.repository_name} repositories"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "GetAuthorizationToken"
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
      {
        Sid    = "PushImages"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = [
          aws_ecr_repository.producer.arn,
          aws_ecr_repository.consumer.arn
        ]
      }
    ]
  })
}
