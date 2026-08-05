from __future__ import annotations

from pathlib import Path

from src.ingest_jobs import run_ingestion
from src.job_models import FetchStatus, FetchedJobPage


def test_ingestion_inserts_and_reports(
    tmp_path: Path,
    monkeypatch,
    json_ld_html: str,
) -> None:
    root = tmp_path
    (root / "input").mkdir()
    (root / "reports").mkdir()
    (root / "data").mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    csv_path = root / "input" / "job_urls.csv"
    csv_path.write_text(
        "url,source,notes,enabled,added_at\n"
        "https://jobs.example.com/ai-123,company_site,,true,\n",
        encoding="utf-8",
    )

    def fake_find_root(*args, **kwargs):
        return root

    def fake_fetch(record, **kwargs):
        return FetchedJobPage(
            requested_url=record.url,
            final_url=record.url,
            source=record.source,
            fetch_status=FetchStatus.SUCCESS,
            status_code=200,
            content_type="text/html",
            html=json_ld_html,
        )

    monkeypatch.setattr("src.ingest_jobs.find_repository_root", fake_find_root)
    monkeypatch.setattr("src.ingest_jobs.fetch_job_page", fake_fetch)

    run = run_ingestion(
        csv_path=csv_path,
        db_path=root / "data" / "jobs.db",
        report_path=root / "reports" / "job_ingestion_report.json",
    )

    assert run.inserted_count == 1
    assert run.failed_count == 0
    assert (root / "data" / "jobs.db").exists()
    assert (root / "reports" / "job_ingestion_report.json").exists()


def test_second_ingestion_marks_duplicate(
    tmp_path: Path,
    monkeypatch,
    json_ld_html: str,
) -> None:
    root = tmp_path
    (root / "input").mkdir()
    (root / "reports").mkdir()
    (root / "data").mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    csv_path = root / "input" / "job_urls.csv"
    csv_path.write_text(
        "url,source,notes,enabled,added_at\n"
        "https://jobs.example.com/ai-123,company_site,,true,\n",
        encoding="utf-8",
    )

    monkeypatch.setattr("src.ingest_jobs.find_repository_root", lambda *a, **k: root)
    monkeypatch.setattr(
        "src.ingest_jobs.fetch_job_page",
        lambda record, **kwargs: FetchedJobPage(
            requested_url=record.url,
            final_url=record.url,
            source=record.source,
            fetch_status=FetchStatus.SUCCESS,
            status_code=200,
            content_type="text/html",
            html=json_ld_html,
        ),
    )

    kwargs = {
        "csv_path": csv_path,
        "db_path": root / "data" / "jobs.db",
        "report_path": root / "reports" / "job_ingestion_report.json",
    }
    first = run_ingestion(**kwargs)
    second = run_ingestion(**kwargs)
    assert first.inserted_count == 1
    assert second.duplicate_count == 1
