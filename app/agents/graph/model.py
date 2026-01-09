"""State models for the Graph orchestration layer.

The Graph uses a shared state to coordinate data flow between Router, Scout,
and Expert agents. State fields are updated by each node as the graph executes.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from langchain.agents import AgentState


# =============================================================================
# Context Schema
# =============================================================================

@dataclass
class GraphContext:
    """Context for graph execution (currently unused, reserved for future)."""
    pass


# =============================================================================
# State Schema
# =============================================================================

class GraphState(AgentState):
    """Shared state for the multi-agent graph.

    This state flows through all nodes and accumulates data as agents respond.

    Attributes:
        # Interface fields
        interface_thread_id: Thread ID for Interface's document context.
        interface_paragraph: Current paragraph being analyzed.
        interface_paragraph_index: Index of current paragraph (0-based).
        interface_is_update: Whether current paragraph is an update.
        interface_grammar_corrections: Grammar/style issues from Interface.
        interface_logic_issues: Logic/consistency issues from Interface.
        interface_fact_questions: Questions to verify facts (sent to Router).
        interface_fact_results: Fact verification results from Router.

        # Router fields
        router_thread_id: Persistent thread ID for Router's conversation memory.
        expert_registry: Maps paper_id to expert info (thread_id, title, description).
        expert_questions: Questions to ask experts, keyed by paper_id.
        expert_answers: Answers from experts, keyed by paper_id.
        scout_questions: Questions to send to Scout for knowledge base search.
        scout_answers: Answers received from Scout.
        router_questions: Questions for Router (from Interface or direct).
        router_incoming_answers: Formatted answers to send back to Router.
        router_final_answer: Final answer when Router is done.
    """
    # Interface state
    interface_thread_id: str
    interface_paragraph: Optional[str]
    interface_paragraph_index: Optional[int]
    interface_is_update: bool
    interface_grammar_corrections: List[str]
    interface_logic_issues: List[str]
    interface_fact_questions: List[str]
    interface_fact_results: List[str]

    # Router state
    router_thread_id: str
    expert_registry: Dict[str, Dict[str, Any]]
    expert_questions: Dict[str, List[str]]
    expert_answers: Dict[str, str]
    scout_questions: List[str]
    scout_answers: List[str]
    router_questions: List[str]
    router_incoming_answers: List[str]
    router_final_answer: Optional[str]