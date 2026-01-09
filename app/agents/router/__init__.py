"""
Router Agent Module

The Router Agent is the central orchestrator that maintains conversation history,
manages the expert registry, and routes questions to appropriate agents (Scout or
existing Experts).

Usage:
    from app.agents.router import query

    # Query with conversation persistence
    result = await query(
        thread_id="conversation-123",
        query="What is attention mechanism?",
        expert_registry={}  # or existing registry from previous queries
    )
    # Returns: {"answer": "...", "expert_questions": {...}, "scout_questions": [...], "expert_registry": {...}}
"""

from .main import query

__all__ = ["query"]
