"""
Interface Agent Module

The Interface Agent is the user-facing layer that analyzes research paper paragraphs.
It handles grammar corrections, logic analysis, and fact verification by coordinating
with the Router agent.

Usage:
    from app.agents.interface import query

    # Analyze a new paragraph
    result = await query(
        thread_id="doc-123",
        paragraph="The attention mechanism allows...",
        paragraph_index=0,
        is_update=False
    )
    # Returns: {"grammar": [...], "logic": [...], "fact_questions": [...], "answer_to_user": "..."}
"""

from .main import query

__all__ = ["query"]
