from src.cv_tailor import tailor_cv
from tests.phase5_helpers import (
    make_match,
    make_profile,
    make_selected_evidence,
)


def test_tailored_cv_contains_candidate_and_role():
    cv = tailor_cv(
        make_profile(),
        make_match(),
        make_selected_evidence(),
    )
    assert "Anthony L. Anumel" in cv.markdown
    assert "Data Engineer" in cv.markdown


def test_tailored_cv_includes_selected_project():
    cv = tailor_cv(
        make_profile(),
        make_match(),
        make_selected_evidence(),
    )
    assert "Document Intelligence Pipeline" in cv.markdown


def test_tailored_cv_limits_skills():
    profile = make_profile(
        skills=[f"Skill {i}" for i in range(30)],
        tools=[f"Tool {i}" for i in range(30)],
    )
    cv = tailor_cv(
        profile,
        make_match(),
        make_selected_evidence(),
    )
    assert len(cv.skills) <= 18
