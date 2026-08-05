from src.application_models import ClaimStatus
from src.claim_guard import check_claims
from tests.phase5_helpers import make_selected_evidence


def test_supported_claim_is_not_blocked():
    results = check_claims(
        "Built a Python and AWS document-processing pipeline.",
        make_selected_evidence(),
    )
    assert results[0].status in {
        ClaimStatus.APPROVED,
        ClaimStatus.REVIEW_REQUIRED,
    }


def test_unsupported_number_is_blocked():
    results = check_claims(
        "Improved results by 95%.",
        make_selected_evidence(),
    )
    assert results[0].status == ClaimStatus.BLOCKED


def test_unrelated_claim_requires_review():
    results = check_claims(
        "Led a global legal engineering division.",
        make_selected_evidence(),
    )
    assert results[0].status == ClaimStatus.REVIEW_REQUIRED
