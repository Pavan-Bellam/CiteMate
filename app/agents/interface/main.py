"""
Interface Agent - User-facing paragraph analyzer.

The Interface Agent is the entry point for user interactions. It analyzes
research paper paragraphs for grammar, logic, and factual accuracy. For fact
verification, it coordinates with Router to query the knowledge base.

Lifecycle:
    1. User writes paragraph → sent to Interface with prefix
    2. Interface analyzes → returns corrections + fact_questions
    3. If fact_questions exist → Router verifies → answers return to Interface
    4. Interface synthesizes → returns final answer_to_user
"""

import os
from typing import Any, Dict, Optional

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain.messages import HumanMessage

from .prompt import INTERFACE_AGENT_PROMPT
from .models import InterfaceResponse
from app.core.lifespan import get_checkpointer
from app.core.logging import get_logger


# =============================================================================
# Module Setup
# =============================================================================

logger = get_logger(__name__, agent="interface")


# =============================================================================
# Agent Setup
# =============================================================================

_interface_agent = None

REASONING = {"effort": "low"}


def _get_agent():
    """Lazy initialization of interface agent."""
    global _interface_agent
    if _interface_agent is None:
        model_name = os.environ.get("INTERFACE_MODEL", "gpt-5")
        model = ChatOpenAI(model=model_name, reasoning=REASONING)
        _interface_agent = create_agent(
            model=model,
            system_prompt=INTERFACE_AGENT_PROMPT,
            checkpointer=get_checkpointer(),
            response_format=InterfaceResponse
        )
        logger.info("Interface agent initialized", extra={"model": model_name, "reasoning": REASONING})
    return _interface_agent


# =============================================================================
# Public API
# =============================================================================

async def query(
    thread_id: str,
    paragraph: Optional[str] = None,
    paragraph_index: Optional[int] = None,
    is_update: bool = False,
    fact_verification_results: Optional[str] = None,
) -> Dict[str, Any]:
    """Analyze a paragraph or process fact verification results.

    This function handles two scenarios:
    1. New/updated paragraph: Analyzes for grammar, logic, identifies facts
    2. Fact verification: Receives Router answers and returns fact_results

    Args:
        thread_id: Document thread identifier for state persistence.
        paragraph: The paragraph text to analyze (for new/update).
        paragraph_index: Index of the paragraph in the document (0-based).
        is_update: True if this is an update to existing paragraph.
        fact_verification_results: Answers from Router about factual claims.

    Returns:
        Dictionary with:
            - grammar_corrections: List of grammar issues (or None)
            - logic_issues: List of logic problems (or None)
            - fact_questions: Questions for Router (or None)
            - fact_results: Verification results (or None)

    Raises:
        ValueError: If neither paragraph nor fact_verification_results provided.
    """
    config = {"configurable": {"thread_id": thread_id}}

    # Build message based on input type
    if paragraph is not None and paragraph_index is not None:
        prefix = "UPDATED" if is_update else "NEW"
        content = f"[{prefix} PARAGRAPH {paragraph_index}] {paragraph}"
        logger.info(
            "Analyzing paragraph",
            extra={
                "thread_id": thread_id,
                "paragraph_index": paragraph_index,
                "is_update": is_update,
                "length": len(paragraph)
            }
        )
    elif fact_verification_results is not None:
        content = f"[FACT VERIFICATION] {fact_verification_results}"
        logger.info(
            "Processing fact verification",
            extra={"thread_id": thread_id, "results_length": len(fact_verification_results)}
        )
    else:
        raise ValueError("Must provide either paragraph or fact_verification_results")

    # Invoke agent
    response = await _get_agent().ainvoke(
        {"messages": [HumanMessage(content=content)]},
        config
    )

    structured = response['structured_response']
    result = {
        "grammar_corrections": structured.grammar_corrections,
        "logic_issues": structured.logic_issues,
        "fact_questions": structured.fact_questions,
        "fact_results": structured.fact_results,
    }

    logger.info(
        "Query completed",
        extra={
            "thread_id": thread_id,
            "has_grammar": bool(structured.grammar_corrections),
            "has_logic": bool(structured.logic_issues),
            "has_fact_questions": bool(structured.fact_questions),
            "has_fact_results": bool(structured.fact_results),
        }
    )

    return result
