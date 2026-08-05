import pytest
from pydantic import ValidationError
from uuid import uuid4

from src.matching_models import (
    EligibilityCheck,
    EligibilityStatus,
    HardStopType,
    MatchScoreBreakdown,
    ScoreComponent,
)


def test_score_component_validates_weighted_score():
    item = ScoreComponent(
        name="skills",
        raw_score=80,
        weight=0.30,
        weighted_score=24,
    )
    assert item.weighted_score == 24


def test_score_component_rejects_wrong_weighted_score():
    with pytest.raises(ValidationError):
        ScoreComponent(
            name="skills",
            raw_score=80,
            weight=0.30,
            weighted_score=30,
        )


def test_score_weights_cannot_exceed_one():
    with pytest.raises(ValidationError):
        MatchScoreBreakdown(
            components=[
                ScoreComponent(
                    name="a", raw_score=100, weight=0.6, weighted_score=60
                ),
                ScoreComponent(
                    name="b", raw_score=100, weight=0.5, weighted_score=50
                ),
            ],
            total_score=100,
        )


def test_hard_stop_check_requires_type():
    with pytest.raises(ValidationError):
        EligibilityCheck(
            check_id="x",
            label="Test",
            status=EligibilityStatus.FAILED,
            is_hard_stop=True,
            explanation="Failed.",
        )


def test_hard_stop_check_accepts_type():
    check = EligibilityCheck(
        check_id="x",
        label="Test",
        status=EligibilityStatus.FAILED,
        hard_stop_type=HardStopType.NO_SPONSORSHIP,
        is_hard_stop=True,
        explanation="Failed.",
    )
    assert check.is_hard_stop is True
