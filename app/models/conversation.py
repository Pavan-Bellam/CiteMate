"""Conversation document model."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Conversation:
    """Conversation document stored in MongoDB.

    The conversation_id is also used as the graph thread_id for checkpointing.
    Interface and router thread IDs are stored in the graph state checkpoint,
    not in this document.
    """
    conversation_id: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict:
        return {
            "conversation_id": self.conversation_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Conversation":
        return cls(
            conversation_id=data["conversation_id"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )
