"""
Expert Agent - Stateful paper-specific Q&A agent.

The Expert Agent maintains full context of a single research paper and answers
questions based solely on that paper's content. Each expert is identified by
a unique thread_id and persists conversation history via MongoDB checkpointing.

Lifecycle:
    1. create_thread(paper_id) - Fetches paper, creates expert, returns thread_id
    2. query(question, thread_id) - Ask questions using the thread_id

The agent uses structured output (ExpertAgentResponse) to ensure consistent
response format across all queries.
"""

import os
from uuid import uuid4

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from .prompt import EXPERT_AGENT_PROMPT
from .models import ExpertAgentResponse
from .utils import get_markdown_of_paper
from app.core.lifespan import get_checkpointer
from app.core.logging import get_logger
import openai

from app.core.exceptions import (
    ExpertQueryError,
    ExpertCreationError,
    PaperNotFoundError,
    LLMTimeoutError,
    LLMRateLimitError,
)


# =============================================================================
# Module Setup
# =============================================================================

logger = get_logger(__name__, agent="expert")

_expert_agent = None


REASONING = {"effort": "medium"}


def _get_agent():
    """Lazy initialization of expert agent."""
    global _expert_agent
    if _expert_agent is None:
        model_name = os.environ.get("EXPERT_MODEL", "gpt-5")
        model = ChatOpenAI(model=model_name, reasoning=REASONING)
        _expert_agent = create_agent(
            model=model,
            system_prompt=EXPERT_AGENT_PROMPT,
            response_format=ExpertAgentResponse,
            checkpointer=get_checkpointer()
        )
        logger.info("Expert agent initialized", extra={"model": model_name, "reasoning": REASONING})
    return _expert_agent


# =============================================================================
# Public API
# =============================================================================

async def query(question: str, thread_id: str) -> ExpertAgentResponse:
    """Query an existing expert with a question.

    Args:
        question: The question to ask about the paper.
        thread_id: Expert thread identifier (from create_thread).

    Returns:
        ExpertAgentResponse containing the answer.

    Raises:
        LLMTimeoutError: If the LLM request times out.
        LLMRateLimitError: If rate limit is exceeded.
        ExpertQueryError: If the LLM call fails for other reasons.
    """
    logger.debug("Processing query", extra={"thread_id": thread_id})

    try:
        response = await _get_agent().ainvoke(
            {"messages": [{"role": "user", "content": question}]},
            {"configurable": {"thread_id": thread_id}}
        )
        return response['structured_response']

    except openai.APITimeoutError as e:
        logger.error("LLM timeout", extra={"thread_id": thread_id})
        raise LLMTimeoutError(agent="expert", timeout_seconds=0) from e

    except openai.RateLimitError as e:
        retry_after = getattr(e, 'retry_after', None)
        logger.error("LLM rate limit", extra={"thread_id": thread_id, "retry_after": retry_after})
        raise LLMRateLimitError(agent="expert", retry_after=retry_after) from e

    except Exception as e:
        logger.error("Query failed", extra={"thread_id": thread_id, "error": str(e), "error_type": type(e).__name__})
        raise ExpertQueryError(thread_id=thread_id, reason=str(e)) from e


async def create_thread(paper_id: str) -> tuple[str, str, str]:
    """Create a new expert for a paper.

    Fetches the parsed paper from S3, converts it to markdown, and initializes an
    expert agent with the paper's full content. The expert then provides a
    title and description of what it can answer.

    Args:
        paper_id: ArXiv paper ID (e.g., "2512.02942v1").

    Returns:
        Tuple of (thread_id, title, description) where:
            - thread_id: Unique identifier for querying this expert.
            - title: Paper's title.
            - description: Brief summary of paper's scope.

    Raises:
        PaperNotFoundError: If paper doesn't exist in S3.
        ExpertCreationError: If expert initialization fails.
    """
    logger.debug("Creating expert thread", extra={"paper_id": paper_id})

    # Fetch and convert paper to markdown
    try:
        paper_markdown = get_markdown_of_paper(paper_id)
    except PaperNotFoundError:
        raise
    except Exception as e:
        logger.error("Failed to get paper", extra={"paper_id": paper_id, "error": str(e)})
        raise ExpertCreationError(paper_id=paper_id, reason=f"Paper retrieval failed: {e}") from e

    # Initialize expert with paper content
    thread_id = str(uuid4())
    first_message = (
        f"This is the paper:\n\n{paper_markdown}\n\n"
        "Please provide the title and a 2-3 sentence description of this paper "
        "so I understand what questions you can answer."
    )

    try:
        response = await query(first_message, thread_id=thread_id)
        logger.info("Expert created", extra={"paper_id": paper_id, "thread_id": thread_id})
        return thread_id, response.title, response.description

    except (LLMTimeoutError, LLMRateLimitError):
        # Re-raise LLM errors as-is for upstream handling
        raise

    except ExpertQueryError as e:
        raise ExpertCreationError(paper_id=paper_id, reason=str(e)) from e