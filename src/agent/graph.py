from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.agent.nodes import (
    drafting_agent_node,
    evaluation_agent_node,
    revision_agent_node,
)
from src.agent.state import AgentState
from src.agent.validator import validation_node


MAX_REVISIONS = 2


def should_revise(state: AgentState) -> str:
    """
    Decide whether the workflow should terminate or send the draft
    to the revision agent.

    Termination conditions:
    1. Evaluation is clean.
    2. Maximum number of revisions has been reached.
    """

    evaluation_results = state.get("evaluation_results", {})
    revision_count = state.get("revision_count", 0)

    issues = evaluation_results.get("issues", [])

    if not issues:
        return "end"

    if revision_count >= MAX_REVISIONS:
        return "revision_limit_reached"

    return "revise"


def build_agent_graph():
    """
    Build the Phase 4D agent workflow.

    Workflow:

        START
          ↓
        Drafting Agent
          ↓
        Deterministic Validator
          ↓
        Evaluation Agent
          ↓
        ┌─────────────────────────────┐
        │                             │
      clean                        issues
        │                             │
        ↓                             ↓
       END                     Revision Agent
                                      ↓
                               Deterministic Validator
                                      ↓
                               Evaluation Agent
                                      ↓
                               ┌──────┴──────┐
                               │             │
                             clean        issues
                               │             │
                               ↓             ↓
                              END       Revision Agent
                                            ...
                                      max 2 revisions
    """

    graph = StateGraph(AgentState)

    graph.add_node(
        "drafting_agent",
        drafting_agent_node,
    )

    graph.add_node(
        "deterministic_validator",
        validation_node,
    )

    graph.add_node(
        "evaluation_agent",
        evaluation_agent_node,
    )

    graph.add_node(
        "revision_agent",
        revision_agent_node,
    )

    graph.add_edge(
        START,
        "drafting_agent",
    )

    graph.add_edge(
        "drafting_agent",
        "deterministic_validator",
    )

    graph.add_edge(
        "deterministic_validator",
        "evaluation_agent",
    )

    graph.add_conditional_edges(
        "evaluation_agent",
        should_revise,
        {
            "end": END,
            "revise": "revision_agent",
            "revision_limit_reached": END,
        },
    )

    graph.add_edge(
        "revision_agent",
        "deterministic_validator",
    )

    return graph.compile()


def run_drafting_agent(
    case_data,
    template_specification,
    content_map,
):
    """
    Execute the complete Phase 4D workflow.
    """

    graph = build_agent_graph()

    initial_state: AgentState = {
        "case_data": case_data,
        "template_specification": template_specification,
        "content_map": content_map,
        "revision_count": 0,
        "evaluation_history": [],
    }

    result = graph.invoke(initial_state)

    if result.get("revision_count", 0) >= MAX_REVISIONS:
        evaluation_results = result.get("evaluation_results", {})
        if evaluation_results.get("issues"):
            result["status"] = "revision_limit_reached"

    return result