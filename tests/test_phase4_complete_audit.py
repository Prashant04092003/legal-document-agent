from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from src.agent.graph import run_drafting_agent
from src.agent.validator import validation_node
from src.evaluation.evaluator import (
    evaluate_draft,
    _deterministic_entity_checks,
    _deterministic_completeness_checks,
    _deterministic_structure_checks,
    _deterministic_consistency_checks,
    _deterministic_hallucination_checks,
)
from src.extraction.entity_extractor import extract_case_data
from src.extraction.pdf_extractor import extract_pdf_text
from src.mapping.content_mapper import build_content_map
from src.template.template_analyzer import (
    analyze_reference_documents,
    build_template_specification,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

FORMAT_EXPLAINED = (
    PROJECT_ROOT
    / "data"
    / "reference"
    / "01 Affidavit Format Explained.pdf"
)

SAMPLE_AFFIDAVIT = (
    PROJECT_ROOT
    / "data"
    / "reference"
    / "02 Affidavit in Reply Sample.docx.pdf"
)

CASE_INFORMATION = (
    PROJECT_ROOT
    / "data"
    / "input"
    / "03_Case_Information.pdf"
)


# ============================================================================
# INPUT BUILDING
# ============================================================================


def _build_inputs():
    template_knowledge = analyze_reference_documents(
        str(FORMAT_EXPLAINED),
        str(SAMPLE_AFFIDAVIT),
    )

    template_specification = (
        build_template_specification(
            template_knowledge
        )
    )

    case_pages = extract_pdf_text(
        CASE_INFORMATION
    )

    case_data = extract_case_data(
        case_pages
    )

    content_map = build_content_map(
        case_data,
        template_specification,
    )

    return (
        case_data,
        template_specification,
        content_map,
    )


# ============================================================================
# REPORT HELPERS
# ============================================================================


def _print_header(title: str):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def _issue_text(issues):
    if not issues:
        return "NONE"

    return " | ".join(
        str(issue.get("issue", issue))
        for issue in issues
    )


def _run_validator(
    case_data,
    template_specification,
    content_map,
    draft,
):
    state = {
        "case_data": case_data,
        "template_specification": template_specification,
        "content_map": content_map,
        "generated_draft": draft,
    }

    result = validation_node(state)

    return result["validation_results"]


def _run_deterministic_evaluator(
    case_data,
    template_specification,
    content_map,
    draft,
):
    state = {
        "case_data": case_data,
        "template_specification": template_specification,
        "content_map": content_map,
        "generated_draft": draft,
    }

    issues = []

    issues.extend(
        _deterministic_entity_checks(state)
    )

    issues.extend(
        _deterministic_completeness_checks(state)
    )

    issues.extend(
        _deterministic_structure_checks(state)
    )

    issues.extend(
        _deterministic_consistency_checks(state)
    )

    issues.extend(
        _deterministic_hallucination_checks(state)
    )

    return issues


# ============================================================================
# BASELINE INSPECTION
# ============================================================================


def _print_draft_structure(draft):
    _print_header(
        "BASELINE GENERATED DRAFT STRUCTURE"
    )

    print("\nHEADER SECTIONS:")

    sections = draft.get(
        "sections",
        {},
    )

    for name, value in sections.items():
        print(f"\n[{name}]")
        print(value)

    print("\nNUMBERED PARAGRAPHS:")

    for paragraph in draft.get(
        "paragraphs",
        [],
    ):
        print(
            f"\nParagraph "
            f"{paragraph.get('paragraph_number')}: "
            f"{paragraph.get('title')}"
        )

        content = paragraph.get(
            "content",
            [],
        )

        if isinstance(
            content,
            list,
        ):
            for item in content:
                print(f"  {item}")
        else:
            print(f"  {content}")

    print("\nPRAYER:")
    print(
        draft.get(
            "prayer",
            "",
        )
    )

    print("\nJURAT:")
    print(
        draft.get(
            "jurat",
            "",
        )
    )

    print("\nVERIFICATION:")
    print(
        draft.get(
            "verification",
            "",
        )
    )

    print("\nEXHIBIT:")
    print(
        draft.get(
            "exhibit",
            "",
        )
    )

    print("\nADVOCATE:")
    print(
        draft.get(
            "advocate",
            "",
        )
    )


# ============================================================================
# EXPECTED TEMPLATE CONTRACT
# ============================================================================


def _check_baseline_contract(
    case_data,
    content_map,
    draft,
):
    _print_header(
        "BASELINE CONTRACT AUDIT"
    )

    sections = draft.get(
        "sections",
        {},
    )

    checks = []

    checks.append(
        (
            "Court",
            sections.get(
                "FORUM_HEADING",
                ""
            ),
            case_data.court,
        )
    )

    checks.append(
        (
            "Jurisdiction",
            sections.get(
                "JURISDICTION",
                ""
            ),
            case_data.jurisdiction,
        )
    )

    expected_case_number = (
        f"{case_data.proceeding_type} "
        f"No. {case_data.case_number} "
        f"of {case_data.year}"
    )

    checks.append(
        (
            "Case Number",
            sections.get(
                "CASE_NUMBER",
                ""
            ),
            expected_case_number,
        )
    )

    expected_title = (
        f"{case_data.document_type} "
        f"on behalf of "
        f"{case_data.filed_on_behalf_of}"
    )

    checks.append(
        (
            "Affidavit Title",
            sections.get(
                "AFFIDAVIT_TITLE",
                ""
            ),
            expected_title,
        )
    )

    expected_range = (
        f"paragraphs 1 to "
        f"{content_map.paragraph_count}"
    )

    checks.append(
        (
            "Verification Range",
            draft.get(
                "verification",
                ""
            ),
            expected_range,
        )
    )

    checks.append(
        (
            "Verification Wording",
            draft.get(
                "verification",
                ""
            ),
            "do hereby verify",
        )
    )

    expected_jurat_verb = (
        "solemnly affirmed"
        if case_data.verification_verb
        == "solemnly affirm"
        else "sworn"
    )

    checks.append(
        (
            "Jurat Verb",
            draft.get(
                "jurat",
                ""
            ),
            expected_jurat_verb,
        )
    )

    for name, actual, expected in checks:
        passed = (
            expected.lower()
            in str(actual).lower()
        )

        status = "PASS" if passed else "FAIL"

        print(
            f"[{status}] "
            f"{name}\n"
            f"  Expected: {expected}\n"
            f"  Actual:   {actual}"
        )


# ============================================================================
# DETERMINISTIC MUTATION SUITE
# ============================================================================


def _mutation_suite():
    """
    Each mutation returns:

        name
        description
        mutation function
        expected dimension

    These mutations deliberately damage ONE thing.
    """

    return [
        {
            "name": "WRONG_CASE_NUMBER",
            "description": "Change case number 1847 to 9999.",
            "expected_dimension": [
                "Entity Accuracy",
                "Hallucination Check",
            ],
            "mutate": lambda draft: (
                draft["sections"].update(
                    {
                        "CASE_NUMBER":
                            "WRIT PETITION No. 9999 of 2026"
                    }
                )
            ),
        },
        {
            "name": "WRONG_COURT",
            "description": "Change Bombay High Court to another court.",
            "expected_dimension": [
                "Entity Accuracy",
            ],
            "mutate": lambda draft: (
                draft["sections"].update(
                    {
                        "FORUM_HEADING":
                            "IN THE HIGH COURT OF JUDICATURE AT DELHI"
                    }
                )
            ),
        },
        {
            "name": "WRONG_JURISDICTION",
            "description": "Change Ordinary Original Civil Jurisdiction.",
            "expected_dimension": [
                "Entity Accuracy",
            ],
            "mutate": lambda draft: (
                draft["sections"].update(
                    {
                        "JURISDICTION":
                            "CIVIL APPELLATE JURISDICTION"
                    }
                )
            ),
        },
        {
            "name": "MISSING_PETITIONER",
            "description": "Remove petitioner from cause title.",
            "expected_dimension": [
                "Entity Accuracy",
            ],
            "mutate": lambda draft: (
                draft["sections"].update(
                    {
                        "CAUSE_TITLE":
                            "State of Maharashtra vs. Mumbai Metropolitan Region Development Authority"
                    }
                )
            ),
        },
        {
            "name": "MISSING_RESPONDENT",
            "description": "Remove Respondent No. 2 from cause title.",
            "expected_dimension": [
                "Entity Accuracy",
            ],
            "mutate": lambda draft: (
                draft["sections"].update(
                    {
                        "CAUSE_TITLE":
                            "Sunrise Housing Private Limited vs. State of Maharashtra"
                    }
                )
            ),
        },
        {
            "name": "WRONG_DEPONENT",
            "description": "Change deponent name.",
            "expected_dimension": [
                "Entity Accuracy",
            ],
            "mutate": lambda draft: (
                draft["sections"].update(
                    {
                        "DEPONENT_CLAUSE":
                            draft["sections"].get(
                                "DEPONENT_CLAUSE",
                                ""
                            ).replace(
                                "Arvind Rajan",
                                "Rahul Sharma",
                            )
                    }
                )
            ),
        },
        {
            "name": "WRONG_RESPONDENT_TITLE",
            "description": "Change Respondent No. 2 to Respondent No. 1.",
            "expected_dimension": [
                "Entity Accuracy",
                "Consistency",
            ],
            "mutate": lambda draft: (
                draft["sections"].update(
                    {
                        "AFFIDAVIT_TITLE":
                            draft["sections"].get(
                                "AFFIDAVIT_TITLE",
                                ""
                            ).replace(
                                "Respondent No. 2",
                                "Respondent No. 1",
                            )
                    }
                )
            ),
        },
        {
            "name": "MISSING_PARAGRAPH",
            "description": "Remove paragraph 4.",
            "expected_dimension": [
                "Completeness",
                "Structure",
            ],
            "mutate": lambda draft: (
                draft.__setitem__(
                    "paragraphs",
                    [
                        p
                        for p in draft.get(
                            "paragraphs",
                            [],
                        )
                        if p.get(
                            "paragraph_number"
                        ) != 4
                    ],
                )
            ),
        },
        {
            "name": "WRONG_PARAGRAPH_NUMBER",
            "description": "Change paragraph 4 number to 8.",
            "expected_dimension": [
                "Structure",
            ],
            "mutate": lambda draft: (
                [
                    p.__setitem__(
                        "paragraph_number",
                        8,
                    )
                    for p in draft.get(
                        "paragraphs",
                        []
                    )
                    if p.get(
                        "paragraph_number"
                    ) == 4
                ]
            ),
        },
        {
            "name": "EMPTY_PARAGRAPH",
            "description": "Remove paragraph 4 content.",
            "expected_dimension": [
                "Completeness",
                "Structure",
            ],
            "mutate": lambda draft: (
                [
                    p.__setitem__(
                        "content",
                        [],
                    )
                    for p in draft.get(
                        "paragraphs",
                        []
                    )
                    if p.get(
                        "paragraph_number"
                    ) == 4
                ]
            ),
        },
        {
            "name": "MISSING_PRAYER",
            "description": "Remove prayer.",
            "expected_dimension": [
                "Structure",
                "Completeness",
            ],
            "mutate": lambda draft: (
                draft.__setitem__(
                    "prayer",
                    "",
                )
            ),
        },
        {
            "name": "MISSING_JURAT",
            "description": "Remove jurat.",
            "expected_dimension": [
                "Structure",
                "Consistency",
            ],
            "mutate": lambda draft: (
                draft.__setitem__(
                    "jurat",
                    "",
                )
            ),
        },
        {
            "name": "WRONG_JURAT_DATE",
            "description": "Change jurat date.",
            "expected_dimension": [
                "Consistency",
            ],
            "mutate": lambda draft: (
                draft.__setitem__(
                    "jurat",
                    draft.get(
                        "jurat",
                        ""
                    ).replace(
                        "5 September 2026",
                        "6 September 2026",
                    ),
                )
            ),
        },
        {
            "name": "WRONG_JURAT_PLACE",
            "description": "Change jurat place.",
            "expected_dimension": [
                "Consistency",
            ],
            "mutate": lambda draft: (
                draft.__setitem__(
                    "jurat",
                    draft.get(
                        "jurat",
                        ""
                    ).replace(
                        "Mumbai",
                        "Pune",
                    ),
                )
            ),
        },
        {
            "name": "WRONG_JURAT_VERB",
            "description": "Change solemnly affirmed to sworn.",
            "expected_dimension": [
                "Consistency",
            ],
            "mutate": lambda draft: (
                draft.__setitem__(
                    "jurat",
                    draft.get(
                        "jurat",
                        ""
                    ).replace(
                        "solemnly affirmed",
                        "sworn",
                    ),
                )
            ),
        },
        {
            "name": "WRONG_VERIFICATION_RANGE",
            "description": "Change verification range 1 to 7 into 1 to 5.",
            "expected_dimension": [
                "Consistency",
            ],
            "mutate": lambda draft: (
                draft.__setitem__(
                    "verification",
                    draft.get(
                        "verification",
                        ""
                    ).replace(
                        "paragraphs 1 to 7",
                        "paragraphs 1 to 5",
                    ),
                )
            ),
        },
        {
            "name": "WRONG_VERIFICATION_WORDING",
            "description": "Remove do hereby verify.",
            "expected_dimension": [
                "Consistency",
            ],
            "mutate": lambda draft: (
                draft.__setitem__(
                    "verification",
                    draft.get(
                        "verification",
                        ""
                    ).replace(
                        "do hereby verify",
                        "hereby state",
                    ),
                )
            ),
        },
        {
            "name": "MISSING_EXHIBIT",
            "description": "Remove Exhibit A.",
            "expected_dimension": [
                "Completeness",
            ],
            "mutate": lambda draft: (
                draft.__setitem__(
                    "exhibit",
                    "",
                )
            ),
        },
        {
            "name": "WRONG_PRAYER",
            "description": "Change dismissal prayer.",
            "expected_dimension": [
                "Completeness",
            ],
            "mutate": lambda draft: (
                draft.__setitem__(
                    "prayer",
                    "The petition may be allowed.",
                )
            ),
        },
    ]


# ============================================================================
# MAIN AUDIT
# ============================================================================


def test_complete_phase4_audit():

    (
        case_data,
        template_specification,
        content_map,
    ) = _build_inputs()

    _print_header(
        "PHASE 4 COMPLETE SYSTEM AUDIT"
    )

    print(
        "\nThis test intentionally runs a broad diagnostic suite."
    )

    # ------------------------------------------------------------------------
    # Run real production workflow once
    # ------------------------------------------------------------------------

    result = run_drafting_agent(
        case_data,
        template_specification,
        content_map,
    )

    draft = result["generated_draft"]

    # ------------------------------------------------------------------------
    # Baseline
    # ------------------------------------------------------------------------

    _print_draft_structure(
        draft
    )

    validation = result[
        "validation_results"
    ]

    evaluation = result[
        "evaluation_results"
    ]

    _print_header(
        "BASELINE VALIDATION"
    )

    print(
        "Passed:",
        validation["passed"],
    )

    print(
        "Score:",
        validation["score"],
    )

    print(
        "Errors:",
        validation["error_count"],
    )

    if validation["errors"]:
        for error in validation[
            "errors"
        ]:
            print(
                " -",
                error,
            )

    _print_header(
        "BASELINE HYBRID EVALUATION"
    )

    print(
        "Overall:",
        evaluation["overall_score"],
    )

    for dimension, score in evaluation[
        "dimension_scores"
    ].items():
        print(
            f"{dimension}: {score}"
        )

    print(
        "\nDeterministic issues:",
        len(
            evaluation[
                "deterministic_issues"
            ]
        ),
    )

    print(
        "Semantic issues:",
        len(
            evaluation[
                "semantic_issues"
            ]
        ),
    )

    for issue in evaluation[
        "deterministic_issues"
    ]:
        print(
            " -",
            issue,
        )

    for issue in evaluation[
        "semantic_issues"
    ]:
        print(
            " -",
            issue,
        )

    # ------------------------------------------------------------------------
    # Baseline contract
    # ------------------------------------------------------------------------

    _check_baseline_contract(
        case_data,
        content_map,
        draft,
    )

    # ------------------------------------------------------------------------
    # Deterministic mutation audit
    # ------------------------------------------------------------------------

    _print_header(
        "DETERMINISTIC MUTATION AUDIT"
    )

    mutation_results = []

    for mutation in _mutation_suite():

        corrupted = deepcopy(
            draft
        )

        mutation["mutate"](
            corrupted
        )

        validator_result = _run_validator(
            case_data,
            template_specification,
            content_map,
            corrupted,
        )

        evaluator_issues = (
            _run_deterministic_evaluator(
                case_data,
                template_specification,
                content_map,
                corrupted,
            )
        )

        evaluator_dimensions = sorted(
            {
                issue.get(
                    "dimension"
                )
                for issue in evaluator_issues
            }
        )

        validator_caught = (
            not validator_result["passed"]
        )

        evaluator_caught = (
            len(
                evaluator_issues
            )
            > 0
        )

        expected = mutation[
            "expected_dimension"
        ]

        expected_caught = any(
            dimension in evaluator_dimensions
            or dimension in validator_result.get(
                "dimension_scores",
                {}
            )
            for dimension in expected
        )

        status = (
            "PASS"
            if validator_caught
            or evaluator_caught
            else "MISS"
        )

        mutation_results.append(
            {
                "name": mutation["name"],
                "expected": expected,
                "validator_caught": validator_caught,
                "evaluator_caught": evaluator_caught,
                "dimensions": evaluator_dimensions,
                "status": status,
            }
        )

        print(
            f"\n[{status}] "
            f"{mutation['name']}"
        )

        print(
            "  Expected:",
            ", ".join(expected),
        )

        print(
            "  Validator:",
            "CAUGHT"
            if validator_caught
            else "MISSED",
        )

        print(
            "  Evaluator:",
            "CAUGHT"
            if evaluator_caught
            else "MISSED",
        )

        if evaluator_dimensions:
            print(
                "  Dimensions:",
                ", ".join(
                    evaluator_dimensions
                ),
            )

        if evaluator_issues:
            for issue in evaluator_issues:
                print(
                    "   -",
                    issue["issue"],
                )

    # ------------------------------------------------------------------------
    # Semantic adversarial audit
    # ------------------------------------------------------------------------

    _print_header(
        "SEMANTIC ADVERSARIAL AUDIT"
    )

    semantic_mutations = []

    # 1. Unsupported site inspection
    corrupted = deepcopy(
        draft
    )

    corrupted[
        "paragraphs"
    ][0][
        "content"
    ] += (
        " I personally inspected the "
        "redevelopment site on 1 August 2026."
    )

    semantic_mutations.append(
        (
            "INVENTED_SITE_INSPECTION",
            corrupted,
        )
    )

    # 2. Generic replacement of substantive answer
    corrupted = deepcopy(
        draft
    )

    if len(
        corrupted.get(
            "paragraphs",
            []
        )
    ) >= 4:

        corrupted[
            "paragraphs"
        ][3][
            "content"
        ] = (
            "With reference to the Petition, "
            "I deny the allegations."
        )

    semantic_mutations.append(
        (
            "GENERIC_SUBSTANTIVE_ANSWER",
            corrupted,
        )
    )

    # 3. Invented approval
    corrupted = deepcopy(
        draft
    )

    if len(
        corrupted.get(
            "paragraphs",
            []
        )
    ) >= 5:

        corrupted[
            "paragraphs"
        ][4][
            "content"
        ] = (
            "The communication dated 15 July 2026 "
            "was issued after approval by the "
            "competent authority and following an "
            "internal investigation."
        )

    semantic_mutations.append(
        (
            "INVENTED_APPROVAL_AND_INVESTIGATION",
            corrupted,
        )
    )

    for name, corrupted in semantic_mutations:

        state = {
            "case_data": case_data,
            "template_specification":
                template_specification,
            "content_map":
                content_map,
            "generated_draft":
                corrupted,
        }

        semantic_evaluation = evaluate_draft(
            state
        )

        semantic_issues = (
            semantic_evaluation[
                "semantic_issues"
            ]
        )

        print(
            f"\n[{name}]"
        )

        print(
            "Overall:",
            semantic_evaluation[
                "overall_score"
            ],
        )

        print(
            "Semantic issues:",
            len(
                semantic_issues
            ),
        )

        for issue in semantic_issues:
            print(
                " -",
                issue,
            )

        if not semantic_issues:
            print(
                "  !!! SEMANTIC DETECTOR MISSED "
                "THIS MUTATION !!!"
            )

    # ------------------------------------------------------------------------
    # Final audit summary
    # ------------------------------------------------------------------------

    _print_header(
        "FINAL PHASE 4 AUDIT SUMMARY"
    )

    total_mutations = len(
        mutation_results
    )

    caught_mutations = sum(
        1
        for result in mutation_results
        if result["status"] == "PASS"
    )

    missed_mutations = [
        result
        for result in mutation_results
        if result["status"] == "MISS"
    ]

    print(
        f"Deterministic mutations tested: "
        f"{total_mutations}"
    )

    print(
        f"Caught by validator/evaluator: "
        f"{caught_mutations}"
    )

    print(
        f"Missed: "
        f"{len(missed_mutations)}"
    )

    if missed_mutations:

        print(
            "\n!!! MISSED MUTATIONS !!!"
        )

        for result in missed_mutations:
            print(
                f"\n{result['name']}"
            )

            print(
                " Expected:",
                result["expected"],
            )

            print(
                " Validator:",
                result["validator_caught"],
            )

            print(
                " Evaluator:",
                result["evaluator_caught"],
            )

    print(
        "\nBaseline validation:",
        validation["score"],
    )

    print(
        "Baseline hybrid evaluation:",
        evaluation["overall_score"],
    )

    print(
        "\nIMPORTANT:"
    )

    print(
        "This diagnostic test is intentionally "
        "informational. It reports misses instead "
        "of stopping at the first failure."
    )

    # The audit itself should complete.
    assert total_mutations > 0