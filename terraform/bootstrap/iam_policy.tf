locals {
  environments = ["staging", "production"]
}

data "aws_iam_policy_document" "github_actions" {
  for_each = toset(local.environments)

  # General AWS access
  statement {
    sid    = "GeneralAccess"
    effect = "Allow"
    actions = [
      "sts:GetCallerIdentity",
      "ssm:DescribeParameters",
      "ec2:DescribeVpcs",
      "ec2:DescribeSubnets",
      "ec2:DescribeRouteTables",
      "ecs:DescribeTaskDefinition",
      "ecr:CreateRepository",
    ]
    resources = ["*"]
  }

  # S3 - Terraform state bucket
  statement {
    sid    = "S3ListBucket"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
    ]
    resources = ["arn:aws:s3:::${var.bucket_name}"]
    condition {
      test = "StringLike"
      variable = "s3:prefix"
      values = [
        "${each.key}/terraform*",
        "shared/terraform*",
      ]
    }
  }

  statement {
    sid    = "S3TerraformState"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListMultipartUploadParts",
    ]
    resources = [
      "arn:aws:s3:::${var.bucket_name}/shared/terraform/*",
      "arn:aws:s3:::${var.bucket_name}/${each.key}/terraform/*",
    ]
  }

  # S3 - Application data
#   statement {
#     sid    = "S3AppData"
#     effect = "Allow"
#     actions = [
#       "s3:GetObject",
#       "s3:PutObject",
#       "s3:DeleteObject",
#     ]
#     resources = [
#       "arn:aws:s3:::${var.bucket_name}/${each.key}/*",
#     ]
#   }

  # ECR
  statement {
    sid    = "ECRRead"
    effect = "Allow"
    actions = [
      "ecr:GetAuthorizationToken",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ECRPushPullTag"
    effect = "Allow"
    actions = [
      "ecr:DescribeRepositories",
      "ecr:ListTagsForResource",
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:PutImage",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
      "ecr:TagResource",
      "ecr:UntagResource",
    ]
    resources = [
      "arn:aws:ecr:${var.aws_region}:${var.aws_account_id}:repository/${var.project_name}-producer",
      "arn:aws:ecr:${var.aws_region}:${var.aws_account_id}:repository/${var.project_name}-consumer",
    ]
  }

  # SSM Parameters
  statement {
    sid    = "SSMParameters"
    effect = "Allow"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
      "ssm:PutParameter",
      "ssm:DeleteParameter",
      "ssm:ListTagsForResource",
      "ssm:AddTagsToResource",
    ]
    resources = [
      "arn:aws:ssm:${var.aws_region}:${var.aws_account_id}:parameter/${var.project_name}/${each.key}/*",
    ]
  }

  # SQS
  statement {
    sid    = "SQS"
    effect = "Allow"
    actions = [
      "sqs:CreateQueue",
      "sqs:DeleteQueue",
      "sqs:GetQueueAttributes",
      "sqs:SetQueueAttributes",
      "sqs:ListQueueTags",
      "sqs:TagQueue",
      "sqs:UntagQueue",
    ]
    resources = [
      "arn:aws:sqs:${var.aws_region}:${var.aws_account_id}:${var.project_name}-${each.key}-*",
    ]
  }

  # ECS
  statement {
    sid    = "ECS"
    effect = "Allow"
    actions = [
      "ecs:CreateCluster",
      "ecs:DeleteCluster",
      "ecs:DescribeClusters",
      "ecs:RegisterTaskDefinition",
      "ecs:DeregisterTaskDefinition",
      "ecs:ListTaskDefinitions",
      "ecs:CreateService",
      "ecs:UpdateService",
      "ecs:DeleteService",
      "ecs:DescribeServices",
      "ecs:TagResource",
    ]
    resources = ["*"]
  }

  # IAM - Roles for ECS tasks
  statement {
    sid    = "IAMRoles"
    effect = "Allow"
    actions = [
      "iam:GetRole",
      "iam:CreateRole",
      "iam:DeleteRole",
      "iam:UpdateRole",
      "iam:ListRolePolicies",
      "iam:ListInstanceProfilesForRole",
      "iam:ListAttachedRolePolicies",
      "iam:AttachRolePolicy",
      "iam:DetachRolePolicy",
      "iam:PutRolePolicy",
      "iam:DeleteRolePolicy",
      "iam:GetRolePolicy",
      "iam:TagRole",
      "iam:PassRole",
    ]
    resources = [
      "arn:aws:iam::${var.aws_account_id}:role/${var.project_name}-${each.key}-*",
    ]
  }

  # IAM - Policies for ECS tasks and EventBridge
  statement {
    sid    = "IAMPolicies"
    effect = "Allow"
    actions = [
      "iam:GetPolicy",
      "iam:GetPolicyVersion",
      "iam:ListPolicyVersions",
      "iam:CreatePolicy",
      "iam:DeletePolicy",
      "iam:TagPolicy",
      "iam:UntagPolicy",
    ]
    resources = [
      "arn:aws:iam::${var.aws_account_id}:policy/${var.project_name}-${each.key}-*",
    ]
  }

  # CloudWatch Logs
  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:DeleteLogGroup",
      "logs:DescribeLogGroups",
      "logs:PutRetentionPolicy",
      "logs:TagLogGroup",
    ]
    resources = [
      "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:log-group:/ecs/${var.project_name}-${each.key}/*",
    ]
  }

  # EC2 VPC (for ECS networking) requred for eventbridge
  statement {
    sid    = "EC2VPC"
    effect = "Allow"
    actions = [
      "ec2:DescribeVpcAttribute",
      "ec2:DescribeSecurityGroups",
      "ec2:CreateSecurityGroup",
      "ec2:DeleteSecurityGroup",
      "ec2:AuthorizeSecurityGroupIngress",
      "ec2:AuthorizeSecurityGroupEgress",
      "ec2:RevokeSecurityGroupIngress",
      "ec2:RevokeSecurityGroupEgress",
    ]
    resources = ["*"]
  }

  # EventBridge Scheduler
  statement {
    sid    = "EventBridge"
    effect = "Allow"
    actions = [
      "scheduler:CreateSchedule",
      "scheduler:DeleteSchedule",
      "scheduler:GetSchedule",
      "scheduler:UpdateSchedule",
      "scheduler:TagResource",
    ]
    resources = [
      "arn:aws:scheduler:${var.aws_region}:${var.aws_account_id}:schedule/default/${var.project_name}-${each.key}-*",
    ]
  }
}

resource "aws_iam_policy" "github_actions" {
  for_each = toset(local.environments)

  name   = "${var.project_name}-github-actions-${each.key}"
  policy = data.aws_iam_policy_document.github_actions[each.key].json
}
