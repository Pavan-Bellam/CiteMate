"""API dependencies for dependency injection."""

from fastapi import Depends

from app.core.lifespan import (
    get_checkpointer,
    get_retrieval_service,
    get_conversation_service,
)
from app.services.conversations import ConversationService
from app.services.retrieval import RetrievalService
from langgraph.checkpoint.mongodb import MongoDBSaver


def get_conversation_svc() -> ConversationService:
    """Dependency for ConversationService."""
    return get_conversation_service()


def get_retrieval_svc() -> RetrievalService:
    """Dependency for RetrievalService."""
    return get_retrieval_service()


def get_checkpointer_svc() -> MongoDBSaver:
    """Dependency for MongoDBSaver checkpointer."""
    return get_checkpointer()
