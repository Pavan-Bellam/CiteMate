import logging
import time
from datetime import date, timedelta
from typing import Generator

import arxiv
import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0
ARXIV_REQUESTS_PER_MINUTE = 20


class ArxivClient:
    """Client for fetching papers and downloading PDFs from ArXiv."""

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        requests_per_minute: int = ARXIV_REQUESTS_PER_MINUTE,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._min_interval = 60.0 / requests_per_minute
        self._last_request_time: float = 0
        self._http_client: httpx.Client | None = None
        self._arxiv_client = arxiv.Client()

    def __enter__(self) -> "ArxivClient":
        self._http_client = httpx.Client(timeout=self.timeout)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._http_client:
            self._http_client.close()
            self._http_client = None

    def _build_query(
        self,
        categories: str,
        start_date: date | None,
        end_date: date | None,
    ) -> str:
        """Build ArXiv query string with optional date filter.

        Args:
            categories: Single category or comma-separated list (e.g., "cs.LG" or "cs.AI,cs.LG,cs.CL")
        """
        # Handle multiple categories
        cat_list = [c.strip() for c in categories.split(",")]
        if len(cat_list) == 1:
            query = f"cat:{cat_list[0]}"
        else:
            cat_query = " OR ".join(f"cat:{c}" for c in cat_list)
            query = f"({cat_query})"

        if start_date and end_date:
            start = start_date.strftime("%Y%m%d")
            end = end_date.strftime("%Y%m%d")
            query = f"{query} AND submittedDate:[{start}0000 TO {end}0000]"

        return query

    def fetch_papers(
        self,
        category: str,
        max_results: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Generator[dict, None, None]:
        """
        Fetch paper metadata from ArXiv.

        Args:
            category: ArXiv category (e.g., "cs.LG").
            max_results: Maximum number of papers to fetch.
            start_date: If provided with end_date, filter by submission date range.
            end_date: End of date range (exclusive).

        Yields:
            Paper metadata dictionaries.
        """
        query = self._build_query(category, start_date, end_date)
        logger.info(f"Fetching papers: query='{query}', max_results={max_results}")

        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
        )

        count = 0
        for paper in self._arxiv_client.results(search):
            arxiv_id = paper.entry_id.split("/")[-1]
            metadata = {
                "arxiv_id": arxiv_id,
                "title": paper.title,
                "authors": [a.name for a in paper.authors],
                "abstract": paper.summary,
                "pdf_url": paper.pdf_url,
                "published": paper.published.isoformat(),
                "categories": paper.categories,
            }
            count += 1
            yield metadata

        logger.info(f"Fetched {count} papers")

    def _wait_for_rate_limit(self) -> None:
        """Wait if needed to respect rate limit."""
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()

    def download_pdf(self, pdf_url: str) -> bytes:
        """
        Download PDF from URL with retry logic and rate limiting.

        Args:
            pdf_url: URL to the PDF.

        Returns:
            PDF content as bytes.

        Raises:
            httpx.HTTPError: If download fails after all retries.
        """
        if not self._http_client:
            raise RuntimeError("Client not initialized. Use 'with' statement.")

        last_exception: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                self._wait_for_rate_limit()
                response = self._http_client.get(pdf_url)
                response.raise_for_status()
                return response.content
            except httpx.HTTPStatusError as e:
                if e.response.status_code < 500:
                    raise
                last_exception = e
            except httpx.RequestError as e:
                last_exception = e

            if attempt < self.max_retries:
                delay = self.retry_delay * (2 ** (attempt - 1))
                logger.warning(
                    f"Download failed (attempt {attempt}/{self.max_retries}), "
                    f"retrying in {delay:.1f}s: {pdf_url}"
                )
                time.sleep(delay)

        logger.error(f"Download failed after {self.max_retries} attempts: {pdf_url}")
        raise last_exception  # type: ignore[misc]
