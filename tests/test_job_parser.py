from __future__ import annotations

import pytest

from src.job_models import FetchStatus, FetchedJobPage
from src.job_parser import parse_job_page


def test_parses_json_ld_job(fetched_json_ld_page) -> None:
    parsed = parse_job_page(fetched_json_ld_page)
    assert parsed.title == "Machine Learning Engineer"
    assert parsed.company == "Example AI Ltd"
    assert parsed.source_job_id == "AI-123"
    assert parsed.location_text == "London, Greater London, EC1A 1BB, GB"
    assert parsed.salary_text == "GBP 50000-65000 YEAR"
    assert parsed.parser_name == "json_ld_job_posting"


def test_generic_html_fallback() -> None:
    page = FetchedJobPage(
        requested_url="https://example.com/jobs/data",
        source="manual",
        fetch_status=FetchStatus.SUCCESS,
        status_code=200,
        content_type="text/html",
        html=(
            "<html><head><meta property='og:site_name' content='Example Ltd'>"
            "<meta name='description' content='Build data pipelines'></head>"
            "<body><h1>Data Engineer</h1></body></html>"
        ),
    )
    parsed = parse_job_page(page)
    assert parsed.title == "Data Engineer"
    assert parsed.company == "Example Ltd"
    assert str(parsed.parse_status) == "partial"


def test_rejects_unsuccessful_fetch() -> None:
    page = FetchedJobPage(
        requested_url="https://example.com/jobs/data",
        source="manual",
        fetch_status=FetchStatus.FAILED,
        error_message="timeout",
    )
    with pytest.raises(ValueError, match="cannot parse"):
        parse_job_page(page)
