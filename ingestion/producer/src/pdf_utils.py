import io
import logging

from pypdf import PdfReader

logger = logging.getLogger(__name__)


class TooManyPagesError(Exception):
    """Raised when PDF exceeds max page count."""
    pass


def check_page_count(pdf_bytes: bytes, max_pages: int) -> int:
    """
    Check if PDF has acceptable page count.

    Args:
        pdf_bytes: PDF content as bytes.
        max_pages: Maximum allowed pages.

    Returns:
        Actual page count.

    Raises:
        TooManyPagesError: If page count exceeds max_pages.
    """
    reader = PdfReader(io.BytesIO(pdf_bytes))
    page_count = len(reader.pages)

    if page_count > max_pages:
        raise TooManyPagesError(f"PDF has {page_count} pages, max allowed is {max_pages}")

    logger.debug(f"PDF has {page_count} pages (max: {max_pages})")
    return page_count
