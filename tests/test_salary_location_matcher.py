from src.job_models import JobLocation, SalaryRange, WorkModel
from src.matching_models import FitStatus
from src.salary_location_matcher import (
    assess_location_fit,
    assess_preference_fit,
    assess_salary_fit,
)
from tests.phase4_helpers import make_job, make_profile


def test_salary_meets_candidate_minimum():
    result = assess_salary_fit(make_job(), make_profile())
    assert result.status in {FitStatus.MEETS, FitStatus.EXCEEDS}
    assert result.score >= 95


def test_salary_below_minimum():
    job = make_job(
        salary=SalaryRange(minimum=35000, maximum=45000, currency="GBP")
    )
    result = assess_salary_fit(job, make_profile())
    assert result.status == FitStatus.BELOW_REQUIREMENT


def test_location_and_hybrid_match():
    result = assess_location_fit(make_job(), make_profile())
    assert result.status == FitStatus.MEETS
    assert result.score == 100


def test_preference_result_has_combined_score():
    result = assess_preference_fit(make_job(), make_profile())
    assert 0 <= result.overall_score <= 100
