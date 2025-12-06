import json
import logging

import boto3

logger = logging.getLogger(__name__)


class SQSClient:
    """Client for sending messages to SQS."""

    def __init__(self, queue_url: str):
        self.client = boto3.client("sqs")
        self.queue_url = queue_url

    def send_message(self, paper: dict, s3_key: str) -> str:
        """
        Send paper metadata to SQS.

        Args:
            paper: Paper metadata from ArXiv
            s3_key: S3 key where PDF was uploaded

        Returns:
            Message ID
        """
        message = {
            "arxiv_id": paper["arxiv_id"],
            "s3_key": s3_key,
            "title": paper["title"],
            "authors": paper["authors"],
            "abstract": paper["abstract"],
            "published": paper["published"],
            "categories": paper["categories"],
        }

        response = self.client.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps(message),
        )

        logger.debug(f"Sent message for {paper['arxiv_id']}: {response['MessageId']}")
        return response["MessageId"]
