from dataclasses import dataclass, field


@dataclass
class TemplateSection:
    """
    Describes one structural section of the Affidavit in Reply.
    """

    order: int
    name: str
    required: bool = True
    formatting: str = ""
    notes: str = ""


@dataclass
class ReplyMove:
    """
    Describes the purpose and expected behaviour of a numbered
    paragraph or prayer component.
    """

    name: str
    purpose: str
    expected_position: str


@dataclass
class TemplateSpecification:
    """
    Structured representation of the Affidavit in Reply template.

    This object is the contract between template understanding
    and the downstream content-mapping/document-generation stages.
    """

    document_type: str

    sections: list[TemplateSection] = field(default_factory=list)

    entities: list[str] = field(default_factory=list)

    reply_moves: list[ReplyMove] = field(default_factory=list)

    fixed_phrases: dict[str, list[str]] = field(default_factory=dict)

    formatting_rules: dict[str, str] = field(default_factory=dict)

    consistency_rules: list[str] = field(default_factory=list)

    unsupported_elements: list[str] = field(default_factory=list)