from src.match_explainer import build_match_explanation
from src.match_scoring import calculate_match_score
from tests.phase4_helpers import (
    empty_experience_result,
    empty_skill_result,
    make_eligibility,
    make_preference_result,
)


def test_explanation_contains_score_summary():
    skills = empty_skill_result(80)
    experience = empty_experience_result(70)
    eligibility = make_eligibility(100)
    preferences = make_preference_result(90)
    score = calculate_match_score(
        skill_result=skills,
        experience_result=experience,
        eligibility_result=eligibility,
        preference_result=preferences,
        evidence_quality_score=80,
    )

    explanation = build_match_explanation(
        skill_result=skills,
        experience_result=experience,
        eligibility_result=eligibility,
        preference_result=preferences,
        score_breakdown=score,
    )

    assert "Overall match score" in explanation.summary
    assert explanation.recommended_actions
