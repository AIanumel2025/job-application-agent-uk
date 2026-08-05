from src.experience_matcher import match_experience
from src.matching_models import ExperienceEvidenceLevel
from tests.phase4_helpers import make_profile, make_requirements


def test_returns_experience_match():
    result = match_experience(make_requirements(), make_profile())
    assert len(result.matches) == 1


def test_uses_available_evidence():
    result = match_experience(make_requirements(), make_profile())
    assert result.matches[0].evidence_level != ExperienceEvidenceLevel.INSUFFICIENT


def test_no_evidence_is_insufficient():
    profile = make_profile(evidence=[])
    result = match_experience(make_requirements(), profile)
    assert result.insufficient_matches == 1
