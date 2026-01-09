"""Conversation management endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_conversation_svc
from app.api.models import ConversationResponse, ConversationCreateResponse
from app.core.logging import get_logger
from app.services.conversations import ConversationService


logger = get_logger(__name__, component="api.conversations")
router = APIRouter()


@router.post("", response_model=ConversationCreateResponse, status_code=201)
async def create(service: ConversationService = Depends(get_conversation_svc)):
    """Create a new conversation."""
    conversation = await service.create()
    logger.info("Conversation created", extra={"conversation_id": conversation.conversation_id})
    return ConversationCreateResponse(conversation_id=conversation.conversation_id)


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get(conversation_id: str, service: ConversationService = Depends(get_conversation_svc)):
    """Get a conversation by ID."""
    conversation = await service.get(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationResponse(
        conversation_id=conversation.conversation_id,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.delete("/{conversation_id}", status_code=204)
async def delete(conversation_id: str, service: ConversationService = Depends(get_conversation_svc)):
    """Delete a conversation."""
    if not await service.delete(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    logger.info("Conversation deleted", extra={"conversation_id": conversation_id})
