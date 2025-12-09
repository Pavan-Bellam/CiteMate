import json
import logging
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3Client:
    """Client for downloading and uploading files to S3."""

    def __init__(self, bucket_name: str, prefix: str):
        self.client = boto3.client("s3")
        self.bucket_name = bucket_name
        self.prefix = prefix

    @contextmanager
    def download_pdf(self, arxiv_id: str) -> Generator[Path, None, None]:
        """
        Download PDF from S3 to a temporary file.

        Args:
            arxiv_id: ArXiv paper ID.

        Yields:
            Path to the temporary PDF file.

        Raises:
            ClientError: If download fails.
        """
        s3_key = f"{self.prefix}/pdfs/{arxiv_id}.pdf"
        fd, temp_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        try:
            self.client.download_file(self.bucket_name, s3_key, temp_path)
            logger.debug(f"Downloaded {s3_key} to {temp_path}")
            yield Path(temp_path)
        except ClientError as e:
            logger.error(f"S3 download failed for {s3_key}: {e.response['Error']['Message']}")
            raise
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                logger.debug(f"Cleaned up {temp_path}")

    def save_raw_elements(self, arxiv_id: str, elements: list[dict]) -> str:
        """
        Save raw parsed elements to S3 as JSON.

        Args:
            arxiv_id: ArXiv paper ID.
            elements: Raw element dicts from Unstructured API.

        Returns:
            The S3 key where the file was uploaded.
        """
        s3_key = f"{self.prefix}/raw/{arxiv_id}.json"

        self.client.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=json.dumps(elements),
            ContentType="application/json",
        )
        logger.debug(f"Saved raw elements to {s3_key}")
        return s3_key

    def load_raw_elements(self, arxiv_id: str) -> list[dict] | None:
        """
        Load raw parsed elements from S3.

        Args:
            arxiv_id: ArXiv paper ID.

        Returns:
            List of element dicts, or None if not found.
        """
        s3_key = f"{self.prefix}/raw/{arxiv_id}.json"

        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=s3_key)
            elements = json.loads(response["Body"].read())
            logger.debug(f"Loaded raw elements from {s3_key}")
            return elements
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise

    def list_raw_arxiv_ids(self) -> list[str]:
        """
        List all arxiv IDs that have raw elements in S3.

        Returns:
            List of arxiv IDs.
        """
        prefix = f"{self.prefix}/raw/"
        arxiv_ids = []

        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.endswith(".json"):
                    # Extract arxiv_id from key: {prefix}/raw/{arxiv_id}.json
                    arxiv_id = key[len(prefix):-5]  # remove prefix and .json
                    arxiv_ids.append(arxiv_id)

        logger.debug(f"Found {len(arxiv_ids)} raw element files")
        return arxiv_ids
