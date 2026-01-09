"""Graph Runner - High-level interface for graph invocation.

Provides a clean API for invoking the graph. Thread IDs for interface and
router agents are stored in graph state checkpoint, not in conversations table.
"""

from dataclasses import dataclass
from uuid import uuid4

from app.core.logging import get_logger
from app.core.lifespan import get_checkpointer
from app.models import Conversation
from .main import get_graph


logger = get_logger(__name__, component="graph_runner")


@dataclass
class AnalysisResult:
    """Result of paragraph analysis."""
    conversation_id: str
    paragraph_index: int
    grammar_corrections: list[str]
    logic_issues: list[str]
    fact_results: list[str]
    expert_registry: dict


async def _get_thread_ids(conversation_id: str) -> tuple[str, str]:
    """Get or generate interface and router thread IDs.

    For new conversations, generates new UUIDs.
    For existing conversations, retrieves from checkpoint.

    Returns:
        Tuple of (interface_thread_id, router_thread_id)
    """
    checkpointer = get_checkpointer()
    config = {"configurable": {"thread_id": conversation_id}}

    checkpoint = await checkpointer.aget_tuple(config)
    if checkpoint and checkpoint.checkpoint:
        state = checkpoint.checkpoint.get("channel_values", {})
        interface_thread_id = state.get("interface_thread_id")
        router_thread_id = state.get("router_thread_id")

        if interface_thread_id and router_thread_id:
            logger.debug(
                "Retrieved thread IDs from checkpoint",
                extra={"conversation_id": conversation_id}
            )
            return interface_thread_id, router_thread_id

    # New conversation - generate new IDs
    interface_thread_id = str(uuid4())
    router_thread_id = str(uuid4())
    logger.debug(
        "Generated new thread IDs",
        extra={
            "conversation_id": conversation_id,
            "interface_thread_id": interface_thread_id,
            "router_thread_id": router_thread_id,
        }
    )
    return interface_thread_id, router_thread_id


async def analyze_paragraph(
    conversation: Conversation,
    paragraph: str,
    paragraph_index: int,
    is_update: bool = False,
) -> AnalysisResult:
    """Analyze a paragraph using the multi-agent graph.

    Args:
        conversation: The conversation (provides conversation_id for checkpointing).
        paragraph: The paragraph text to analyze.
        paragraph_index: Index of the paragraph (0-based).
        is_update: Whether this is an update to a previously analyzed paragraph.

    Returns:
        AnalysisResult with grammar corrections, logic issues, and fact results.
    """
    conversation_id = conversation.conversation_id

    logger.info(
        "Starting analysis",
        extra={
            "conversation_id": conversation_id,
            "paragraph_index": paragraph_index,
            "is_update": is_update,
        }
    )

    # Get or generate thread IDs
    interface_thread_id, router_thread_id = await _get_thread_ids(conversation_id)

    # Build initial state
    initial_state = {
        # Interface state
        "interface_thread_id": interface_thread_id,
        "interface_paragraph": paragraph,
        "interface_paragraph_index": paragraph_index,
        "interface_is_update": is_update,
        "interface_grammar_corrections": [],
        "interface_logic_issues": [],
        "interface_fact_questions": [],
        "interface_fact_results": [],
        # Router state
        "router_thread_id": router_thread_id,
        "router_questions": [],
        "router_incoming_answers": [],
        "scout_questions": [],
        "scout_answers": [],
        "expert_questions": {},
        "expert_answers": {},
        "expert_registry": {},
        "router_final_answer": None,
    }

    # Execute graph with thread_id for checkpointing
    graph = get_graph()
    config = {"configurable": {"thread_id": conversation_id}}
    response = await graph.ainvoke(initial_state, config=config)

    logger.info(
        "Analysis completed",
        extra={
            "conversation_id": conversation_id,
            "grammar_count": len(response.get("interface_grammar_corrections", [])),
            "logic_count": len(response.get("interface_logic_issues", [])),
            "fact_results_count": len(response.get("interface_fact_results", [])),
        }
    )

    return AnalysisResult(
        conversation_id=conversation_id,
        paragraph_index=paragraph_index,
        grammar_corrections=response.get("interface_grammar_corrections", []),
        logic_issues=response.get("interface_logic_issues", []),
        fact_results=response.get("interface_fact_results", []),
        expert_registry=response.get("expert_registry", {}),
    )
