"""
Expert Agent Module

The Expert Agent is a stateful agent that maintains full context of a single
research paper. It answers questions based solely on the paper's content,
never hallucinating or introducing external knowledge.

Usage:
    from app.agents.expert import create_thread, query

    # Create an expert for a paper
    thread_id, title, description = await create_thread("2512.02942v1")

    # Ask questions
    response = await query("What methodology does this paper use?", thread_id)
"""

from .main import query, create_thread
from .models import ExpertAgentResponse

__all__ = ["query", "create_thread", "ExpertAgentResponse"]
