import json
import logging
from dataclasses import dataclass

import redis

logger = logging.getLogger(__name__)

CHUNKS_KEY = "chunks:pending"
TOKENS_KEY = "chunks:token_count"


@dataclass
class ChunkData:
    arxiv_id: str
    chunk_index: int
    text: str
    token_count: int
    metadata: dict

    def to_dict(self) -> dict:
        return {
            "arxiv_id": self.arxiv_id,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "token_count": self.token_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChunkData":
        return cls(
            arxiv_id=data["arxiv_id"],
            chunk_index=data["chunk_index"],
            text=data["text"],
            token_count=data["token_count"],
            metadata=data["metadata"],
        )


class RedisClient:
    """Client for batching chunks in Redis."""

    def __init__(self, url: str, token_threshold: int):
        self.client = redis.from_url(url)
        self.token_threshold = token_threshold

    def push_chunk(self, chunk: ChunkData) -> int:
        """
        Push a chunk to the pending queue and update token count.

        Args:
            chunk: Chunk data to push.

        Returns:
            New total token count after push.
        """
        pipe = self.client.pipeline()
        pipe.rpush(CHUNKS_KEY, json.dumps(chunk.to_dict()))
        pipe.incrby(TOKENS_KEY, chunk.token_count)
        results = pipe.execute()

        new_count = results[1]
        logger.debug(f"Pushed chunk {chunk.arxiv_id}:{chunk.chunk_index}, total tokens: {new_count}")
        return new_count

    def get_token_count(self) -> int:
        """Get current accumulated token count."""
        count = self.client.get(TOKENS_KEY)
        return int(count) if count else 0

    def should_embed(self) -> bool:
        """Check if we've accumulated enough tokens to trigger embedding."""
        return self.get_token_count() >= self.token_threshold

    def pop_batch(self) -> list[ChunkData]:
        """
        Pop all pending chunks and reset token count.

        Returns:
            List of chunk data.
        """
        pipe = self.client.pipeline()
        pipe.lrange(CHUNKS_KEY, 0, -1)
        pipe.delete(CHUNKS_KEY)
        pipe.delete(TOKENS_KEY)
        results = pipe.execute()

        chunks_raw = results[0]
        chunks = [ChunkData.from_dict(json.loads(c)) for c in chunks_raw]

        logger.info(f"Popped {len(chunks)} chunks from queue")
        return chunks

    def get_pending_count(self) -> int:
        """Get number of pending chunks."""
        return self.client.llen(CHUNKS_KEY)

    def clear(self) -> None:
        """Clear all pending chunks and reset token count."""
        self.client.delete(CHUNKS_KEY, TOKENS_KEY)
        logger.info("Cleared pending chunks")
