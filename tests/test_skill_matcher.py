from src.matching_models import MatchStrength
from src.skill_matcher import match_skills
from tests.phase4_helpers import make_profile, make_requirements


def test_exact_python_match():
    result = match_skills(make_requirements(), make_profile())
    python_match = next(
        item for item in result.matches
        if item.required_skill == "python"
    )
    assert python_match.match_strength == MatchStrength.EXACT


def test_aws_related_match():
    result = match_skills(make_requirements(), make_profile())
    aws_match = next(
        item for item in result.matches
        if item.required_skill == "aws"
    )
    assert aws_match.match_strength in {
        MatchStrength.EXACT,
        MatchStrength.STRONG_RELATED,
    }


def test_missing_skill_reduces_score():
    result = match_skills(
        make_requirements(),
        make_profile(skills=[], tools=[]),
    )
    assert result.missing_required >= 1
    assert result.score < 50
