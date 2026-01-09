"""State and response models for the Router Agent.

The Router Agent maintains conversation state via MongoDB checkpointing and
uses structured output to route questions to appropriate agents.
"""

from typing import Annotated, Any, Dict, List, Optional

from langchain.agents import AgentState
from pydantic import BaseModel, Field


# =============================================================================
# State Reducers
# =============================================================================

def merge_dicts(current: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """Shallow merge dictionaries. Update overwrites existing keys."""
    return {**current, **update}


# =============================================================================
# State Schema
# =============================================================================

class RouterState(AgentState):
    """Extended agent state for Router with expert registry tracking.

    Attributes:
        expert_registry: Maps paper_id to expert info (thread_id, title, description).
                        Uses merge reducer to accumulate experts across invocations.
    """
    expert_registry: Annotated[Dict[str, Any], merge_dicts]


# =============================================================================
# Response Model
# =============================================================================

class RouterResponse(BaseModel):
    """Structured response from the Router Agent.

    The Router uses this to indicate its next action:
    - Set expert_questions/scout_questions when more information is needed
    - Set answer when ready to provide final response

    Only one of these should be set at a time.
    """

    expert_questions: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="Questions to ask experts, keyed by paper_id. Set when you need information from specific papers."
    )
    scout_questions: Optional[List[str]] = Field(
        default=None,
        description="Questions to ask scout. Set when you need to search the knowledge base."
    )
    answer: Optional[str] = Field(
        default=None,
        description="Final answer to the user's question. Only set when you have complete information with citations."
    )