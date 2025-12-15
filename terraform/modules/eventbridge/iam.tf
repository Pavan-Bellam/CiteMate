resource "aws_iam_role" "scheduler_role" {
    name = "${var.project_name}-${var.environment}-scheduler-role"
    assume_role_policy = jsonencode({
        "Version":"2012-10-17",		 	 	 
        "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "scheduler.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    })
}

resource "aws_iam_policy" "scheduler_policy" {
    name = "${var.project_name}-${var.environment}-scheduler-policy"
    policy = jsonencode({
        "Version": "2012-10-17",
        "Statement": [
            {
                Effect = "Allow",
                Action = [
                    "ecs:RunTask",
                ],
                Resource = [
                    var.producer_task_arn,
                    var.consumer_task_arn
                ]
            }
        ]
    })
}