"""
Graph Module - LangGraph orchestration for the multi-agent system.

The Graph coordinates Interface, Router, Scout, and Expert agents using
LangGraph's StateGraph with conditional branching and parallel execution.

Usage:
    from app.agents.graph import analyze_paragraph, AnalysisResult
    from app.services.conversations import ConversationService

    conversation = conversation_service.create()
    result = await analyze_paragraph(
        conversation=conversation,
        paragraph="Your text here...",
        paragraph_index=0,
    )
"""

from .main import get_graph
from .runner import analyze_paragraph, AnalysisResult

__all__ = [
    "get_graph",
    "analyze_paragraph",
    "AnalysisResult",
]
