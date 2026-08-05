from src.career_profile_builder import build_career_matching_profile


def test_builds_profile_from_mapping():
    bundle = {
        "profile": {"name": "Anthony"},
        "skills": {"skills": [{"name": "Python"}, {"name": "SQL"}]},
        "projects": {
            "projects": [
                {
                    "project_id": "p1",
                    "name": "Pipeline",
                    "description": "Python data pipeline",
                    "skills": ["AWS"],
                }
            ]
        },
        "target_roles": {
            "preferred_roles": ["Data Engineer"],
            "preferred_locations": ["London"],
            "preferred_work_models": ["Hybrid"],
            "employment_types": ["Permanent"],
            "minimum_salary": 50000,
        },
        "application_answers": {
            "right_to_work_uk": True,
            "future_sponsorship_required": True,
            "willing_to_relocate": True,
        },
    }

    profile = build_career_matching_profile(bundle)

    assert profile.name == "Anthony"
    assert "Python" in profile.skills
    assert "AWS" in profile.skills
    assert profile.minimum_salary == 50000


def test_deduplicates_profile_values():
    bundle = {
        "profile": {"name": "Anthony"},
        "skills": {
            "skills": [
                {"name": "Python"},
                {"name": "python"},
            ]
        },
    }
    profile = build_career_matching_profile(bundle)
    assert len(profile.skills) == 1


def test_does_not_invent_missing_salary():
    profile = build_career_matching_profile(
        {"profile": {"name": "Anthony"}}
    )
    assert profile.minimum_salary is None
