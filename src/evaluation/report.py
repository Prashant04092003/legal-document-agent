import json
from pathlib import Path
from typing import Any


DIMENSIONS = (
    "Entity Accuracy",
    "Completeness",
    "Structure",
    "Consistency",
    "Template Fidelity",
    "Hallucination Check",
)


def _case_value(case_data: Any, *names: str) -> Any:
    """
    Safely retrieve a value from CaseData regardless of whether
    the object exposes attributes or dictionary-style fields.
    """
    for name in names:
        if isinstance(case_data, dict):
            value = case_data.get(name)
        else:
            value = getattr(case_data, name, None)

        if value not in (None, ""):
            return value

    return None


def _issue_origin(
    issue: dict[str, Any],
    deterministic_issues: list[dict[str, Any]],
    semantic_issues: list[dict[str, Any]],
) -> str:
    """
    Identify whether an issue came from deterministic checks,
    semantic evaluation, or both.
    """
    in_deterministic = issue in deterministic_issues
    in_semantic = issue in semantic_issues

    if in_deterministic and in_semantic:
        return "deterministic+semantic"

    if in_deterministic:
        return "deterministic"

    if in_semantic:
        return "semantic"

    return "hybrid"


def _determine_status(
    validation_results: dict[str, Any],
    evaluation_results: dict[str, Any],
    workflow_status: str | None,
) -> str:
    """
    Determine the final report status from the final workflow state.
    """
    if validation_results.get("passed") is False:
        return "FAIL"

    if workflow_status == "revision_limit_reached":
        return "FAIL"

    if evaluation_results.get("issues"):
        return "NEEDS REVISION"

    return "PASS"


def build_evaluation_report(state: dict[str, Any]) -> dict[str, Any]:
    """
    Build the final Evaluation Report from the existing agent state.

    This function does not perform validation or evaluation itself.
    It only converts already-produced results into the assignment's
    report format.
    """
    case_data = state.get("case_data")
    validation_results = state.get("validation_results") or {}
    evaluation_results = state.get("evaluation_results") or {}

    deterministic_issues = (
        evaluation_results.get("deterministic_issues") or []
    )
    semantic_issues = (
        evaluation_results.get("semantic_issues") or []
    )
    issues = evaluation_results.get("issues") or []

    dimension_scores = evaluation_results.get("dimension_scores") or {}

    report = {
        "report_title": "Affidavit in Reply - Evaluation Report",

        "document": {
            "document_type": (
                _case_value(case_data, "document_type")
                or "Affidavit in Reply"
            ),
            "case_number": _case_value(case_data, "case_number"),
            "year": _case_value(case_data, "year"),
        },

        "status": _determine_status(
            validation_results,
            evaluation_results,
            state.get("status"),
        ),

        "overall_score": evaluation_results.get("overall_score"),

        "dimension_scores": {
            dimension: dimension_scores.get(dimension)
            for dimension in DIMENSIONS
        },

        "issues": [
            {
                **issue,
                "origin": _issue_origin(
                    issue,
                    deterministic_issues,
                    semantic_issues,
                ),
            }
            for issue in issues
        ],

        "validation_summary": {
            "deterministic": {
                "passed": validation_results.get("passed"),
                "score": validation_results.get("score"),
                "error_count": validation_results.get(
                    "error_count",
                    0,
                ),
                "errors": validation_results.get(
                    "errors",
                    [],
                ),
            },

            "semantic": {
                "passed": len(semantic_issues) == 0,
                "issue_count": len(semantic_issues),
                "summary": evaluation_results.get(
                    "semantic_summary"
                ),
            },
        },

        "scoring": {
            "method": (
                "Hybrid dimension scores are based on "
                "deduplicated evaluation issues; the overall "
                "score is the weighted average using the "
                "evaluator weights."
            ),
            "weights": evaluation_results.get("weights", {}),
        },

        "revision": {
            "revision_count": state.get(
                "revision_count",
                0,
            ),
            "evaluation_history_count": len(
                state.get("evaluation_history") or []
            ),
        },

        "model": evaluation_results.get("model"),
    }

    return report


def save_evaluation_report(
    report: dict[str, Any],
    output_path: str | Path = "outputs/evaluation_report.json",
) -> Path:
    """
    Save an evaluation report as a UTF-8 JSON file.

    This function only handles report persistence.
    It does not perform validation, evaluation, or scoring.
    """
    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False,
        )

    return output_path