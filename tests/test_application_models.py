import pytest
from pydantic import ValidationError

from src.application_models import (
    ApplicationPackManifest,
    ApplicationPackStatus,
    ClaimCheck,
    ClaimStatus,
)


def test_blocked_claim_blocks_manifest():
    manifest = ApplicationPackManifest(
        job_id="11111111-1111-1111-1111-111111111111",
        company="Example Ltd",
        role_title="Data Engineer",
        claim_checks=[
            ClaimCheck(
                claim_id="claim_1",
                text="Improved performance by 90%.",
                status=ClaimStatus.BLOCKED,
                reasons=["Unsupported metric."],
            )
        ],
    )
    assert manifest.status == ApplicationPackStatus.BLOCKED


def test_cover_letter_requires_three_paragraphs():
    from src.application_models import CoverLetter

    with pytest.raises(ValidationError):
        CoverLetter(
            candidate_name="Anthony",
            company="Example Ltd",
            role_title="Data Engineer",
            paragraphs=["One", "Two"],
            markdown="Draft",
        )


def test_generated_answer_requires_positive_word_count():
    from src.application_models import GeneratedApplicationAnswer

    with pytest.raises(ValidationError):
        GeneratedApplicationAnswer(
            question_id="q1",
            question="Why this role?",
            answer="Because.",
            word_count=0,
        )
