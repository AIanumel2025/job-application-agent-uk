from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from src.job_models import NormalisedJob, SalaryRange, canonicalise_url


def test_canonicalise_url_removes_tracking_and_fragment() -> None:
    assert canonicalise_url(
        "HTTPS://Example.COM/jobs/1/?utm_source=x&b=2&a=1#apply"
    ) == "https://example.com/jobs/1?a=1&b=2"


def test_salary_maximum_cannot_be_below_minimum() -> None:
    with pytest.raises(ValidationError):
        SalaryRange(minimum=60000, maximum=50000)


def test_normalised_job_populates_hashes() -> None:
    job = NormalisedJob(
        source="manual",
        application_url="https://example.com/jobs/1?utm_campaign=x",
        canonical_url="",
        title="Data Engineer",
        title_normalised="data engineer",
        company="Example Ltd",
        company_normalised="example",
        description="Build reliable pipelines.",
    )
    assert job.description_hash
    assert job.deduplication_key


def test_closing_date_cannot_precede_posted_date() -> None:
    with pytest.raises(ValidationError):
        NormalisedJob(
            source="manual",
            application_url="https://example.com/jobs/1",
            canonical_url="https://example.com/jobs/1",
            title="Data Engineer",
            title_normalised="data engineer",
            company="Example Ltd",
            company_normalised="example",
            description="Build pipelines.",
            posted_date=date(2026, 8, 10),
            closing_date=date(2026, 8, 1),
        )


def test_definitive_sponsorship_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        NormalisedJob(
            source="manual",
            application_url="https://example.com/jobs/1",
            canonical_url="https://example.com/jobs/1",
            title="Data Engineer",
            title_normalised="data engineer",
            company="Example Ltd",
            company_normalised="example",
            description="Build pipelines.",
            sponsorship_status="confirmed",
        )
