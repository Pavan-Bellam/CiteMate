"""Paragraph analysis endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from app.agents.graph import analyze_paragraph, AnalysisResult
from app.api.dependencies import get_conversation_svc
from app.api.models import AnalyzeRequest, AnalyzeResponse
from app.core.logging import get_logger
from app.services.conversations import ConversationService


logger = get_logger(__name__, component="api.analysis")
router = APIRouter()


@router.post("", response_model=AnalyzeResponse)
async def analyze(
    request: AnalyzeRequest,
    conversation_service: ConversationService = Depends(get_conversation_svc),
):
    """Analyze a paragraph for grammar, logic, and factual issues.

    If conversation_id is not provided, a new conversation is created automatically.
    The conversation_id in the response can be used for subsequent paragraphs.
    """
    # Get or create conversation
    if request.conversation_id:
        conversation = await conversation_service.get(request.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        await conversation_service.touch(request.conversation_id)
    else:
        conversation = await conversation_service.create()

    logger.info(
        "Analysis requested",
        extra={
            "conversation_id": conversation.conversation_id,
            "paragraph_index": request.paragraph_index,
            "is_update": request.is_update,
        }
    )

    result: AnalysisResult = await analyze_paragraph(
        conversation=conversation,
        paragraph=request.paragraph,
        paragraph_index=request.paragraph_index,
        is_update=request.is_update,
    )

    logger.info(
        "Analysis completed",
        extra={
            "conversation_id": result.conversation_id,
            "grammar_count": len(result.grammar_corrections),
            "logic_count": len(result.logic_issues),
            "fact_count": len(result.fact_results),
        }
    )

    return AnalyzeResponse(
        conversation_id=result.conversation_id,
        paragraph_index=result.paragraph_index,
        grammar_corrections=result.grammar_corrections,
        logic_issues=result.logic_issues,
        fact_results=result.fact_results,
        expert_count=len(result.expert_registry),
    )
