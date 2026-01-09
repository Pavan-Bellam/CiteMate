"""
Scout Agent Module

The Scout Agent is a stateless retrieval agent that searches the knowledge base
and answers questions using retrieved chunks. When chunks are insufficient, it
can spawn Expert agents for deep paper analysis.

Usage:
    from app.agents.scout import query

    # Query the knowledge base
    result = await query("What is the attention mechanism?")
    # Returns: {"answer": "...", "expert_registry": {...}}
"""

from .main import query

__all__ = ["query"]
