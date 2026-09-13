import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from src.api.service import (
    OUTPUT_DIR,
    run_affidavit_pipeline,
)


app = FastAPI(
    title="Legal Document Generation & Evaluation Agent",
    description=(
        "API for generating and evaluating an Affidavit in Reply "
        "from the supplied case information and reference format."
    ),
    version="1.0.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "legal-document-agent",
    }


@app.post("/generate")
def generate_affidavit() -> dict:
    """
    Run the complete existing document-generation and evaluation
    pipeline and return the evaluation result plus API artifact
    endpoints.
    """

    try:
        result = run_affidavit_pipeline()

        return {
            "status": result["status"],
            "revision_count": result["revision_count"],
            "evaluation_history_count": (
                result["evaluation_history_count"]
            ),
            "report": result["report"],
            "artifacts": {
                "affidavit": "/download/affidavit",
                "evaluation_report": "/report",
            },
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Document generation failed: {exc}",
        ) from exc


@app.get("/report")
def get_evaluation_report() -> dict:
    """
    Return the latest evaluation report.
    """

    report_path = (
        OUTPUT_DIR / "evaluation_report.json"
    )

    if not report_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "Evaluation report not found. "
                "Run /generate first."
            ),
        )

    try:
        return json.loads(
            report_path.read_text(
                encoding="utf-8"
            )
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Unable to read evaluation report: {exc}"
            ),
        ) from exc


@app.get("/download/affidavit")
def download_affidavit() -> FileResponse:
    """
    Download the latest generated Affidavit in Reply DOCX.
    """

    affidavit_path = (
        OUTPUT_DIR / "affidavit_in_reply.docx"
    )

    if not affidavit_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "Affidavit not found. "
                "Run /generate first."
            ),
        )

    return FileResponse(
        path=affidavit_path,
        media_type=(
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document"
        ),
        filename="affidavit_in_reply.docx",
    )