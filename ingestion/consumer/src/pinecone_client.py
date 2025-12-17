import logging
import os

from pinecone import Pinecone, ServerlessSpec

logger = logging.getLogger(__name__)


class PineconeClient:
    """Client for storing vectors in Pinecone with separate dense and sparse indices."""

    def __init__(self, api_key: str, index_name: str):
        environment = os.getenv("ENVIRONMENT", "dev")
        embedding_dim = os.getenv("EMBEDDING_DIMENSION", "3072")

        self.dense_index_name = f"{index_name}-dense-{environment}-{embedding_dim}"
        self.sparse_index_name = f"{index_name}-sparse-{environment}"

        self.pc = Pinecone(api_key=api_key)
        self.dense_index = self._get_dense_index(self.dense_index_name)
        self.sparse_index = self._get_sparse_index(self.sparse_index_name)

    def _get_dense_index(self, index_name: str):
        """Get or create the dense vector index."""
        if index_name not in self.pc.list_indexes().names():
            logger.info(f"Creating dense index: {index_name}")
            self.pc.create_index(
                name=index_name,
                dimension=int(os.getenv("EMBEDDING_DIMENSION", "3072")),
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                vector_type="dense",
            )
        return self.pc.Index(index_name)

    def _get_sparse_index(self, index_name: str):
        """Get or create the sparse vector index."""
        if index_name not in self.pc.list_indexes().names():
            logger.info(f"Creating sparse index: {index_name}")
            self.pc.create_index(
                name=index_name,
                metric="dotproduct",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                vector_type="sparse",
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
        sparse_vectors: list[dict],
    ) -> dict:
        """
        Upsert vectors with metadata to Pinecone (dense and sparse indices).

        Args:
            ids: Vector IDs.
            embeddings: Embedding vectors (dense).
            metadatas: Metadata dicts (must include 'text' for retrieval).
            sparse_vectors: Sparse vectors for hybrid search (required).

        Returns:
            Dict with 'dense' and 'sparse' upserted counts.

        Raises:
            ValueError: If inputs are invalid or counts don't match.
        """
        # Validate inputs
        if not ids:
            raise ValueError("ids cannot be empty")
        if not embeddings:
            raise ValueError("embeddings cannot be empty")
        if not sparse_vectors:
            raise ValueError("sparse_vectors cannot be empty")

        n = len(ids)
        if len(embeddings) != n:
            raise ValueError(f"embeddings count ({len(embeddings)}) must equal ids count ({n})")
        if len(metadatas) != n:
            raise ValueError(f"metadatas count ({len(metadatas)}) must equal ids count ({n})")
        if len(sparse_vectors) != n:
            raise ValueError(f"sparse_vectors count ({len(sparse_vectors)}) must equal ids count ({n})")

        result = {"dense": 0, "sparse": 0}

        # Upsert dense vectors
        dense_vectors = []
        for id_, embedding, metadata in zip(ids, embeddings, metadatas):
            dense_vectors.append({
                "id": id_,
                "values": embedding,
                "metadata": self._clean_metadata(metadata),
            })

        logger.debug(f"Upserting {len(dense_vectors)} dense vectors to {self.dense_index_name}")
        dense_response = self.dense_index.upsert(vectors=dense_vectors)
        result["dense"] = dense_response.upserted_count
        logger.info(f"Upserted {result['dense']} dense vectors to Pinecone")

        # Upsert sparse vectors
        sparse_vecs = []
        for id_, sparse, metadata in zip(ids, sparse_vectors, metadatas):
            sparse_vecs.append({
                "id": id_,
                "sparse_values": sparse,
                "metadata": self._clean_metadata(metadata),
            })

        logger.debug(f"Upserting {len(sparse_vecs)} sparse vectors to {self.sparse_index_name}")
        sparse_response = self.sparse_index.upsert(vectors=sparse_vecs)
        result["sparse"] = sparse_response.upserted_count
        logger.info(f"Upserted {result['sparse']} sparse vectors to Pinecone")

        return result
