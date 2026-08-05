from __future__ import annotations

from pathlib import Path

import pytest

from src.job_url_loader import load_job_urls, parse_boolean


def test_loads_valid_skips_blank_and_disabled(tmp_path: Path) -> None:
    path = tmp_path / "jobs.csv"
    path.write_text(
        "url,source,notes,enabled,added_at\n"
        "https://example.com/jobs/1,company,good,true,2026-08-04T18:00:00+01:00\n"
        ",,,,\n"
        "https://example.com/jobs/2,manual,,false,\n",
        encoding="utf-8",
    )
    result = load_job_urls(path)
    assert result.summary() == {
        "total_rows": 3,
        "valid_records": 1,
        "blank_rows": 1,
        "disabled_rows": 1,
        "issues": 0,
        "passed": True,
    }
    assert str(result.records[0].source) == "company_site"


def test_invalid_url_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "jobs.csv"
    path.write_text(
        "url,source,notes,enabled,added_at\nnot-a-url,manual,,true,\n",
        encoding="utf-8",
    )
    result = load_job_urls(path)
    assert result.valid_count == 0
    assert result.issues[0].code == "invalid_job_url_record"


def test_missing_header_raises(tmp_path: Path) -> None:
    path = tmp_path / "jobs.csv"
    path.write_text("url,source\nhttps://example.com,manual\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing required columns"):
        load_job_urls(path)


def test_parse_boolean_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        parse_boolean("perhaps")
