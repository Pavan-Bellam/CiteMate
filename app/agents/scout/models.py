"""State models for the Scout Agent.

The Scout Agent uses custom state to track experts it spawns during question
answering. This state is passed back to the Router for registry updates.
"""

from typing import Annotated, Dict, Any, Set
from langchain.agents import AgentState


# =============================================================================
# State Reducers
# =============================================================================

def merge_dicts(current: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """Shallow merge dictionaries. Update overwrites existing keys."""
    return {**current, **update}


def merge_sets(current: Set[str], update: Set[str]) -> Set[str]:
    """Union sets. Accumulates seen paper IDs across tool calls."""
    return current | update


# =============================================================================
# State Schema
# =============================================================================

class ScoutState(AgentState):
    """Extended agent state for Scout with expert registry tracking.

    Attributes:
        expert_registry: Maps paper_id to expert info (thread_id, title, description).
                        Uses merge reducer to accumulate experts across tool calls.
        retrieval_count: Number of sample_chunks calls made. Used to enforce limit.
        seen_paper_ids: Set of arxiv_ids already retrieved. Used for Pinecone filtering.
    """
    expert_registry: Annotated[Dict[str, Any], merge_dicts]
    retrieval_count: int
    seen_paper_ids: Annotated[Set[str], merge_sets]