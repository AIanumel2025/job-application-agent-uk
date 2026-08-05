from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.job_database import JobDatabase
from src.job_models import IngestionRun


def test_initialise_insert_and_retrieve(tmp_path: Path, sample_job) -> None:
    database = JobDatabase(tmp_path / "jobs.db")
    database.initialise()
    database.insert_job(sample_job)

    assert database.count_jobs() == 1
    restored = database.get_job(sample_job.job_id)
    assert restored is not None
    assert restored.title == sample_job.title
    assert restored.canonical_url == sample_job.canonical_url


def test_list_jobs(tmp_path: Path, sample_job) -> None:
    database = JobDatabase(tmp_path / "jobs.db")
    database.initialise()
    database.insert_job(sample_job)
    assert len(database.list_jobs()) == 1


def test_update_job(tmp_path: Path, sample_job) -> None:
    database = JobDatabase(tmp_path / "jobs.db")
    database.initialise()
    database.insert_job(sample_job)
    updated = sample_job.model_copy(update={"status": "reviewed"})
    database.update_job(updated)
    restored = database.get_job(sample_job.job_id)
    assert restored is not None
    assert str(restored.status) == "reviewed"


def test_saves_ingestion_run(tmp_path: Path) -> None:
    database = JobDatabase(tmp_path / "jobs.db")
    database.initialise()
    run = IngestionRun(started_at=datetime.now(timezone.utc))
    database.save_ingestion_run(run)
    with database.connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM ingestion_runs").fetchone()[0]
    assert count == 1
