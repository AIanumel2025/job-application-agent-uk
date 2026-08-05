from uuid import uuid4

from src.job_ranker import rank_jobs, urgency_score_for
from src.matching_models import (
    EligibilityResult,
    EligibilityStatus,
    JobMatchResult,
    MatchExplanation,
    MatchRecommendation,
)
from src.match_scoring import calculate_match_score
from tests.phase4_helpers import (
    empty_experience_result,
    empty_skill_result,
    make_eligibility,
    make_preference_result,
    make_requirements,
)


def make_result(score, title):
    eligibility = make_eligibility()
    breakdown = calculate_match_score(
        skill_result=empty_skill_result(score),
        experience_result=empty_experience_result(score),
        eligibility_result=eligibility,
        preference_result=make_preference_result(score),
        evidence_quality_score=score,
    )
    return JobMatchResult(
        job_id=uuid4(),
        job_title=title,
        company="Example Ltd",
        requirements=make_requirements(),
        skill_result=empty_skill_result(score),
        experience_result=empty_experience_result(score),
        eligibility_result=eligibility,
        preference_result=make_preference_result(score),
        score_breakdown=breakdown,
        explanation=MatchExplanation(
            summary="Summary",
            recommended_actions=["Proceed"],
        ),
        recommendation=MatchRecommendation.GOOD_MATCH,
        final_score=breakdown.total_score,
    )


def test_higher_scoring_job_ranks_first():
    high = make_result(90, "High")
    low = make_result(60, "Low")
    report = rank_jobs([low, high])
    assert report.ranked_jobs[0].job_title == "High"
    assert report.ranked_jobs[0].rank == 1


def test_missing_closing_date_has_default_urgency():
    assert urgency_score_for(None) == 40
