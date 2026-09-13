TEMPLATE_SECTIONS = [
    "FORUM_HEADING",
    "JURISDICTION",
    "CASE_NUMBER",
    "CAUSE_TITLE",
    "AFFIDAVIT_TITLE",
    "DEPONENT_CLAUSE",
    "NUMBERED_PARAGRAPHS",
    "PRAYER",
    "JURAT",
    "VERIFICATION",
]


REPLY_MOVES = [
    (
        "IDENTITY_AND_PERUSAL",
        "Establishes the deponent's identity, familiarity with the case, "
        "perusal of the petition and competence to affirm the affidavit.",
        "First numbered paragraph",
    ),
    (
        "BLANKET_DENIAL",
        "Provides the general denial of allegations except those "
        "specifically admitted.",
        "Second numbered paragraph",
    ),
    (
        "PRELIMINARY_POSITION",
        "States the preliminary position of the respondent.",
        "Early numbered paragraphs after the blanket denial",
    ),
    (
        "SUBSTANTIVE_ANSWER",
        "Provides the substantive response to the relevant allegation "
        "or averment.",
        "After the preliminary position",
    ),
    (
        "CLOSING",
        "Concludes that the proceeding deserves dismissal with costs.",
        "Final numbered paragraph",
    ),
    (
        "PRAYER_TO_DISMISS",
        "Requests dismissal of the proceeding with costs and the "
        "specified reliefs.",
        "Prayer section after the numbered paragraphs",
    ),
]