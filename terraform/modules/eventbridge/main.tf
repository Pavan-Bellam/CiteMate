data "aws_vpc" "default" {
    default = true
}

data "aws_subnets" "default" {
    filter {
        name = "vpc-id"
        values = [data.aws_vpc.default.id]
    }
}

resource "aws_scheduler_schedule" "producer_trigger" {
    name = "${var.project_name}-${var.environment}-producer-trigger"
    group_name = "default"

    flexible_time_window {
      mode = "OFF"
    }

    schedule_expression = "cron(0 0 * * ? *)"

    target {
      arn = var.cluster_arn
      role_arn = aws_iam_role.scheduler_role.arn
      ecs_parameters {
        task_definition_arn = var.producer_task_arn
        task_count = 1
        launch_type = "FARGATE"
        network_configuration {
            subnets = data.aws_subnets.default.ids
            assign_public_ip = true #todo: make this false later   
        }
      }
    }
}

resource "aws_scheduler_schedule" "consumer_trigger" {
    name = "${var.project_name}-${var.environment}-consumer-trigger"
    group_name = "default"

    flexible_time_window {
      mode = "OFF"
    }

    schedule_expression = "cron(0 0 * * ? *)"

    target {
      arn = var.cluster_arn
      role_arn = aws_iam_role.scheduler_role.arn
      ecs_parameters {
        task_definition_arn = var.consumer_task_arn
        task_count = 1
        launch_type = "FARGATE"
        network_configuration {
            subnets = data.aws_subnets.default.ids
            assign_public_ip = true #todo: make this false later   
        }
      }
    }
}