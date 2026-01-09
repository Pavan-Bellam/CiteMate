"""
Graph Orchestration - LangGraph-based multi-agent coordination.

This module defines the StateGraph that coordinates Interface, Router, Scout,
and Expert agents. The graph uses conditional branching for dynamic routing
and supports parallel execution when multiple agents need to be queried.

Graph Structure:
    START → interface (analyze) → [branch]
                                    ├── create_router_request → router → [branch]
                                    │                                      ├── expert ─┐
                                    │                                      ├── scout ──┼→ create_router_request (loop)
                                    │                                      └── interface (synthesize) → END
                                    └── END (no fact questions, direct answer)
"""

import asyncio
from typing import Any, Dict, List

from langgraph.graph import StateGraph, START, END

from app.agents.interface.main import query as interface_query
from app.agents.expert.main import query as expert_query
from app.agents.scout.main import query as scout_query
from app.agents.router.main import query as router_query
from app.core.logging import get_logger
from .model import GraphState, GraphContext


# =============================================================================
# Module Setup
# =============================================================================

logger = get_logger(__name__, component="graph")


# =============================================================================
# Graph Nodes - Interface
# =============================================================================

async def analyze_paragraph(state: GraphState) -> Dict[str, Any]:
    """Interface analyzes a new/updated paragraph.

    Returns grammar corrections, logic issues, and fact questions.
    """
    interface_thread_id = state['interface_thread_id']
    paragraph = state.get('interface_paragraph')
    paragraph_index = state.get('interface_paragraph_index')
    is_update = state.get('interface_is_update', False)

    logger.info(
        "analyze_paragraph starting",
        extra={
            "thread_id": interface_thread_id,
            "paragraph_index": paragraph_index,
            "is_update": is_update
        }
    )

    if paragraph is None or paragraph_index is None:
        logger.error("analyze_paragraph called without paragraph")
        return {
            "interface_grammar_corrections": [],
            "interface_logic_issues": [],
            "interface_fact_questions": [],
            "interface_fact_results": ["Error: No paragraph provided"],
        }

    result = await interface_query(
        thread_id=interface_thread_id,
        paragraph=paragraph,
        paragraph_index=paragraph_index,
        is_update=is_update,
    )

    logger.info(
        "analyze_paragraph completed",
        extra={
            "grammar_count": len(result.get('grammar_corrections') or []),
            "logic_count": len(result.get('logic_issues') or []),
            "fact_questions_count": len(result.get('fact_questions') or []),
        }
    )

    return {
        "interface_grammar_corrections": result.get('grammar_corrections') or [],
        "interface_logic_issues": result.get('logic_issues') or [],
        "interface_fact_questions": result.get('fact_questions') or [],
        # Clear paragraph input after processing
        "interface_paragraph": None,
    }


async def process_fact_results(state: GraphState) -> Dict[str, Any]:
    """Interface processes fact verification results from Router.

    Called after Router returns with fact verification answers.
    """
    interface_thread_id = state['interface_thread_id']
    router_answer = state.get('router_final_answer', '')

    logger.info(
        "process_fact_results starting",
        extra={"thread_id": interface_thread_id, "has_router_answer": bool(router_answer)}
    )

    result = await interface_query(
        thread_id=interface_thread_id,
        fact_verification_results=router_answer,
    )

    logger.info(
        "process_fact_results completed",
        extra={"thread_id": interface_thread_id, "fact_results_count": len(result.get('fact_results') or [])}
    )

    return {
        "interface_fact_results": result.get('fact_results') or [],
        # Clear router answer and fact questions after processing
        "router_final_answer": None,
        "interface_fact_questions": [],
    }


# =============================================================================
# Graph Nodes - Scout/Expert
# =============================================================================

async def ask_scout(state: GraphState) -> Dict[str, Any]:
    """Query Scout agent with all pending questions in parallel.

    Scout searches the knowledge base and may spawn new experts.
    Results are collected and expert_registry is updated with any new experts.
    """
    questions = state.get('scout_questions', [])
    logger.info("ask_scout starting", extra={"question_count": len(questions)})

    if not questions:
        logger.warning("ask_scout called with no questions")
        return {"scout_answers": [], "expert_registry": state.get('expert_registry', {})}

    # Execute all scout queries in parallel
    tasks = [scout_query(question) for question in questions]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    answers = []
    expert_registry = dict(state.get('expert_registry', {}))

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error("Scout query failed", extra={"question_index": i, "error": str(result)})
            answers.append(f"Scout query failed for question: {questions[i]}")
        else:
            answers.append(result['answer'])
            expert_registry.update(result.get('expert_registry', {}))

    logger.info(
        "ask_scout completed",
        extra={
            "answers_count": len(answers),
            "experts_count": len(expert_registry),
            "expert_papers": list(expert_registry.keys())
        }
    )

    return {
        "scout_answers": answers,
        "expert_registry": expert_registry
    }


async def ask_expert(state: GraphState) -> Dict[str, Any]:
    """Query Expert agents with pending questions in parallel.

    Each paper's questions are combined and sent to its expert.
    Missing experts are logged and skipped gracefully.
    """
    expert_questions = state.get('expert_questions', {})
    expert_registry = state.get('expert_registry', {})

    logger.info("ask_expert starting", extra={"expert_count": len(expert_questions)})

    if not expert_questions:
        logger.warning("ask_expert called with no questions")
        return {"expert_answers": {}}

    # Build tasks for each expert
    tasks = []
    paper_ids = []
    failed_questions = {}

    for paper_id, question_list in expert_questions.items():
        if paper_id not in expert_registry:
            failed_questions[paper_id] = "Expert not found in registry, please spawn before asking a question to this expert"
            logger.error("Expert not found in registry", extra={"paper_id": paper_id})
            continue

        thread_id = expert_registry[paper_id].get('thread_id')
        if not thread_id:
            failed_questions[paper_id] = "Expert missing, please spawn before asking a question to this expert"
            logger.error("Expert missing thread_id", extra={"paper_id": paper_id})
            continue

        formatted_questions = "Questions:\n" + "\n".join(f"- {q}" for q in question_list)
        tasks.append(expert_query(question=formatted_questions, thread_id=thread_id))
        paper_ids.append(paper_id)

    if not tasks:
        logger.warning("No valid expert queries to execute")
        return {"expert_answers": {}}

    # Execute in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    answers = {}
    for paper_id, result in zip(paper_ids, results):
        if isinstance(result, Exception):
            logger.error("Expert query failed", extra={"paper_id": paper_id, "error": str(result)})
            answers[paper_id] = f"Expert query failed: {str(result)}"
        else:
            answers[paper_id] = result.answer
    answers.update(failed_questions)
    logger.info("ask_expert completed", extra={"answers_count": len(answers)})

    return {"expert_answers": answers}


async def ask_router(state: GraphState) -> Dict[str, Any]:
    """Query Router agent with questions or incoming answers.

    Router decides whether to ask more questions or provide a final answer.
    """
    router_thread_id = state['router_thread_id']
    answers = state.get('router_incoming_answers', [])
    questions = state.get('router_questions', [])
    expert_registry = state.get('expert_registry', {})

    logger.info(
        "ask_router starting",
        extra={
            "thread_id": router_thread_id,
            "has_questions": bool(questions),
            "has_answers": bool(answers),
            "expert_count": len(expert_registry)
        }
    )

    # Validate input
    if questions and answers:
        raise ValueError("Cannot have both questions and answers")
    if not questions and not answers:
        raise ValueError("Must have either questions or answers")

    # Build query string
    if questions:
        query = "\n".join(questions) if isinstance(questions, list) else questions
    else:
        query = "\n".join(answers) if isinstance(answers, list) else answers

    # Call router
    response = await router_query(
        thread_id=router_thread_id,
        query=query,
        expert_registry=expert_registry,
    )

    # Router returned final answer
    if response['answer']:
        logger.info("ask_router completed with final answer", extra={"thread_id": router_thread_id})
        return {
            "router_final_answer": response['answer'],
            "expert_questions": {},
            "scout_questions": [],
            "expert_registry": response.get('expert_registry', {}),
            "router_questions": [],
            "router_incoming_answers": [],
        }

    # Router needs more information
    expert_questions = response.get('expert_questions') or {}
    scout_questions = response.get('scout_questions') or []

    logger.info(
        "ask_router completed with follow-up questions",
        extra={
            "thread_id": router_thread_id,
            "expert_questions_count": len(expert_questions),
            "scout_questions_count": len(scout_questions)
        }
    )

    return {
        "expert_questions": expert_questions,
        "scout_questions": scout_questions,
        "expert_registry": response.get('expert_registry', {}),
        "router_questions": [],
        "router_incoming_answers": [],
    }


def create_router_request(state: GraphState) -> Dict[str, Any]:
    """Prepare state for router node by formatting answers or passing questions.

    This node acts as a junction point that:
    - Passes interface fact questions as router questions (first entry from interface)
    - Passes through direct router questions
    - Formats expert/scout answers for subsequent router calls
    """
    questions = state.get('router_questions', [])
    interface_fact_questions = state.get('interface_fact_questions', [])
    expert_answers = state.get('expert_answers', {})
    scout_answers = state.get('scout_answers', [])

    logger.debug(
        "create_router_request",
        extra={
            "has_questions": bool(questions),
            "has_interface_fact_questions": bool(interface_fact_questions),
            "has_expert_answers": bool(expert_answers),
            "has_scout_answers": bool(scout_answers)
        }
    )

    # Interface fact questions become router questions
    if interface_fact_questions:
        return {
            "router_questions": interface_fact_questions,
            "interface_fact_questions": [],  # Clear after passing
            "expert_answers": {},
            "scout_answers": []
        }

    # Pass through direct questions
    if questions:
        return {
            "router_questions": questions,
            "expert_answers": {},
            "scout_answers": []
        }

    # Format answers for router
    formatted = []

    if expert_answers:
        formatted.append("## Expert Answers")
        for paper_id, answer in expert_answers.items():
            formatted.append(f"**Paper {paper_id}:**\n{answer}")

    if scout_answers:
        formatted.append("## Scout Answers")
        for i, answer in enumerate(scout_answers, 1):
            formatted.append(f"**Answer {i}:**\n{answer}")

    return {
        "router_incoming_answers": formatted,
        "expert_answers": {},
        "scout_answers": []
    }


# =============================================================================
# Graph Branching
# =============================================================================

def branch_from_interface(state: GraphState) -> str:
    """Determine next destination after interface analysis.

    Returns:
        - "end" if no fact questions (analysis complete)
        - "router" if fact questions need verification
    """
    fact_questions = state.get('interface_fact_questions', [])

    if fact_questions:
        logger.debug("branch_from_interface: router", extra={"fact_questions_count": len(fact_questions)})
        return "router"

    logger.debug("branch_from_interface: END (no fact questions)")
    return "end"


def branch_from_router(state: GraphState) -> List[str] | str:
    """Determine next destination(s) based on router response.

    Returns:
        - "interface" if router has final answer (go back for fact results)
        - List of destinations ["expert", "scout"] for parallel execution
        - Single destination if only one agent needs querying
    """
    if state.get('router_final_answer'):
        logger.debug("branch_from_router: interface (fact results)")
        return "interface"

    destinations = []
    if state.get('expert_questions'):
        destinations.append('expert')
    if state.get('scout_questions'):
        destinations.append('scout')

    if not destinations:
        logger.warning("branch_from_router: no destinations, going to interface")
        return "interface"

    logger.debug(
        "branch_from_router",
        extra={"destinations": destinations, "parallel": len(destinations) > 1}
    )

    return destinations


# =============================================================================
# Graph Builder
# =============================================================================

def get_graph():
    """Build and compile the multi-agent StateGraph.

    Returns:
        Compiled StateGraph ready for execution.

    Graph Structure:
        START → interface_analyze → [branch]
                                      ├── END (no fact questions)
                                      └── create_router_request → router → [branch]
                                                                             ├── expert ─┐
                                                                             ├── scout ──┼→ create_router_request
                                                                             └── interface_fact_results → END
    """
    graph = StateGraph(state_schema=GraphState, context_schema=GraphContext)

    # Add nodes
    graph.add_node('interface_analyze', analyze_paragraph)
    graph.add_node('interface_fact_results', process_fact_results)
    graph.add_node('create_router_request', create_router_request)
    graph.add_node('router', ask_router)
    graph.add_node('expert', ask_expert)
    graph.add_node('scout', ask_scout)

    # Define edges
    # Entry: Interface analyzes paragraph
    graph.add_edge(START, 'interface_analyze')

    # After analysis: end if no fact questions, else go to router
    graph.add_conditional_edges(
        'interface_analyze',
        branch_from_interface,
        {
            "end": END,
            "router": 'create_router_request'
        }
    )

    # Router flow
    graph.add_edge('create_router_request', 'router')
    graph.add_conditional_edges(
        'router',
        branch_from_router,
        {
            "expert": 'expert',
            "scout": 'scout',
            "interface": 'interface_fact_results'
        }
    )

    # Expert/Scout loop back to router
    graph.add_edge('expert', 'create_router_request')
    graph.add_edge('scout', 'create_router_request')

    # Fact results ends the graph
    graph.add_edge('interface_fact_results', END)

    logger.info("Graph compiled successfully")

    return graph.compile()
