data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

#create ecs execution role
resource "aws_iam_role" "ecs_execution_role" {
  name = "${var.project_name}-${var.environment}-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

# Attach the AWS managed ECS policy
resource "aws_iam_role_policy_attachment" "ecs_execution_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# SSM parameter read access and CloudWatch Logs for execution role
resource "aws_iam_policy" "execution_extra_policy" {
  name = "${var.project_name}-${var.environment}-execution-extra-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameters", "ssm:GetParameter"]
        Resource = var.ssm_parameter_arns
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:/ecs/${var.project_name}-${var.environment}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "execution_extra_policy_attachment" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = aws_iam_policy.execution_extra_policy.arn
}

# Producer Role
resource "aws_iam_role" "producer_role" {
  name = "${var.project_name}-${var.environment}-producer-task-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_policy" "producer_policy" {
  name = "${var.project_name}-${var.environment}-producer-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "s3:PutObject"
        Resource = "arn:aws:s3:::${var.bucket_name}/${var.environment}/papers/pdfs/*"
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueUrl"
        ]
        Resource = "arn:aws:sqs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:${var.sqs_queue_name}"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "producer_policy_attachment" {
  role       = aws_iam_role.producer_role.name
  policy_arn = aws_iam_policy.producer_policy.arn
}

# Consumer Role
resource "aws_iam_role" "consumer_role" {
  name = "${var.project_name}-${var.environment}-consumer-task-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_policy" "consumer_policy" {
  name = "${var.project_name}-${var.environment}-consumer-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:GetQueueUrl"
        ]
        Resource = "arn:aws:sqs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:${var.sqs_queue_name}"
      },
      {
        Effect   = "Allow"
        Action   = "s3:GetObject"
        Resource = "arn:aws:s3:::${var.bucket_name}/${var.environment}/papers/pdfs/*"
      },
      {
        Effect   = "Allow"
        Action   = "s3:PutObject"
        Resource = "arn:aws:s3:::${var.bucket_name}/${var.environment}/papers/raw/*"
      },
      {
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = "arn:aws:s3:::${var.bucket_name}"
        Condition = {
          StringLike = {
            "s3:prefix" : "${var.environment}/papers/raw/*"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "consumer_policy_attachment" {
  role       = aws_iam_role.consumer_role.name
  policy_arn = aws_iam_policy.consumer_policy.arn
}
