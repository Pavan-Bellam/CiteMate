import logging
import os
from datetime import date, timedelta

from src import ArxivClient, S3Client, setup_logging

logger = logging.getLogger(__name__)


def main() -> None:
    setup_logging()

    s3_client = S3Client(
        bucket_name=os.environ["BUCKET_NAME"],
        prefix=os.environ["BUCKET_PREFIX"],
    )

    # Fetch papers submitted yesterday
    target_date = date.today() - timedelta(days=1)

    uploaded = 0
    skipped = 0
    failed = 0

    with ArxivClient() as arxiv_client:
        papers = arxiv_client.fetch_papers(
            category="cs.LG",
            max_results=1,  # TODO: Change back to 10000 for production
            submitted_date=target_date,
        )
        for paper in papers:
            arxiv_id = paper["arxiv_id"]

            if s3_client.file_exists(arxiv_id):
                skipped += 1
                continue

            try:
                pdf_bytes = arxiv_client.download_pdf(paper["pdf_url"])
                s3_client.upload_pdf(arxiv_id, pdf_bytes)
                uploaded += 1
            except Exception as e:
                logger.error(f"Failed to process {arxiv_id}: {e}")
                failed += 1

    logger.info(f"Completed: uploaded={uploaded}, skipped={skipped}, failed={failed}")


if __name__ == "__main__":
    main()
