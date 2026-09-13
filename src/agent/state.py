from __future__ import annotations

from typing import TypedDict

from src.extraction.case_schema import CaseData
from src.mapping.content_mapper import ContentMap
from src.template.schema import TemplateSpecification


class AgentState(TypedDict, total=False):
    """
    Working state for one Affidavit in Reply generation run.

    LangGraph passes this state between nodes.

    The state is scoped to a single document-generation run.
    It is not long-term or cross-case memory.
    """

    # ------------------------------------------------------------------
    # Source / planning state
    # ------------------------------------------------------------------

    case_data: CaseData
    template_specification: TemplateSpecification
    content_map: ContentMap

    # ------------------------------------------------------------------
    # Generated artifacts
    # ------------------------------------------------------------------

    generated_draft: dict

    # ------------------------------------------------------------------
    # Future evaluation pipeline
    # ------------------------------------------------------------------

    validation_results: dict
    evaluation_results: dict
    evaluation_history: list[dict]

    # ------------------------------------------------------------------
    # Agent control state
    # ------------------------------------------------------------------

    revision_count: int
    status: str
    error: str