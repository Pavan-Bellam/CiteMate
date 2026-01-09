"""
Scout Agent - Stateless retrieval agent for answering questions.

The Scout Agent searches the knowledge base and answers questions using retrieved
chunks. When chunks are insufficient, it spawns Expert agents for deep paper
analysis. Unlike Expert, Scout is stateless and doesn't maintain conversation
history.

Workflow:
    1. Receives question with initial retrieved chunks
    2. Assesses if chunks can answer the question
    3. Either synthesizes answer or spawns Expert for specific papers
    4. Returns answer with citations to Router
"""

import os
from typing import Any, Dict, List, Optional

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import StructuredTool
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from langchain.tools import ToolRuntime, tool

from .prompt import SCOUT_AGENT_PROMPT
from .models import ScoutState
from app.agents.expert.main import query as expert_query, create_thread
from app.core.lifespan import get_retrieval_service
from app.core.logging import get_logger
from app.core.exceptions import (
    PaperNotFoundError,
    ExpertCreationError,
    ExpertQueryError,
    LLMTimeoutError,
    LLMRateLimitError,
    RetrievalServiceError,
)


# =============================================================================
# Module Setup
# =============================================================================

logger = get_logger(__name__, agent="scout")


# =============================================================================
# Helpers
# =============================================================================

def _filter_top_k_per_paper(chunks: List[Dict[str, Any]], k: int = 3) -> tuple[List[Dict[str, Any]], set]:
    """Filter chunks to keep only top k per arxiv_id, sorted by score.

    Returns:
        Tuple of (filtered_chunks, paper_ids_set)
    """
    paper_chunks: Dict[str, List[Dict[str, Any]]] = {}
    paper_ids: set = set()

    for chunk in chunks:
        arxiv_id = chunk.get("arxiv_id") or chunk.get("metadata", {}).get("arxiv_id", "unknown")
        if arxiv_id not in paper_chunks:
            paper_chunks[arxiv_id] = []
        paper_chunks[arxiv_id].append(chunk)
        if arxiv_id != "unknown":
            paper_ids.add(arxiv_id)

    # Take top k from each paper (chunks already sorted by score from retrieval)
    result = []
    for paper_chunk_list in paper_chunks.values():
        result.extend(paper_chunk_list[:k])

    # Sort final result by score descending
    result.sort(key=lambda x: x.get("score", 0), reverse=True)
    return result, paper_ids


# =============================================================================
# Tools
# =============================================================================

MAX_RETRIEVAL_ATTEMPTS = 3
FETCH_TOP_K = 50
CHUNKS_PER_PAPER = 3


@tool
async def sample_chunks(
    query: str,
    runtime: ToolRuntime[ScoutState],
) -> List[Dict[str, Any]] | str:
    """Retrieve relevant chunks from the knowledge base across multiple papers.

    Fetches top 50 chunks and filters to top 3 per paper. Previously seen papers
    are automatically excluded via Pinecone filter.

    Args:
        query: The search query. Make it specific and retrievable - use key terms,
               technical vocabulary, and concepts that would appear in paper text.

    Returns:
        List of chunks (max 3 per paper) with text and metadata, or error message.
    """
    # Check retrieval limit
    current_count = runtime.state.get('retrieval_count', 0)
    if current_count >= MAX_RETRIEVAL_ATTEMPTS:
        logger.warning("Retrieval limit reached", extra={"count": current_count, "max": MAX_RETRIEVAL_ATTEMPTS})
        return f"Retrieval limit reached ({MAX_RETRIEVAL_ATTEMPTS} attempts). Use query_paper for specific papers or spawn_and_ask for full context."

    # Increment counter
    runtime.state['retrieval_count'] = current_count + 1

    # Get already seen papers from state for exclusion
    seen_papers = list(runtime.state.get('seen_paper_ids', set()))

    logger.debug("Retrieving chunks", extra={
        "query": query[:100],
        "fetch_k": FETCH_TOP_K,
        "attempt": current_count + 1,
        "excluded_papers": len(seen_papers)
    })

    # Fetch more chunks, exclude seen papers via Pinecone filter
    chunks = await get_retrieval_service().retrieve(
        query,
        top_k=FETCH_TOP_K,
        exclude_papers=seen_papers if seen_papers else None
    )

    # Filter to top k per paper and extract paper IDs in one pass
    filtered_chunks, new_paper_ids = _filter_top_k_per_paper(chunks, k=CHUNKS_PER_PAPER)
    runtime.state['seen_paper_ids'] = runtime.state.get('seen_paper_ids', set()) | new_paper_ids

    logger.debug("Chunks filtered", extra={
        "raw_count": len(chunks),
        "filtered_count": len(filtered_chunks),
        "papers": len(new_paper_ids)
    })

    return filtered_chunks


@tool
async def query_paper(
    arxiv_id: str,
    query: str,
    runtime: ToolRuntime[ScoutState],
    top_k: int = 5,
) -> List[Dict[str, Any]] | str:
    """Query chunks from a specific paper by arxiv_id.

    Use this when you need more chunks from a paper you've already seen.
    Does NOT count against retrieval limit.

    Args:
        arxiv_id: The arxiv paper ID (e.g., '2310.06825').
        query: Search query for this specific paper. Make it retrievable - use
               terms that would appear in the paper text, not abstract questions.
        top_k: Number of chunks to retrieve. Defaults to 5.

    Returns:
        List of chunks from this specific paper.
    """
    logger.debug("Querying specific paper", extra={
        "arxiv_id": arxiv_id,
        "query": query[:100],
        "top_k": top_k
    })

    # Query with arxiv_id filter
    retrieval_service = get_retrieval_service()

    # Build filter for specific paper
    chunks = await retrieval_service._query_dense(
        query=query,
        top_k=top_k,
        include_metadata=True,
        filter={"arxiv_id": {"$eq": arxiv_id}}
    )

    # Format results
    result = [
        {
            "id": m.id,
            "score": m.score,
            "arxiv_id": m.metadata.get("arxiv_id") or arxiv_id,
            "metadata": m.metadata,
        }
        for m in chunks
    ]

    logger.debug("Paper query completed", extra={"arxiv_id": arxiv_id, "chunks": len(result)})
    return result


@tool
async def search_paper(
    title_keywords: str,
    runtime: ToolRuntime[ScoutState],
) -> List[Dict[str, str]]:
    """Search for papers by title or keywords.

    Use this when you know the paper name/title but don't have the arxiv_id.
    Searches paper titles in metadata and returns matching papers.

    Args:
        title_keywords: Paper title or keywords to search for.
                       Example: "Attention Is All You Need" or "BERT transformer"

    Returns:
        List of up to 5 unique papers with arxiv_id and title.
    """
    logger.debug("Searching for paper by title", extra={"keywords": title_keywords[:100]})

    retrieval_service = get_retrieval_service()

    # Use semantic search to get chunks, then filter by title metadata locally
    chunks = await retrieval_service._query_dense(
        query=title_keywords,
        top_k=100,  # Fetch more to find unique papers
        include_metadata=True,
    )

    # Normalize search keywords for matching
    keywords_lower = title_keywords.lower().split()

    # Extract unique papers and score by title match
    seen_ids = set()
    all_papers = []

    for chunk in chunks:
        metadata = chunk.metadata if hasattr(chunk, 'metadata') else chunk.get('metadata', {})
        arxiv_id = metadata.get('arxiv_id')
        title = metadata.get('title', '')

        if arxiv_id and arxiv_id not in seen_ids and title:
            seen_ids.add(arxiv_id)

            # Score by how many keywords match the title
            title_lower = title.lower()
            match_count = sum(1 for kw in keywords_lower if kw in title_lower)

            all_papers.append({
                "arxiv_id": arxiv_id,
                "title": title,
                "_match_score": match_count,
            })

    # Sort by match score (most keywords matched first), then take top 5
    all_papers.sort(key=lambda x: x["_match_score"], reverse=True)

    # Remove internal score and return top 5
    papers = [{"arxiv_id": p["arxiv_id"], "title": p["title"]} for p in all_papers[:5]]

    logger.debug("Paper search completed", extra={
        "keywords": title_keywords[:50],
        "found": len(papers),
        "top_match": papers[0]["title"] if papers else None
    })
    return papers


@tool
async def spawn_and_ask(paper_id: str, question: str, runtime: ToolRuntime[ScoutState]) -> str | Command:
    """Spawn an expert agent for a paper and ask it a question.

    Use this when you need full-paper context that chunks can't provide.

    Args:
        paper_id: The arxiv paper ID (e.g., '2512.02942v1').
        question: The question to ask about the paper.

    Returns:
        Answer string if expert exists, or Command to update registry if new expert created.
    """
    logger.info("spawn_and_ask called", extra={"paper_id": paper_id, "question_preview": question[:100]})

    experts_registry = runtime.state.get('expert_registry', {})

    # Reuse existing expert if available
    if paper_id in experts_registry:
        logger.debug("Reusing existing expert", extra={"paper_id": paper_id})
        thread_id = experts_registry[paper_id]['thread_id']

        try:
            answer = await expert_query(question, thread_id=thread_id)
            return answer.answer
        except (LLMTimeoutError, LLMRateLimitError) as e:
            logger.warning("Expert query failed (retryable)", extra={"paper_id": paper_id, "error_type": type(e).__name__})
            return f"Could not query expert for paper {paper_id}: service temporarily unavailable. Try again later."
        except ExpertQueryError as e:
            logger.error("Expert query failed", extra={"paper_id": paper_id, "error": str(e)})
            return f"Could not get answer from expert for paper {paper_id}."

    # Create new expert
    logger.info("Creating new expert", extra={"paper_id": paper_id})

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

    # Query the new expert
    try:
        answer = await expert_query(question, thread_id=thread_id)
    except Exception as e:
        logger.error("Expert query after creation failed", extra={"paper_id": paper_id, "error": str(e)})
        return f"Expert was created but failed to answer. Try asking about paper {paper_id} again."

    # Update registry with new expert
    experts_registry[paper_id] = {
        'thread_id': thread_id,
        'title': title,
        'description': description
    }

    return Command(
        update={
            "expert_registry": experts_registry,
            "messages": [
                ToolMessage(
                    content=answer.answer,
                    tool_call_id=runtime.tool_call_id
                )
            ]
        },
    )


# =============================================================================
# Agent Setup
# =============================================================================

_scout_agent = None

REASONING = {"effort": "medium"}


def _get_agent():
    """Lazy initialization of scout agent."""
    global _scout_agent
    if _scout_agent is None:
        model_name = os.environ.get("SCOUT_MODEL", "gpt-5")
        model = ChatOpenAI(model=model_name, reasoning=REASONING)
        _scout_agent = create_agent(
            model=model,
            system_prompt=SCOUT_AGENT_PROMPT,
            state_schema=ScoutState,
            tools=[sample_chunks, query_paper, search_paper, spawn_and_ask],
        )
        logger.info("Scout agent initialized", extra={"model": model_name, "reasoning": REASONING})
    return _scout_agent


# =============================================================================
# Public API
# =============================================================================

async def query(question: str) -> Dict[str, Any]:
    """Run the Scout agent with a question.

    Retrieves initial chunks and invokes the agent to synthesize an answer.
    The agent may call tools to retrieve more chunks or spawn experts.

    Args:
        question: The user's question to answer.

    Returns:
        Dictionary with:
            - answer: The synthesized answer string.
            - expert_registry: Any experts spawned during answering.

    Raises:
        RetrievalServiceError: If initial chunk retrieval fails.
        Exception: For other unexpected errors.
    """
    logger.info("Processing query")

    # Pre-retrieve initial chunks (fetch 50, filter to top 3 per paper)
    try:
        raw_chunks = await get_retrieval_service().retrieve(question, top_k=FETCH_TOP_K)
        initial_chunks, initial_paper_ids = _filter_top_k_per_paper(raw_chunks, k=CHUNKS_PER_PAPER)
        logger.debug("Initial chunks retrieved", extra={
            "raw_count": len(raw_chunks),
            "filtered_count": len(initial_chunks),
            "papers": len(initial_paper_ids)
        })
    except Exception as e:
        logger.error("Initial retrieval failed", extra={"error": str(e)})
        raise RetrievalServiceError(operation="initial_retrieve", reason=str(e)) from e

    # Format chunks for the initial message
    if initial_chunks:
        def _format_score(score):
            return f"{score:.3f}" if isinstance(score, (int, float)) else "N/A"

        chunks_text = "\n\n".join([
            f"[Chunk {i+1}] (Paper: {chunk.get('arxiv_id') or chunk.get('metadata', {}).get('arxiv_id', 'unknown')}, Score: {_format_score(chunk.get('score'))}):\n{chunk.get('metadata', {}).get('text', str(chunk))}"
            for i, chunk in enumerate(initial_chunks)
        ])
    else:
        chunks_text = "No initial chunks found."

    initial_message = f"Question: {question}\n\n## Initial Retrieved Chunks:\n{chunks_text}"

    # Invoke the agent with initialized state
    logger.debug("Invoking scout agent", extra={"message_length": len(initial_message)})

    response = await _get_agent().ainvoke({
        "messages": [{"role": "user", "content": initial_message}],
        "expert_registry": {},
        "retrieval_count": 1,  # Initial retrieval counts as first attempt
        "seen_paper_ids": initial_paper_ids,
    })

    # Extract text content from response (handles reasoning model content blocks)
    content = response['messages'][-1].content
    if isinstance(content, list):
        text_parts = [block.get('text', '') for block in content if block.get('type') == 'text']
        answer = '\n'.join(text_parts)
    else:
        answer = content

    logger.info("Query completed", extra={"answer_length": len(answer), "experts_spawned": len(response.get('expert_registry', {}))})

    return {
        "answer": answer,
        "expert_registry": response.get('expert_registry', {})
    }