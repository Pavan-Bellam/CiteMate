import logging

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3Client:
    """Client for uploading files to S3."""

    def __init__(self, bucket_name: str, prefix: str):
        self.client = boto3.client("s3")
        self.bucket_name = bucket_name
        self.prefix = prefix

    def upload_pdf(self, arxiv_id: str, content: bytes) -> str:
        """
        Upload PDF to S3.

        Args:
            arxiv_id: ArXiv paper ID (used as filename).
            content: PDF content as bytes.

        Returns:
            The S3 key where the file was uploaded.

        Raises:
            ClientError: If upload fails.
        """
        key = f"{self.prefix}/pdfs/{arxiv_id}.pdf"

        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content,
                ContentType="application/pdf",
            )
        except ClientError as e:
            logger.error(f"S3 upload failed for {arxiv_id}: {e.response['Error']['Message']}")
            raise

        return key

    def file_exists(self, arxiv_id: str) -> bool:
        """
        Check if a PDF already exists in S3.

        Args:
            arxiv_id: ArXiv paper ID.

        Returns:
            True if file exists, False otherwise.
        """
        key = f"{self.prefix}/pdfs/{arxiv_id}.pdf"

        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise
