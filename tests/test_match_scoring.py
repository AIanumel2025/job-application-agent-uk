import pytest

from src.match_scoring import (
    calculate_match_score,
    recommendation_for,
    score_band_for,
)
from src.matching_models import (
    EligibilityCheck,
    EligibilityResult,
    EligibilityStatus,
    HardStopType,
    MatchRecommendation,
    ScoreBand,
)
from tests.phase4_helpers import (
    empty_experience_result,
    empty_skill_result,
    make_eligibility,
    make_preference_result,
)


def test_score_band_boundaries():
    assert score_band_for(85) == ScoreBand.STRONG
    assert score_band_for(70) == ScoreBand.GOOD
    assert score_band_for(55) == ScoreBand.POSSIBLE
    assert score_band_for(40) == ScoreBand.WEAK
    assert score_band_for(39) == ScoreBand.POOR


def test_calculates_weighted_score():
    result = calculate_match_score(
        skill_result=empty_skill_result(80),
        experience_result=empty_experience_result(70),
        eligibility_result=make_eligibility(100),
        preference_result=make_preference_result(90),
        evidence_quality_score=80,
    )
    assert result.total_score == pytest.approx(83.0)


def test_weights_must_sum_to_one():
    with pytest.raises(ValueError):
        calculate_match_score(
            skill_result=empty_skill_result(),
            experience_result=empty_experience_result(),
            eligibility_result=make_eligibility(),
            preference_result=make_preference_result(),
            weights={
                "skills": 0.2,
                "experience": 0.2,
                "eligibility": 0.2,
                "preferences": 0.1,
                "evidence_quality": 0.1,
            },
        )


def test_hard_stop_caps_score_and_recommendation():
    check = EligibilityCheck(
        check_id="sponsor",
        label="Sponsorship",
        status=EligibilityStatus.FAILED,
        hard_stop_type=HardStopType.NO_SPONSORSHIP,
        is_hard_stop=True,
        explanation="No sponsorship.",
    )
    eligibility = EligibilityResult(
        checks=[check],
        overall_status=EligibilityStatus.FAILED,
        hard_stop_triggered=True,
        hard_stops=[check],
        score=0,
    )
    score = calculate_match_score(
        skill_result=empty_skill_result(100),
        experience_result=empty_experience_result(100),
        eligibility_result=eligibility,
        preference_result=make_preference_result(100),
        evidence_quality_score=100,
    )
    assert score.total_score <= 39
    assert recommendation_for(score.total_score, eligibility) == MatchRecommendation.NOT_ELIGIBLE
