"""Shared pytest fixtures for Phase 2 and Phase 3 test suites."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from src.career_data_loader import (
    CareerDataBundle,
    find_repository_root,
    load_career_data,
)
from src.job_models import (
    FetchStatus,
    FetchedJobPage,
    JobSource,
    NormalisedJob,
)


# ---------------------------------------------------------------------------
# Phase 2 fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def repository_root() -> Path:
    """Return the real project repository root."""
    return find_repository_root(Path(__file__))


@pytest.fixture(scope="session")
def valid_bundle(repository_root: Path) -> CareerDataBundle:
    """Load the current validated career-data package."""
    return load_career_data(repository_root)


@pytest.fixture
def mutable_bundle(valid_bundle: CareerDataBundle) -> CareerDataBundle:
    """Return an isolated deep copy for mutation tests."""
    return valid_bundle.model_copy(deep=True)


@pytest.fixture
def temporary_repository(
    tmp_path: Path,
    repository_root: Path,
) -> Path:
    """Create an isolated repository containing the YAML data package."""

    temporary_root = tmp_path / "job-application-agent-uk"
    temporary_root.mkdir()

    shutil.copytree(
        repository_root / "career_data",
        temporary_root / "career_data",
    )
    shutil.copytree(
        repository_root / "source_documents",
        temporary_root / "source_documents",
    )

    source_pyproject = repository_root / "pyproject.toml"
    if source_pyproject.exists():
        shutil.copy2(
            source_pyproject,
            temporary_root / "pyproject.toml",
        )

    return temporary_root


# ---------------------------------------------------------------------------
# Phase 3 fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def json_ld_html() -> str:
    payload = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "identifier": {"value": "AI-123"},
        "title": "Machine Learning Engineer",
        "hiringOrganization": {"name": "Example AI Ltd"},
        "jobLocation": {
            "address": {
                "addressLocality": "London",
                "addressRegion": "Greater London",
                "postalCode": "EC1A 1BB",
                "addressCountry": "GB",
            }
        },
        "baseSalary": {
            "currency": "GBP",
            "value": {
                "minValue": 50000,
                "maxValue": 65000,
                "unitText": "YEAR",
            },
        },
        "employmentType": ["FULL_TIME", "PERMANENT"],
        "datePosted": "2026-08-01",
        "validThrough": "2026-08-31T23:59:59Z",
        "description": "<p>Build production ML systems.</p>",
        "url": "https://jobs.example.com/ai-123",
    }

    return (
        '<html><head><script type="application/ld+json">'
        + json.dumps(payload)
        + "</script></head>"
        "<body><h1>Machine Learning Engineer</h1></body></html>"
    )


@pytest.fixture
def fetched_json_ld_page(json_ld_html: str) -> FetchedJobPage:
    return FetchedJobPage(
        requested_url="https://jobs.example.com/ai-123?utm_source=test",
        final_url="https://jobs.example.com/ai-123",
        source=JobSource.COMPANY_SITE,
        fetch_status=FetchStatus.SUCCESS,
        status_code=200,
        content_type="text/html",
        html=json_ld_html,
    )


@pytest.fixture
def sample_job() -> NormalisedJob:
    return NormalisedJob(
        source=JobSource.COMPANY_SITE,
        source_job_id="AI-123",
        application_url="https://jobs.example.com/ai-123",
        canonical_url="https://jobs.example.com/ai-123",
        title="Machine Learning Engineer",
        title_normalised="machine learning engineer",
        company="Example AI Ltd",
        company_normalised="example ai",
        description="Build production machine-learning systems.",
        employment_types=["Permanent", "Full-time"],
    )
