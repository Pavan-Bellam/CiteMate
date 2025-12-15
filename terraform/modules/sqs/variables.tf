variable "queue_name" {
  description = "Name of the SQS queue"
  type        = string
}

variable "visibility_timeout_seconds" {
  description = "Time a message is hidden after being received (seconds)"
  type        = number
  default     = 600 # 10 minutes
}

variable "message_retention_seconds" {
  description = "How long messages are kept in queue (seconds)"
  type        = number
  default     = 1209600 # 14 days
}

variable "receive_wait_time_seconds" {
  description = "Long polling wait time (seconds)"
  type        = number
  default     = 20
}

variable "max_receive_count" {
  description = "Number of receives before message goes to DLQ"
  type        = number
  default     = 3
}

variable "dlq_message_retention_seconds" {
  description = "How long messages are kept in DLQ (seconds)"
  type        = number
  default     = 1209600 # 14 days
}
