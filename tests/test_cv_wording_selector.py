"""Tests for Phase 5.1 safe wording selection."""

from src.cv_content_mapper import CVWordingCandidate
from src.cv_wording_selector import select_cv_wording
from tests.phase5_helpers import make_match


def _candidate(
    text: str,
    *,
    approved: bool = True,
    review_required: bool = False,
    relevance: float = 0.8,
) -> CVWordingCandidate:
    return CVWordingCandidate(
        source_cv_key="data_reference",
        source_file="data.docx",
        text=text,
        source_type="professional_experience",
        matched_evidence_ids=["project_1"],
        relevance_score=relevance,
        contains_numeric_claim=False,
        numeric_claim_supported=True,
        approved_for_reuse=approved,
        review_required=review_required,
        reasons=["Mapped to verified evidence."],
    )


def test_selects_approved_job_relevant_wording() -> None:
    match = make_match()
    candidates = [
        _candidate(
            "Built a Python and AWS data pipeline using Docker.",
            relevance=0.9,
        ),
        _candidate(
            "Presented classroom materials to students.",
            relevance=0.3,
        ),
    ]

    selected = select_cv_wording(candidates, match)

    assert selected
    assert (
        selected[0].text
        == "Built a Python and AWS data pipeline using Docker."
    )


def test_rejects_unapproved_reference_wording() -> None:
    match = make_match()
    candidates = [
        _candidate(
            "Invented unsupported achievement.",
            approved=False,
        )
    ]

    assert select_cv_wording(candidates, match) == []


def test_review_required_wording_is_excluded_by_default() -> None:
    match = make_match()
    candidates = [
        _candidate(
            "Potential wording requiring human verification.",
            review_required=True,
        )
    ]

    assert select_cv_wording(candidates, match) == []


def test_limits_and_deduplicates_selected_wording() -> None:
    match = make_match()
    candidates = [
        _candidate("Built a Python AWS data pipeline.", relevance=0.9),
        _candidate("Built a Python AWS data pipeline.", relevance=0.8),
        _candidate("Used SQL for data analysis.", relevance=0.7),
    ]

    selected = select_cv_wording(
        candidates,
        match,
        maximum_items=1,
    )

    assert len(selected) == 1
