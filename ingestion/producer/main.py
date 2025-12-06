import logging
import os
from datetime import date, timedelta

from src import ArxivClient, S3Client, SQSClient, setup_logging

logger = logging.getLogger(__name__)


def main() -> None:
    setup_logging()

    s3_client = S3Client(
        bucket_name=os.environ["BUCKET_NAME"],
        prefix=os.environ["BUCKET_PREFIX"],
    )
    sqs_client = SQSClient(queue_url=os.environ["QUEUE_URL"])

    # Fetch papers submitted yesterday
    target_date = date.today() - timedelta(days=1)

    uploaded = 0
    skipped = 0
    failed = 0

    with ArxivClient() as arxiv_client:
        papers = arxiv_client.fetch_papers(
            category=os.environ["ARXIV_CATEGORY"],
            max_results=int(os.environ["MAX_RESULTS"]),
            submitted_date=target_date,
        )
        for paper in papers:
            arxiv_id = paper["arxiv_id"]

            if s3_client.file_exists(arxiv_id):
                skipped += 1
                continue

            try:
                pdf_bytes = arxiv_client.download_pdf(paper["pdf_url"])
                s3_key = s3_client.upload_pdf(arxiv_id, pdf_bytes)
                sqs_client.send_message(paper, s3_key)
                uploaded += 1
            except Exception as e:
                logger.error(f"Failed to process {arxiv_id}: {e}")
                failed += 1

    logger.info(f"Completed: uploaded={uploaded}, skipped={skipped}, failed={failed}")


if __name__ == "__main__":
    main()
