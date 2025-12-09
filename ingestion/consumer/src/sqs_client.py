import json
import logging
from typing import Optional

import boto3

logger = logging.getLogger(__name__)


class SQSClient:
    """Client for receiving messages from SQS."""

    def __init__(self, queue_url: str):
        self.client = boto3.client("sqs")
        self.queue_url = queue_url

    def receive_message(self, wait_time: int = 20) -> Optional[dict]:
        """
        Receive a single message from the queue.

        Args:
            wait_time: Long polling wait time in seconds (max 20).

        Returns:
            Message dict with 'body' and 'receipt_handle', or None if no message.
        """
        response = self.client.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=wait_time,
        )

        messages = response.get("Messages", [])
        if not messages:
            return None

        message = messages[0]
        return {
            "body": json.loads(message["Body"]),
            "receipt_handle": message["ReceiptHandle"],
        }

    def delete_message(self, receipt_handle: str) -> None:
        """
        Delete a message from the queue after successful processing.

        Args:
            receipt_handle: Receipt handle from receive_message.
        """
        self.client.delete_message(
            QueueUrl=self.queue_url,
            ReceiptHandle=receipt_handle,
        )
        logger.debug("Deleted message from queue")
