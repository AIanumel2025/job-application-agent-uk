from src.job_requirement_extractor import extract_job_requirements
from src.matching_models import RequirementCategory, RequirementPriority
from tests.phase4_helpers import make_job


def test_extracts_skill_and_experience_requirements():
    job = make_job()
    result = extract_job_requirements(job)

    categories = {item.category for item in result.requirements}
    assert RequirementCategory.SKILL in categories
    assert RequirementCategory.EXPERIENCE in categories
    assert result.minimum_years_experience == 3.0


def test_preferred_skills_are_marked_preferred():
    result = extract_job_requirements(make_job())
    aws = [
        item for item in result.requirements
        if item.normalised_value and "aws" in item.normalised_value
    ]
    assert aws
    assert aws[0].priority == RequirementPriority.PREFERRED


def test_extracts_sponsorship_statement():
    result = extract_job_requirements(make_job())
    assert result.sponsorship_statement is not None
