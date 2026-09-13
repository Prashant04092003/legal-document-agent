import json

from src.evaluation.report import save_evaluation_report


def test_save_evaluation_report(tmp_path):
    report = {
        "report_title": "Affidavit in Reply - Evaluation Report",
        "status": "PASS",
        "overall_score": 100.0,
        "dimension_scores": {
            "Entity Accuracy": 100.0,
            "Completeness": 100.0,
            "Structure": 100.0,
            "Consistency": 100.0,
            "Template Fidelity": 100.0,
            "Hallucination Check": 100.0,
        },
        "issues": [],
    }

    output_path = tmp_path / "evaluation_report.json"

    saved_path = save_evaluation_report(report, output_path)

    assert saved_path == output_path
    assert output_path.exists()

    with output_path.open("r", encoding="utf-8") as file:
        saved_report = json.load(file)

    assert saved_report == report