"""Application lifespan management for FastAPI."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from langgraph.checkpoint.mongodb import MongoDBSaver
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.logging import get_logger
from app.services.retrieval import RetrievalService
from app.services.conversations import ConversationService


logger = get_logger(__name__, service="lifespan")


# =============================================================================
# Singleton Registry
# =============================================================================

_mongo_client: AsyncIOMotorClient | None = None
_checkpointer: MongoDBSaver | None = None
_retrieval_service: RetrievalService | None = None
_conversation_service: ConversationService | None = None


def get_checkpointer() -> MongoDBSaver:
    """Get the MongoDB checkpointer singleton."""
    if _checkpointer is None:
        raise RuntimeError("Checkpointer not initialized. Ensure lifespan has started.")
    return _checkpointer


def get_retrieval_service() -> RetrievalService:
    """Get the retrieval service singleton."""
    if _retrieval_service is None:
        raise RuntimeError("RetrievalService not initialized. Ensure lifespan has started.")
    return _retrieval_service


def get_conversation_service() -> ConversationService:
    """Get the conversation service singleton."""
    if _conversation_service is None:
        raise RuntimeError("ConversationService not initialized. Ensure lifespan has started.")
    return _conversation_service


# =============================================================================
# Lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI = None):
    """
    Manage application lifespan - initialize singletons on startup, cleanup on shutdown.

    All initialized services are available via get_* functions after startup.
    Can be used standalone for testing (without FastAPI app).
    """
    global _mongo_client, _checkpointer, _retrieval_service, _conversation_service

    logger.info("Starting application")

    # Initialize MongoDB (async)
    mongodb_uri = os.environ["MONGODB_URI"]
    _mongo_client = AsyncIOMotorClient(mongodb_uri)
    

    # Initialize conversation service (async)
    _conversation_service = ConversationService(_mongo_client)
    await _conversation_service.ensure_indexes()
    logger.info("ConversationService initialized")

    # Initialize retrieval service
    _retrieval_service = RetrievalService()
    logger.info("RetrievalService initialized")

    with MongoDBSaver.from_conn_string(mongodb_uri) as checkpointer:
        _checkpointer = checkpointer
        logger.info("MongoDB checkpointer initialized")
        logger.info("Application startup complete")

        yield

    # Cleanup on shutdown
    logger.info("Shutting down application")

    # Close retrieval service (Pinecone connections)
    if _retrieval_service is not None:
        await _retrieval_service.close()
        _retrieval_service = None
        logger.info("RetrievalService closed")

    # Close MongoDB connection
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None
        _checkpointer = None
        _conversation_service = None
        logger.info("MongoDB connection closed")

    logger.info("Application shutdown complete")
