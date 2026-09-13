from src.evaluation.report import build_evaluation_report


EXPECTED_DIMENSIONS = {
    "Entity Accuracy": 100.0,
    "Completeness": 100.0,
    "Structure": 100.0,
    "Consistency": 100.0,
    "Template Fidelity": 100.0,
    "Hallucination Check": 100.0,
}


def _build_realistic_success_state():
    """
    Representative state produced by the actual Phase 4-6 workflow.
    """

    return {
        "case_data": {
            "document_type": "Affidavit in Reply",
            "case_number": "1847",
            "year": "2026",
        },

        "validation_results": {
            "passed": True,
            "score": 100.0,
            "dimension_scores": EXPECTED_DIMENSIONS.copy(),
            "errors": [],
            "warnings": [],
            "error_count": 0,
        },

        "evaluation_results": {
            "dimension_scores": EXPECTED_DIMENSIONS.copy(),
            "overall_score": 100.0,
            "issues": [],
            "deterministic_issues": [],
            "semantic_issues": [],
            "semantic_summary": (
                "The generated draft does not fully preserve the "
                "specific blanket-denial position as stated in the "
                "source content."
            ),
            "summary": (
                "Hybrid evaluation completed with 0 deterministic "
                "issues and 0 semantic issues."
            ),
            "weights": {
                "Entity Accuracy": 0.20,
                "Completeness": 0.20,
                "Structure": 0.15,
                "Consistency": 0.15,
                "Template Fidelity": 0.15,
                "Hallucination Check": 0.15,
            },
            "model": "qwen2.5:7b",
        },

        "evaluation_history": [],
        "revision_count": 0,
        "status": "evaluation_completed",
    }


def test_build_evaluation_report_from_realistic_success_state():
    state = _build_realistic_success_state()

    report = build_evaluation_report(state)

    # --------------------------------------------------------------
    # Basic report information
    # --------------------------------------------------------------

    assert report["report_title"] == (
        "Affidavit in Reply - Evaluation Report"
    )

    assert report["document"]["document_type"] == (
        "Affidavit in Reply"
    )

    assert report["document"]["case_number"] == "1847"
    assert report["document"]["year"] == "2026"

    # --------------------------------------------------------------
    # Final status and scores
    # --------------------------------------------------------------

    assert report["status"] == "PASS"

    assert report["overall_score"] == 100.0

    assert report["dimension_scores"] == EXPECTED_DIMENSIONS

    # --------------------------------------------------------------
    # Issues
    # --------------------------------------------------------------

    assert report["issues"] == []

    # --------------------------------------------------------------
    # Deterministic validation summary
    # --------------------------------------------------------------

    deterministic = report["validation_summary"]["deterministic"]

    assert deterministic["passed"] is True
    assert deterministic["score"] == 100.0
    assert deterministic["error_count"] == 0
    assert deterministic["errors"] == []

    # --------------------------------------------------------------
    # Semantic evaluation summary
    #
    # Important:
    # The semantic summary must be preserved even when the evaluator
    # reports zero semantic issues.
    # --------------------------------------------------------------

    semantic = report["validation_summary"]["semantic"]

    assert semantic["passed"] is True
    assert semantic["issue_count"] == 0

    assert semantic["summary"] == (
        "The generated draft does not fully preserve the "
        "specific blanket-denial position as stated in the "
        "source content."
    )

    # --------------------------------------------------------------
    # Scoring methodology
    # --------------------------------------------------------------

    assert report["scoring"]["weights"] == {
        "Entity Accuracy": 0.20,
        "Completeness": 0.20,
        "Structure": 0.15,
        "Consistency": 0.15,
        "Template Fidelity": 0.15,
        "Hallucination Check": 0.15,
    }

    assert "weighted average" in report["scoring"]["method"]

    # --------------------------------------------------------------
    # Revision information
    # --------------------------------------------------------------

    assert report["revision"]["revision_count"] == 0
    assert report["revision"]["evaluation_history_count"] == 0

    # --------------------------------------------------------------
    # Evaluation model
    # --------------------------------------------------------------

    assert report["model"] == "qwen2.5:7b"


def test_report_status_is_needs_revision_when_evaluation_has_issues():
    state = _build_realistic_success_state()

    state["evaluation_results"]["issues"] = [
        {
            "dimension": "Completeness",
            "severity": "HIGH",
            "issue": "Required content is missing.",
            "source_reference": "CaseData",
        }
    ]

    state["evaluation_results"]["deterministic_issues"] = [
        {
            "dimension": "Completeness",
            "severity": "HIGH",
            "issue": "Required content is missing.",
            "source_reference": "CaseData",
        }
    ]

    state["evaluation_results"]["dimension_scores"][
        "Completeness"
    ] = 85.0

    state["evaluation_results"]["overall_score"] = 97.0

    report = build_evaluation_report(state)

    assert report["status"] == "NEEDS REVISION"
    assert report["overall_score"] == 97.0
    assert len(report["issues"]) == 1

    assert report["issues"][0]["origin"] == "deterministic"


def test_report_status_is_fail_when_validation_fails():
    state = _build_realistic_success_state()

    state["validation_results"] = {
        "passed": False,
        "score": 80.0,
        "dimension_scores": EXPECTED_DIMENSIONS.copy(),
        "errors": [
            {
                "dimension": "Entity Accuracy",
                "severity": "HIGH",
                "issue": "Incorrect respondent.",
                "source": "CaseData",
            }
        ],
        "warnings": [],
        "error_count": 1,
    }

    state["evaluation_results"]["overall_score"] = 80.0

    report = build_evaluation_report(state)

    assert report["status"] == "FAIL"

    assert (
        report["validation_summary"]["deterministic"]["passed"]
        is False
    )

    assert (
        report["validation_summary"]["deterministic"]["error_count"]
        == 1
    )


def test_report_status_is_fail_when_revision_limit_is_reached():
    state = _build_realistic_success_state()

    state["status"] = "revision_limit_reached"
    state["revision_count"] = 2

    state["evaluation_results"]["issues"] = [
        {
            "dimension": "Completeness",
            "severity": "HIGH",
            "issue": "Required content is still missing.",
            "source_reference": "CaseData",
        }
    ]

    report = build_evaluation_report(state)

    assert report["status"] == "FAIL"
    assert report["revision"]["revision_count"] == 2