import logging
from pathlib import Path

from unstructured_client import UnstructuredClient as Client
from unstructured_client.models import shared, operations
from unstructured.chunking.title import chunk_by_title
from unstructured.staging.base import elements_from_dicts

logger = logging.getLogger(__name__)

FILTER_CATEGORIES = {"Header", "Footer", "PageNumber", "UncategorizedText"}


class UnstructuredClient:
    """Client for parsing PDFs using Unstructured API."""

    def __init__(
        self,
        api_key: str,
        chunk_max_characters: int = 1500,
        chunk_new_after_n_chars: int = 1000,
        chunk_combine_under_n_chars: int = 500,
    ):
        self.client = Client(api_key_auth=api_key)
        self.chunk_max_characters = chunk_max_characters
        self.chunk_new_after_n_chars = chunk_new_after_n_chars
        self.chunk_combine_under_n_chars = chunk_combine_under_n_chars

    def parse_pdf(self, file_path: Path) -> list[dict]:
        """
        Parse a PDF file into elements via API.

        Args:
            file_path: Path to the PDF file.

        Returns:
            List of raw element dicts from the API.
        """
        logger.debug(f"Parsing {file_path}")

        with open(file_path, "rb") as f:
            file_content = f.read()

        files = shared.Files(
            content=file_content,
            file_name=file_path.name,
        )

        partition_params = shared.PartitionParameters(
            files=files,
            strategy=shared.Strategy.AUTO,
            split_pdf_page=True,
            split_pdf_concurrency_level=15,
        )

        request = operations.PartitionRequest(partition_parameters=partition_params)
        response = self.client.general.partition(request=request)

        logger.debug(f"Parsed {len(response.elements)} elements from {file_path}")
        return response.elements

    def chunk_elements(self, raw_elements: list[dict]) -> list[dict]:
        """
        Chunk raw elements into semantic chunks.

        Args:
            raw_elements: Raw element dicts from parse_pdf.

        Returns:
            List of chunk dicts with text and metadata.
        """
        # Convert dicts to element objects
        elements = elements_from_dicts(raw_elements)

        # Filter out low-value elements
        filtered = [el for el in elements if el.category not in FILTER_CATEGORIES]
        logger.debug(f"Filtered {len(elements)} -> {len(filtered)} elements")

        # Chunk with full document context
        chunks = chunk_by_title(
            elements=filtered,
            max_characters=self.chunk_max_characters,
            new_after_n_chars=self.chunk_new_after_n_chars,
            combine_text_under_n_chars=self.chunk_combine_under_n_chars,
            multipage_sections=True,
        )

        # Build element lookup for section hierarchy
        element_lookup = {el["element_id"]: el for el in raw_elements}

        result = []
        for chunk in chunks:
            metadata = chunk.metadata
            orig_elements = getattr(metadata, "orig_elements", [])

            # Get section title from parent hierarchy
            section_title = None
            for orig_elem in orig_elements:
                parent_id = getattr(orig_elem.metadata, "parent_id", None)
                if parent_id:
                    section_title = self._get_section_title(parent_id, element_lookup)
                    if section_title:
                        break

            char_count = len(chunk.text)
            result.append({
                "type": chunk.category,
                "text": chunk.text,
                "metadata": {
                    "page_number": getattr(metadata, "page_number", None),
                    "section_title": section_title,
                    "char_count": char_count,
                    "estimated_tokens": char_count // 4,
                },
            })

        logger.debug(f"Created {len(result)} chunks")
        return result

    def _get_section_title(self, parent_id: str, lookup: dict) -> str | None:
        """Walk up parent chain to find section title."""
        current_id = parent_id
        while current_id:
            parent = lookup.get(current_id)
            if parent and parent.get("type") == "Title":
                return parent.get("text")
            current_id = parent.get("metadata", {}).get("parent_id") if parent else None
        return None
