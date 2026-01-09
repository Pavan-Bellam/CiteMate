"""Conversation API models."""

from datetime import datetime
from pydantic import BaseModel


class ConversationResponse(BaseModel):
    """Response for conversation retrieval."""
    conversation_id: str
    created_at: datetime
    updated_at: datetime


class ConversationCreateResponse(BaseModel):
    """Response for conversation creation."""
    conversation_id: str
