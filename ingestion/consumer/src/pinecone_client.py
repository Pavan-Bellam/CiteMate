import logging
import os

from pinecone import Pinecone, ServerlessSpec

logger = logging.getLogger(__name__)


class PineconeClient:
    """Client for storing vectors in Pinecone."""

    def __init__(self, api_key: str, index_name: str):
        index_name = f"{index_name}-{os.getenv("EMBEDDING_DIMENSION")}"
        self.pc = Pinecone(api_key=api_key)
        self.index = self._get_index(index_name=index_name)
        self.index_name = index_name

    def _get_index(self, index_name: str):
        if index_name not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=index_name,
                dimension=int(os.getenv("EMBEDDING_DIMENSION")),
                metric="cosine",
                spec=ServerlessSpec(cloud='aws', region='us-east-1')
            )
        return self.pc.Index(index_name)
    
    def _clean_metadata(self, metadata: dict) -> dict:
        """Remove null values from metadata - Pinecone doesn't accept them."""
        return {k: v for k, v in metadata.items() if v is not None}

    def upsert_vectors(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> int:
        """
        Upsert vectors with metadata to Pinecone.

        Args:
            ids: Vector IDs.
            embeddings: Embedding vectors.
            metadatas: Metadata dicts (must include 'text' for retrieval).

        Returns:
            Number of vectors upserted.
        """
        vectors = [
            {"id": id_, "values": embedding, "metadata": self._clean_metadata(metadata)}
            for id_, embedding, metadata in zip(ids, embeddings, metadatas)
        ]

        logger.debug(f"Upserting {len(vectors)} vectors to {self.index_name}")

        response = self.index.upsert(vectors=vectors)
        upserted = response.upserted_count

        logger.info(f"Upserted {upserted} vectors to Pinecone")
        return upserted
