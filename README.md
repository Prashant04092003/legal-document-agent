# Legal Document Generation & Evaluation Agent

An AI-powered workflow for generating, validating, evaluating, and exporting an **Affidavit in Reply** from supplied case information and reference documents.

Developed as a proof-of-concept for the Brainwonders AI Internship Assignment.

---

## Overview

The system takes the supplied case-information document and reference affidavit materials, understands the expected document structure, extracts relevant case entities, maps supplied reply points into that structure, and uses an LLM to generate an Affidavit in Reply.

The generated document is then:

1. Validated using deterministic Python checks.
2. Evaluated across six required dimensions.
3. Automatically revised when issues are detected, subject to a maximum of two revisions.
4. Rendered as a DOCX document.
5. Accompanied by a structured JSON evaluation report.

A Streamlit frontend provides the user interface, while a thin FastAPI layer exposes the existing workflow through HTTP.

## Architecture

```text
Reference Documents + Case Information
                |
                v
       Template Understanding
                +
         Entity Extraction
                |
                v
     Structured Case Representation
                |
                v
          Content Mapping
                |
                v
         Drafting Agent
                |
                v
      Deterministic Validation
                |
                v
        Semantic Evaluation
                |
          +-----+-----+
          |           |
        Clean       Issues
          |           |
          |           v
          |      Revision Agent
          |           |
          +------> Validation
                      |
                      v
                  Evaluation
                      |
                      v
              Final Affidavit
                /                          v             v
          DOCX Output   Evaluation Report
```

Application architecture:

```text
Streamlit UI
     |
     | HTTP
     v
FastAPI
     |
     v
Existing AI Workflow
     |
     +--> Generated DOCX
     +--> Evaluation Report
```

## Assignment Scope

The project focuses on one document type:

> **Affidavit in Reply**

It uses only the supplied case facts, supplied reply points, and supplied reference/template materials.

It does **not** perform independent legal research and is not intended to provide legal advice.

This is a proof-of-concept rather than a production legal-document system.

## Key Features

- PDF extraction using PyMuPDF.
- Reference/template document understanding.
- Structured case/entity extraction.
- Typed structured case representation.
- Content mapping from supplied reply points to affidavit sections.
- LangGraph-based drafting workflow.
- Local LLM inference using Ollama and Qwen 2.5 7B.
- Deterministic validation independent of the LLM.
- Semantic evaluation across six required dimensions.
- Automatic revision loop with a maximum of two revisions.
- Evaluation report generation.
- DOCX rendering using `python-docx`.
- FastAPI backend.
- Streamlit frontend.
- Original case-information PDF preview.
- Generated affidavit preview and DOCX download.
- Adversarial/robustness testing evidence.
- Automated tests for the main pipeline.

## Input Documents

```text
data/
├── reference/
│   ├── 01 Affidavit Format Explained.pdf
│   ├── 02 Affidavit in Reply Sample.docx.pdf
│   └── AI Intern Assignment.docx
└── input/
    └── 03_Case_Information.pdf
```

The format explanation and sample affidavit define the target structure and formatting. The case-information PDF supplies the facts used for generation.

## Workflow

### 1. Template Understanding

The system analyzes the supplied reference materials and identifies the expected affidavit structure, formatting conventions, paragraph sequence, deponent conventions, prayer, jurat, and verification rules.

The major sections are:

1. Forum heading
2. Jurisdiction
3. Case number
4. Cause title
5. Affidavit title
6. Deponent clause
7. Body paragraphs
8. Prayer
9. Jurat
10. Verification

### 2. Entity Extraction

Case information is converted into a structured representation containing fields such as:

```text
document_type
court
jurisdiction
proceeding_type
case_number
year
petitioner
respondents
filed_on_behalf_of
deponent_name
designation
organisation
address
verification_verb
reply_points
prayer
exhibit
attestation_place
attestation_date
advocate_firm
advocate_for
```

### 3. Content Mapping

The supplied reply points are mapped to the expected affidavit paragraphs.

For the supplied case:

```text
Point 1 -> Paragraph 1
Point 2 -> Paragraph 2
Point 3 -> Paragraph 3
Point 4 -> Paragraph 4
Point 5 -> Paragraph 5
Point 6 -> Paragraph 6
Closing -> Paragraph 7
Prayer -> Separate section
```

### 4. AI Drafting

The LangGraph drafting workflow uses Qwen 2.5 7B through Ollama.

The prompts constrain the model to the supplied facts and reply points and discourage unsupported factual additions.

### 5. Deterministic Validation

Independent Python checks validate structural and consistency requirements without relying solely on the LLM.

### 6. Semantic Evaluation

The generated affidavit is evaluated on:

| Dimension | Weight |
|---|---:|
| Entity Accuracy | 20% |
| Completeness | 20% |
| Structure | 15% |
| Consistency | 15% |
| Template Fidelity | 15% |
| Hallucination Check | 15% |

The overall score is calculated from these weighted dimensions.

### 7. Revision

If issues are detected, the revision agent receives the draft and evaluation information and attempts to correct it.

```text
Maximum revisions = 2
```

### 8. Output

The final document is rendered to DOCX and a structured evaluation report is saved as JSON.

## LangGraph Workflow

```text
START
  |
  v
Drafting Agent
  |
  v
Deterministic Validator
  |
  v
Evaluation Agent
  |
  v
Conditional Router
  |
  +---- Clean ------> END
  |
  +---- Issues -----> Revision Agent
                          |
                          v
                       Validator
                          |
                          v
                       Evaluator
                          |
                          v
                       Router
```

## Validation and Evaluation

The project deliberately combines two types of checking:

**Deterministic validation**

Used for properties that can be checked programmatically, such as required sections, numbering, case information consistency, verification range, and other structural constraints.

**Semantic evaluation**

Used to assess the generated text across the six assignment dimensions.

This separation is important because an LLM should not be the only mechanism checking an LLM-generated document.

## Robustness / Adversarial Testing

The project includes deliberate mutations of generated outputs to measure validation/evaluation behavior.

### Deterministic adversarial audit

```text
19 mutations tested
17 caught
2 missed

Detection rate: 89.5%
```

### Semantic adversarial audit

```text
4 hallucination mutations tested
2 caught
2 missed

Detection rate: 50.0%
```

These are **stress-test results**, not substitutes for the production evaluation score.

The semantic evaluator is not perfect; adversarial testing demonstrated that some unsupported factual mutations can pass semantic evaluation. This limitation is intentionally documented.

## Outputs

```text
outputs/
├── affidavit_in_reply.docx
└── evaluation_report.json
```

### Affidavit

`affidavit_in_reply.docx` is the formal generated document artifact.

The renderer uses `python-docx` and applies:

- Times New Roman
- 12 pt body text
- legal-document margins
- centered/bold headings
- structured cause title
- numbered paragraphs
- prayer
- jurat
- verification
- advocate block

### Evaluation report

`evaluation_report.json` contains:

- overall score
- six dimension scores
- detected issues
- issue origin
- deterministic validation summary
- semantic evaluation summary
- scoring methodology
- scoring weights
- revision information
- model information

## Project Structure

```text
legal-document-agent/
├── src/
│   ├── agent/
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   ├── state.py
│   │   └── validator.py
│   ├── evaluation/
│   │   ├── evaluator.py
│   │   └── report.py
│   ├── extraction/
│   │   ├── case_schema.py
│   │   ├── entity_extractor.py
│   │   └── pdf_extractor.py
│   ├── generation/
│   │   └── affidavit_generator.py
│   ├── llm/
│   │   ├── ollama_client.py
│   │   └── output_cleaner.py
│   ├── mapping/
│   │   └── content_mapper.py
│   ├── schemas/
│   │   └── case_schema.py
│   ├── template/
│   │   ├── input_builder.py
│   │   ├── llm_extractors.py
│   │   ├── prompts.py
│   │   ├── reference_splitter.py
│   │   ├── response_parser.py
│   │   ├── schema.py
│   │   ├── structure.py
│   │   ├── template_analyzer.py
│   │   ├── template_knowledge.py
│   │   └── template_schema.json
│   ├── validation/
│   │   └── validator.py
│   ├── output/
│   │   └── docx_renderer.py
│   └── api/
│       ├── main.py
│       ├── schemas.py
│       └── service.py
├── data/
├── outputs/
├── tests/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

The active orchestration/generation implementation is under `src/agent/`. The files `src/orchestrator.py` and `src/generation/affidavit_generator.py` were intentionally not used as the primary orchestration/generation layer.

## Tech Stack

- Python
- LangGraph
- LangChain / LangChain Ollama
- Ollama
- Qwen 2.5 7B
- FastAPI
- Uvicorn
- Streamlit
- PyMuPDF
- python-docx
- Pydantic
- Pytest

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd legal-document-agent
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scriptsctivate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

For Streamlit's PDF viewer:

```bash
python3 -m pip install "streamlit[pdf]==1.63.0"
```

## Ollama Setup

Install Ollama if it is not already installed.

Pull the configured model:

```bash
ollama pull qwen2.5:7b
```

Verify:

```bash
ollama list
```

The current application expects Qwen 2.5 7B through a local Ollama instance.

## Running the Application

The application uses two local services.

### Terminal 1 — FastAPI

```bash
uvicorn src.api.main:app --reload
```

Expected API address:

```text
http://127.0.0.1:8000
```

### Terminal 2 — Streamlit

```bash
streamlit run app.py
```

The frontend is normally available at:

```text
http://localhost:8501
```

## Using the Application

1. Open the Streamlit application.
2. Review the supplied **Original Case Information** PDF.
3. Click **Generate Affidavit in Reply**.
4. Streamlit sends the request to FastAPI.
5. The backend runs extraction, template understanding, mapping, drafting, validation, and evaluation.
6. If required, the revision loop attempts to correct detected issues.
7. The final affidavit is rendered to DOCX.
8. The evaluation report is generated.
9. The generated affidavit appears in the application.
10. Review the evaluation and robustness evidence.
11. Download the final DOCX.

## API

The frontend uses a thin FastAPI service layer.

Main endpoints:

```text
GET  /health
POST /generate
GET  /download/affidavit
```

The API layer does not duplicate the document-generation business logic; it delegates to the existing backend workflow.

## Testing

The test suite covers major pipeline components including:

- PDF extraction
- entity extraction
- content mapping
- deterministic validation
- semantic evaluation
- evaluation report generation/export
- DOCX rendering
- LangGraph workflow
- revision loop
- end-to-end workflow
- adversarial validation

Run all tests:

```bash
pytest -v
```

## Design Decisions

### Structured intermediate representation

A structured case representation separates extraction from generation. This makes the pipeline easier to test, inspect, and maintain.

### Deterministic validation

Programmatic checks provide an independent validation layer rather than relying entirely on the same LLM that generated the document.

### Revision loop

The evaluation stage can feed detected issues back to the drafting process, demonstrating an iterative generation workflow.

### Thin API

FastAPI provides an HTTP boundary between the frontend and backend without duplicating business logic.

### Single document type

The implementation remains focused on the assignment's Affidavit in Reply requirement instead of introducing unnecessary multi-document complexity.

## Limitations

- The workflow is designed for one document type: Affidavit in Reply.
- It uses supplied case facts and reference materials rather than independent legal research.
- It is not a substitute for legal review or professional legal advice.
- The current model is served locally through Ollama.
- Semantic hallucination detection is imperfect, as demonstrated by adversarial testing.
- The Streamlit DOCX preview is a convenience representation; the downloadable DOCX is the formal generated artifact.
- Public deployment requires a remotely accessible model/API or a separate demonstration/cached-output mode because a hosted Streamlit application cannot directly access a developer's local Ollama instance.

## Security and Configuration

Do not commit `.env` or other secrets to source control.

The repository should use `.gitignore` for:

```text
.env
.venv/
__pycache__/
*.pyc
```

Use `.env.example` as the template for environment-specific configuration.

## Future Improvements

Potential future improvements include:

- stronger semantic hallucination detection
- more precise template-fidelity checks
- improved DOCX preview rendering
- remote LLM/API support
- configurable input/reference documents
- broader adversarial test coverage
- support for additional document types if the project scope is expanded

These improvements are outside the current assignment scope.

## Summary

The project demonstrates an end-to-end AI document workflow:

```text
Input Documents
      |
      v
Template Understanding
      |
      v
Entity Extraction
      |
      v
Structured Case Data
      |
      v
Content Mapping
      |
      v
AI Drafting
      |
      v
Deterministic Validation
      |
      v
Semantic Evaluation
      |
      v
Revision when required
      |
      v
Final Affidavit
      |
      +------------------+
      |                  |
      v                  v
   DOCX Output     Evaluation Report
      |
      v
Streamlit + FastAPI
```

The system demonstrates the requested proof of concept: understanding supplied documents, extracting structured information, generating an Affidavit in Reply, independently validating the result, evaluating it, revising it when necessary, and producing a downloadable document and evaluation report.
