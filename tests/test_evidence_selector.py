from src.application_models import EvidenceDecision
from src.evidence_selector import select_evidence
from tests.phase5_helpers import make_match, make_profile


def test_selects_relevant_verified_evidence():
    selected = select_evidence(make_profile().evidence, make_match())
    assert any(
        item.decision == EvidenceDecision.SELECTED
        for item in selected
    )


def test_rejects_unapproved_evidence():
    profile = make_profile()
    profile.evidence[0].approved_for_application = False

    selected = select_evidence(
        profile.evidence,
        make_match(),
        minimum_relevance=0.0,
    )

    item = next(
        item for item in selected
        if item.evidence_id == "exp_1"
    )
    assert item.decision == EvidenceDecision.REJECTED


def test_limits_number_of_items():
    selected = select_evidence(
        make_profile().evidence,
        make_match(),
        maximum_items=2,
        minimum_relevance=0.0,
    )
    assert len(selected) == 2
