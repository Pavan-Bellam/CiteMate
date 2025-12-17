import logging
import os
from pathlib import Path

from pinecone_text.sparse import BM25Encoder

logger = logging.getLogger(__name__)

# Default encoder path in src folder
DEFAULT_ENCODER_PATH = Path(__file__).parent / "bm25_encoder.json"


class BM25Client:
    """Client for generating BM25 sparse vectors."""

    def __init__(self, encoder_path: str = None):
        """
        Initialize BM25 encoder.

        Args:
            encoder_path: Path to saved encoder. If None, uses default from src folder.
        """
        path = encoder_path or DEFAULT_ENCODER_PATH
        if path and os.path.exists(path):
            logger.info(f"Loading BM25 encoder from {path}")
            self.encoder = BM25Encoder().load(str(path))
        else:
            logger.info("Using default BM25 encoder (MS MARCO)")
            self.encoder = BM25Encoder.default()

    def encode_documents(self, texts: list[str]) -> list[dict]:
        """
        Generate sparse vectors for documents.

        Args:
            texts: List of document texts.

        Returns:
            List of sparse vector dicts with 'indices' and 'values'.
        """
        sparse_vectors = []
        for text in texts:
            sparse = self.encoder.encode_documents(text)
            sparse_vectors.append({
                "indices": sparse["indices"],
                "values": sparse["values"],
            })
        return sparse_vectors

    def encode_query(self, query: str) -> dict:
        """
        Generate sparse vector for a query.

        Args:
            query: Query text.

        Returns:
            Sparse vector dict with 'indices' and 'values'.
        """
        sparse = self.encoder.encode_queries(query)
        return {
            "indices": sparse["indices"],
            "values": sparse["values"],
        }
