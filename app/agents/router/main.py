"""
Router Agent - Central orchestrator for the multi-agent system.

The Router Agent maintains conversation history, manages the expert registry,
and routes questions to appropriate agents (Scout or existing Experts). It uses
structured output to indicate whether it needs more information or is ready
to provide a final answer.

Lifecycle:
    1. Receives user query with optional expert_registry from previous queries
    2. Checks for new experts and notifies the LLM
    3. Routes to Scout for knowledge base search or Experts for paper-specific Q&A
    4. Returns structured response with answer or questions for other agents
"""

import os
from typing import Any, Dict

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool
from langchain.messages import HumanMessage, ToolMessage
from langgraph.types import Command

from .prompt import ROUTER_AGENT_PROMPT
from .models import RouterState, RouterResponse
from app.core.lifespan import get_checkpointer
from app.agents.expert.main import create_thread
from app.core.logging import get_logger
from app.core.exceptions import (
    PaperNotFoundError,
    ExpertCreationError,
    LLMTimeoutError,
    LLMRateLimitError,
)


# =============================================================================
# Module Setup
# =============================================================================

logger = get_logger(__name__, agent="router")


# =============================================================================
# Tools
# =============================================================================

@tool
async def create_expert(paper_id: str, runtime: ToolRuntime[RouterState]) -> Command | str:
    """Spawn a new expert agent for a specific paper.

    Use this when you need deep analysis of a paper and no expert exists for it yet.
    Only use when you expect to ask MANY questions about that specific paper.

    Args:
        paper_id: The arxiv paper ID (e.g., '2512.02942v1').

    Returns:
        Command to update registry, or error message string.
    """
    logger.info("create_expert called", extra={"paper_id": paper_id})

    expert_registry = runtime.state.get('expert_registry', {})

    # Check if expert already exists
    if paper_id in expert_registry:
        logger.debug("Expert already exists", extra={"paper_id": paper_id})
        return f"Expert already exists for paper {paper_id}."

    try:
        thread_id, title, description = await create_thread(paper_id)
        logger.info("Expert created", extra={"paper_id": paper_id, "thread_id": thread_id, "title": title})

    except PaperNotFoundError:
        logger.warning("Paper not found", extra={"paper_id": paper_id})
        return f"Could not create expert: paper {paper_id} not found in the knowledge base."

    except (LLMTimeoutError, LLMRateLimitError) as e:
        logger.warning("Expert creation failed (retryable)", extra={"paper_id": paper_id, "error_type": type(e).__name__})
        return f"Could not create expert for paper {paper_id}: service temporarily unavailable. Try again later."

    except ExpertCreationError as e:
        logger.error("Expert creation failed", extra={"paper_id": paper_id, "error": str(e)})
        return f"Could not create expert for paper {paper_id}. The paper may be malformed or inaccessible."

    # Update registry
    expert_registry[paper_id] = {
        'thread_id': thread_id,
        'title': title,
        'description': description
    }

    return Command(
        update={
            "expert_registry": expert_registry,
            "messages": [
                ToolMessage(
                    content=f"Expert created for paper {paper_id}: {title}",
                    tool_call_id=runtime.tool_call_id
                )
            ]
        },
    )


@tool
async def get_expert_registry(runtime: ToolRuntime[RouterState]) -> str:
    """Get the list of available experts and what papers they cover.

    Call this to see which experts are available before routing questions.

    Returns:
        Formatted list of available experts, or message if none exist.
    """
    logger.debug("get_expert_registry called")

    registry = runtime.state.get('expert_registry', {})
    if not registry:
        return "No experts available yet."

    result = []
    for paper_id, info in registry.items():
        title = info.get('title', 'Unknown')
        description = info.get('description', 'No description')
        result.append(f"- {paper_id}: {title}\n  {description}")
    if result:
        return "\n".join(result)
    return "No experts available yet. Use create_expert if you have paper ids, else talk to scout."


# =============================================================================
# Agent Setup
# =============================================================================

_router_agent = None

REASONING = {"effort": "medium"}


def _get_agent():
    """Lazy initialization of router agent."""
    global _router_agent
    if _router_agent is None:
        model_name = os.environ.get("ROUTER_MODEL", "gpt-5")
        model = ChatOpenAI(model=model_name, reasoning=REASONING)
        _router_agent = create_agent(
            model=model,
            system_prompt=ROUTER_AGENT_PROMPT,
            checkpointer=get_checkpointer(),
            tools=[create_expert, get_expert_registry],
            state_schema=RouterState,
            response_format=RouterResponse
        )
        logger.info("Router agent initialized", extra={"model": model_name, "reasoning": REASONING})
    return _router_agent


# =============================================================================
# Public API
# =============================================================================

async def query(thread_id: str, query: str, expert_registry: Dict[str, Any] = None) -> Dict[str, Any]:
    """Run the Router agent with a query.

    The Router checks for new experts, routes the query appropriately, and
    returns either a final answer or questions for other agents.

    Args:
        thread_id: Conversation thread identifier for state persistence.
        query: The user's question or incoming answers from other agents.
        expert_registry: Current expert registry (from previous Scout queries).

    Returns:
        Dictionary with:
            - answer: Final answer (if ready), or None
            - expert_questions: Questions for experts, keyed by paper_id
            - scout_questions: Questions for Scout agent
            - expert_registry: Updated expert registry
    """
    expert_registry = expert_registry or {}
    config = {"configurable": {"thread_id": thread_id}}

    logger.info("Processing query", extra={"thread_id": thread_id})

    # Get router's current state to find new experts
    checkpoint = await get_checkpointer().aget(config)
    existing_registry = {}
    if checkpoint and checkpoint.get('channel_values'):
        existing_registry = checkpoint['channel_values'].get('expert_registry', {})

    # Find new experts by comparing incoming vs existing
    new_experts = []
    for paper_id, info in expert_registry.items():
        if paper_id not in existing_registry:
            title = info.get('title', 'Unknown')
            description = info.get('description', '')
            new_experts.append(f"- {paper_id}: {title}\n  {description}")

    # Build message content
    content = query
    if new_experts:
        content += f"\n\n## New Experts Available:\n" + "\n".join(new_experts)
        logger.debug("New experts found", extra={"count": len(new_experts)})

    # Invoke the agent
    response = await _get_agent().ainvoke(
        {
            "messages": [HumanMessage(content=content)],
            "expert_registry": expert_registry,
        },
        config
    )

    structured = response['structured_response']
    result = {
        "answer": structured.answer,
        "expert_questions": structured.expert_questions,
        "scout_questions": structured.scout_questions,
        "expert_registry": response.get('expert_registry', {}),
    }

    logger.info(
        "Query completed",
        extra={
            "thread_id": thread_id,
            "has_answer": structured.answer is not None,
            "expert_questions_count": len(structured.expert_questions or {}),
            "scout_questions_count": len(structured.scout_questions or []),
        }
    )

    return result
