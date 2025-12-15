# =============================================================================
# Developer Role
# =============================================================================

resource "aws_iam_role" "developer_role" {
    name = "${var.project_name}-developer-role"
    description = "Role for developers to access development resources"

    assume_role_policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
            {
                Effect = "Allow"
                Principal = {
                    AWS = "arn:aws:iam::${var.aws_account_id}:root"
                }
                Action = [
                    "sts:AssumeRole",
                    "sts:SetSourceIdentity"
                ]
                Condition = {
                    StringEquals = {
                        "sts:SourceIdentity": "$${aws:username}"
                    }
                }
            }
        ]
    })

    tags = {
        Project = var.project_name
        service = "bootstrap"
    }
}

resource "aws_iam_policy" "developer_terraform_state_policy" {
    name = "${var.project_name}-developer-terraform-state-policy"
    description = "Policy for developers to access their terraform state"

    policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
            {
                Effect = "Allow"
                Action = "s3:ListBucket"
                Resource = "arn:aws:s3:::${var.bucket_name}"
                Condition = {
                    StringLike = {
                        "s3:prefix": "development/$${aws:SourceIdentity}/terraform/*"
                    }
                }
            },
            {
                Effect = "Allow"
                Action = ["s3:GetObject", "s3:PutObject"]
                Resource = "arn:aws:s3:::${var.bucket_name}/development/$${aws:SourceIdentity}/terraform/terraform.tfstate"
            },
            {
                Effect = "Allow"
                Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
                Resource = "arn:aws:s3:::${var.bucket_name}/development/$${aws:SourceIdentity}/terraform/terraform.tfstate.tflock"
            }
        ]
    })

    tags = {
        Project = var.project_name
        service = "bootstrap"
    }
}

resource "aws_iam_policy" "developer_infrastructure_policy" {
    name = "${var.project_name}-developer-infrastructure-policy"
    description = "Policy for developers to create infrastructure in their workspace"

    policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
            {
                Sid = "AllowS3BucketAccess"
                Effect = "Allow"
                Action = [
                    "s3:ListBucket",
                    "s3:ListBucketVersions"
                ]
                Resource = "arn:aws:s3:::${var.bucket_name}"
                Condition = {
                    StringLike = {
                        "s3:prefix": "development/$${aws:SourceIdentity}/*"
                    }
                }
            },
            {
                Sid = "AllowS3ObjectAccess"
                Effect = "Allow"
                Action = [
                    "s3:GetObject",
                    "s3:GetObjectVersion",
                    "s3:GetObjectTagging",
                    "s3:PutObject",
                    "s3:PutObjectTagging",
                    "s3:PutObjectAcl",
                    "s3:DeleteObject",
                    "s3:ListMultipartUploadParts"
                ]
                Resource = "arn:aws:s3:::${var.bucket_name}/development/$${aws:SourceIdentity}/*"
            },
            {
                Sid = "AllowECRRepositoryAccess"
                Effect = "Allow"
                Action = [
                    "ecr:CreateRepository",
                    "ecr:DeleteRepository",
                    "ecr:DescribeRepositories",
                    "ecr:ListTagsForResource",
                    "ecr:TagResource",
                    "ecr:GetAuthorizationToken"
                ]
                Resource = "arn:aws:ecr:${var.aws_region}:${var.aws_account_id}:repository/${var.project_name}-dev-$${aws:SourceIdentity}-*"
            },
            {
                Sid = "AllowECRAuth"
                Effect = "Allow"
                Action = "ecr:GetAuthorizationToken"
                Resource = "*"
            },
            {
                Sid = "AllowIAMPolicyManagement"
                Effect = "Allow"
                Action = [
                    "iam:CreatePolicy",
                    "iam:DeletePolicy",
                    "iam:GetPolicy",
                    "iam:GetPolicyVersion",
                    "iam:ListPolicyVersions"
                ]
                Resource = "arn:aws:iam::${var.aws_account_id}:policy/${var.project_name}-dev-$${aws:SourceIdentity}-*"
            },
            {
                Sid = "AllowSQSQueueManagement"
                Effect = "Allow"
                Action = [
                    "sqs:CreateQueue",
                    "sqs:DeleteQueue",
                    "sqs:GetQueueAttributes",
                    "sqs:GetQueueUrl",
                    "sqs:SetQueueAttributes",
                    "sqs:TagQueue",
                    "sqs:UntagQueue",
                    "sqs:ListQueueTags"
                ]
                Resource = "arn:aws:sqs:${var.aws_region}:${var.aws_account_id}:${var.project_name}-dev-$${aws:SourceIdentity}-*"
            },
            {
                Sid = "AllowSQSQueueAccess"
                Effect = "Allow"
                Action = [
                    "sqs:SendMessage",
                    "sqs:ReceiveMessage",
                    "sqs:DeleteMessage",
                    "sqs:GetQueueAttributes",
                    "sqs:GetQueueUrl"
                ]
                Resource = "arn:aws:sqs:${var.aws_region}:${var.aws_account_id}:${var.project_name}-dev-$${aws:SourceIdentity}-*"
            }
        ]
    })

    tags = {
        Project = var.project_name
        service = "bootstrap"
    }
}

resource "aws_iam_role_policy_attachment" "developer_terraform_state_attachment" {
    role = aws_iam_role.developer_role.name
    policy_arn = aws_iam_policy.developer_terraform_state_policy.arn
}

resource "aws_iam_role_policy_attachment" "developer_infrastructure_attachment" {
    role = aws_iam_role.developer_role.name
    policy_arn = aws_iam_policy.developer_infrastructure_policy.arn
}

# =============================================================================
# Developers Group
# =============================================================================

resource "aws_iam_group" "developers" {
    name = "${var.project_name}-developers"
}

resource "aws_iam_policy" "assume_developer_role_policy" {
    name = "${var.project_name}-assume-developer-role-policy"
    description = "Policy to allow assuming the developer role and setting source identity"

    policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
            {
                Effect = "Allow"
                Action = [
                    "sts:AssumeRole",
                    "sts:SetSourceIdentity"
                ]
                Resource = aws_iam_role.developer_role.arn
            }
        ]
    })

    tags = {
        Project = var.project_name
        service = "bootstrap"
    }
}

resource "aws_iam_group_policy_attachment" "developers_assume_role" {
    group = aws_iam_group.developers.name
    policy_arn = aws_iam_policy.assume_developer_role_policy.arn
}

# create github oidc roles
resource "aws_iam_role" "github_stage_oidc_role" {
    name = "${var.project_name}-github-stage-oidc-role"
    assume_role_policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
            {
                Effect = "Allow"
                Principal = {
                    Federated = "arn:aws:iam::${var.aws_account_id}:oidc-provider/token.actions.githubusercontent.com"
                }
                Action = "sts:AssumeRoleWithWebIdentity"
                Condition = {
                    StringEquals = {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                        "token.actions.githubusercontent.com:sub": "repo:${var.github_org}/${var.github_repository}:ref:refs/heads/${var.main_branch}"
                    }
                }
            }
        ]
    })
}

resource "aws_iam_role" "github_prod_oidc_role" {
    name = "${var.project_name}-github-prod-oidc-role"
    assume_role_policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
            {
                Effect = "Allow"
                Principal = {
                    Federated = "arn:aws:iam::${var.aws_account_id}:oidc-provider/token.actions.githubusercontent.com"
                }
                Action = "sts:AssumeRoleWithWebIdentity"
                Condition = {
                    StringEquals = {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                        "token.actions.githubusercontent.com:sub": "repo:${var.github_org}/${var.github_repository}:ref:refs/heads/${var.prod_branch}"
                    }
                }
            }
        ]
    })
}


# Attach policies to github oidc roles
resource "aws_iam_role_policy_attachment" "github_stage_actions" {
    role       = aws_iam_role.github_stage_oidc_role.name
    policy_arn = aws_iam_policy.github_actions["staging"].arn
}

resource "aws_iam_role_policy_attachment" "github_prod_actions" {
    role       = aws_iam_role.github_prod_oidc_role.name
    policy_arn = aws_iam_policy.github_actions["production"].arn
}

