from dataclasses import dataclass, field


@dataclass
class ReplyPoint:
    """
    One reply point supplied in the case-information document.

    The original order and wording are preserved so that downstream
    content mapping can trace each generated paragraph back to its
    source case point.
    """

    number: int
    title: str
    content: list[str] = field(default_factory=list)


@dataclass
class CaseData:
    """
    Structured representation of the case information supplied for
    generation of an Affidavit in Reply.

    This object is the contract between case-information extraction
    and the downstream content-mapping/document-generation stages.
    """

    document_type: str = ""

    court: str = ""
    jurisdiction: str = ""
    proceeding_type: str = ""
    case_number: str = ""
    year: str = ""

    petitioner: str = ""
    respondents: dict[str, str] = field(default_factory=dict)
    filed_on_behalf_of: str = ""

    deponent_name: str = ""
    designation: str = ""
    organisation: str = ""
    address: str = ""
    verification_verb: str = ""

    reply_points: list[ReplyPoint] = field(default_factory=list)

    prayer: str = ""

    exhibit: str = ""

    attestation_place: str = ""
    attestation_date: str = ""

    advocate_firm: str = ""
    advocate_for: str = ""
