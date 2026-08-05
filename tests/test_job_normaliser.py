from __future__ import annotations

from src.job_models import ParsedJobRecord
from src.job_normaliser import (
    classify_sponsorship,
    normalise_employment_types,
    normalise_parsed_job,
    normalise_salary,
    normalise_work_model,
)


def test_normalises_annual_salary_range() -> None:
    salary = normalise_salary("£50k-£65k per annum")
    assert salary is not None
    assert salary.minimum == 50000
    assert salary.maximum == 65000
    assert str(salary.currency) == "GBP"


def test_annualises_daily_rate() -> None:
    salary = normalise_salary("£500 per day")
    assert salary is not None
    assert salary.minimum == 130000
    assert salary.is_estimated is True


def test_normalises_employment_and_work_model() -> None:
    values = normalise_employment_types("Permanent, full-time")
    assert "Permanent" in values
    assert "Full-time" in values
    assert normalise_work_model("Hybrid working") == "Hybrid"


def test_classifies_sponsorship_unavailable() -> None:
    result = classify_sponsorship(
        "Applicants must already have the right to work without sponsorship."
    )
    assert result.status == "explicitly_unavailable"
    assert result.evidence


def test_normalises_complete_parsed_job() -> None:
    parsed = ParsedJobRecord(
        source="company_site",
        application_url="https://example.com/jobs/1?utm_source=test",
        title="Sr. ML Engineer",
        company="Example AI Limited",
        location_text="London, Greater London, EC1A 1BB",
        salary_text="£50k-£65k",
        employment_type_text="Permanent full-time",
        work_model_text="Hybrid",
        description="Skilled Worker sponsorship can be provided.",
    )
    job = normalise_parsed_job(parsed)
    assert job.title_normalised == "senior machine learning engineer"
    assert job.company_normalised == "example ai"
    assert job.canonical_url == "https://example.com/jobs/1"
    assert job.location.postcode == "EC1A 1BB"
    assert str(job.sponsorship_status) == "confirmed"
