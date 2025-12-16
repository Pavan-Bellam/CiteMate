resource "aws_ecs_task_definition" "producer" {
  family                   = "${var.project_name}-${var.environment}-producer"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.producer_role.arn
  container_definitions = jsonencode([
    {
      name      = "producer"
      image     = var.producer_image
      essential = true
      environment = [
        { name = "BUCKET_NAME", value = var.bucket_name },
        { name = "BUCKET_PREFIX", value = "${var.environment}/papers" },
        { name = "QUEUE_URL", value = var.sqs_queue_url },
        { name = "ARXIV_CATEGORY", value = var.producer_env.arxiv_category },
        { name = "MAX_RESULTS", value = tostring(var.producer_env.max_results) },
        { name = "MAX_PAGES", value = tostring(var.producer_env.max_pages) }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/${var.project_name}-${var.environment}/producer"
          "awslogs-region"        = data.aws_region.current.region
          "awslogs-stream-prefix" = "ecs"
          "awslogs-create-group"  = "true"
        }
      }
    }
  ])
}

resource "aws_ecs_task_definition" "consumer" {
  family                   = "${var.project_name}-${var.environment}-consumer"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.consumer_role.arn
  container_definitions = jsonencode([
    {
      name      = "consumer"
      image     = var.consumer_image
      essential = true
      environment = [
        { name = "BUCKET_NAME", value = var.bucket_name },
        { name = "BUCKET_PREFIX", value = "${var.environment}/papers" },
        { name = "QUEUE_URL", value = var.sqs_queue_url },
        { name = "ENVIRONMENT", value = var.environment },
        { name = "MODE", value = var.consumer_env.mode },
        { name = "CHUNK_MAX_CHARACTERS", value = tostring(var.consumer_env.chunk_max_characters) },
        { name = "CHUNK_NEW_AFTER_N_CHARS", value = tostring(var.consumer_env.chunk_new_after_n_chars) },
        { name = "CHUNK_COMBINE_UNDER_N_CHARS", value = tostring(var.consumer_env.chunk_combine_under_n_chars) },
        { name = "EMBEDDING_MODEL", value = var.consumer_env.embedding_model },
        { name = "EMBEDDING_TOKEN_THRESHOLD", value = tostring(var.consumer_env.embedding_token_threshold) },
        { name = "PINECONE_INDEX_NAME", value = var.consumer_env.pinecone_index_name },
        { name = "EMBEDDING_DIMENSION", value = var.consumer_env.embedding_dimension }
      ]
      secrets = [
        {
          name      = "UNSTRUCTURED_API_KEY"
          valueFrom = "arn:aws:ssm:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:parameter${var.ssm_parameters.unstructured_api_key}"
        },
        {
          name      = "UPSTASH_EMAIL"
          valueFrom = "arn:aws:ssm:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:parameter${var.ssm_parameters.upstash_email}"
        },
        {
          name      = "UPSTASH_API_KEY"
          valueFrom = "arn:aws:ssm:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:parameter${var.ssm_parameters.upstash_api_key}"
        },
        {
          name      = "PINECONE_API_KEY"
          valueFrom = "arn:aws:ssm:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:parameter${var.ssm_parameters.pinecone_api_key}"
        },
        {
          name      = "REDIS_URL"
          valueFrom = "arn:aws:ssm:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:parameter${var.ssm_parameters.redis_url}"
        },
        {
          name      = "OPENAI_API_KEY"
          valueFrom = "arn:aws:ssm:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:parameter${var.ssm_parameters.openai_api_key}"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/${var.project_name}-${var.environment}/consumer"
          "awslogs-region"        = data.aws_region.current.region
          "awslogs-stream-prefix" = "ecs"
          "awslogs-create-group"  = "true"
        }
      }
    }
  ])
}
