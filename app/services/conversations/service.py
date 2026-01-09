"""
Conversation Service - Manages conversation lifecycle.

A conversation represents a user session with the graph. Each conversation has:
- conversation_id: Main identifier, also used as graph thread_id for checkpointing

Interface and router thread IDs are stored in the graph state checkpoint.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from app.core.logging import get_logger
from app.models import Conversation


logger = get_logger(__name__, service="conversations")


class ConversationService:
    """Async service for managing conversations."""

    def __init__(self, mongo_client: AsyncIOMotorClient, database: str = "ras"):
        self.collection: AsyncIOMotorCollection = mongo_client[database]["conversations"]

    async def ensure_indexes(self):
        """Create indexes for efficient queries."""
        await self.collection.create_index("conversation_id", unique=True)
        logger.info("ConversationService indexes created")

    async def create(self) -> Conversation:
        """Create a new conversation."""
        now = datetime.utcnow()
        conversation = Conversation(
            conversation_id=str(uuid4()),
            created_at=now,
            updated_at=now,
        )

        await self.collection.insert_one(conversation.to_dict())
        logger.info("Conversation created", extra={"conversation_id": conversation.conversation_id})

        return conversation

    async def get(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        doc = await self.collection.find_one({"conversation_id": conversation_id})
        if doc:
            return Conversation.from_dict(doc)
        return None

    async def touch(self, conversation_id: str) -> bool:
        """Update the updated_at timestamp."""
        result = await self.collection.update_one(
            {"conversation_id": conversation_id},
            {"$set": {"updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0

    async def delete(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        result = await self.collection.delete_one({"conversation_id": conversation_id})
        if result.deleted_count > 0:
            logger.info("Conversation deleted", extra={"conversation_id": conversation_id})
            return True
        return False
