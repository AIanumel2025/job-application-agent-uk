"""SQLite persistence for normalised vacancies and ingestion runs."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from uuid import UUID

from src.job_models import (
    IngestionRun,
    JobLocation,
    NormalisedJob,
    SalaryRange,
)


SCHEMA_VERSION = 1


class JobDatabase:
    """Small SQLite repository for Phase 3 job ingestion."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialise(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    source_job_id TEXT,
                    application_url TEXT NOT NULL,
                    canonical_url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    title_normalised TEXT NOT NULL,
                    company TEXT NOT NULL,
                    company_normalised TEXT NOT NULL,
                    location_json TEXT NOT NULL,
                    salary_json TEXT,
                    employment_types_json TEXT NOT NULL,
                    sponsorship_status TEXT NOT NULL,
                    sponsorship_evidence_json TEXT NOT NULL,
                    description TEXT NOT NULL,
                    responsibilities_json TEXT NOT NULL,
                    requirements_json TEXT NOT NULL,
                    preferred_skills_json TEXT NOT NULL,
                    benefits_json TEXT NOT NULL,
                    posted_date TEXT,
                    closing_date TEXT,
                    date_found TEXT NOT NULL,
                    status TEXT NOT NULL,
                    description_hash TEXT,
                    deduplication_key TEXT,
                    recruiter_name TEXT,
                    recruiter_email TEXT,
                    raw_source_data_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_canonical_url
                    ON jobs(canonical_url);

                CREATE INDEX IF NOT EXISTS idx_jobs_source_job_id
                    ON jobs(source, source_job_id);

                CREATE INDEX IF NOT EXISTS idx_jobs_description_hash
                    ON jobs(description_hash);

                CREATE INDEX IF NOT EXISTS idx_jobs_company_title
                    ON jobs(company_normalised, title_normalised);

                CREATE TABLE IF NOT EXISTS ingestion_runs (
                    run_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    input_count INTEGER NOT NULL,
                    fetched_count INTEGER NOT NULL,
                    parsed_count INTEGER NOT NULL,
                    inserted_count INTEGER NOT NULL,
                    updated_count INTEGER NOT NULL,
                    duplicate_count INTEGER NOT NULL,
                    skipped_count INTEGER NOT NULL,
                    failed_count INTEGER NOT NULL,
                    results_json TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                INSERT INTO metadata(key, value)
                VALUES('schema_version', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (str(SCHEMA_VERSION),),
            )

    def insert_job(self, job: NormalisedJob) -> None:
        now = datetime.now(timezone.utc).isoformat()

        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    job_id, source, source_job_id, application_url,
                    canonical_url, title, title_normalised, company,
                    company_normalised, location_json, salary_json,
                    employment_types_json, sponsorship_status,
                    sponsorship_evidence_json, description,
                    responsibilities_json, requirements_json,
                    preferred_skills_json, benefits_json, posted_date,
                    closing_date, date_found, status, description_hash,
                    deduplication_key, recruiter_name, recruiter_email,
                    raw_source_data_json, created_at, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                self._job_to_row(job, now),
            )

    def update_job(self, job: NormalisedJob) -> None:
        now = datetime.now(timezone.utc).isoformat()

        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE jobs SET
                    source = ?,
                    source_job_id = ?,
                    application_url = ?,
                    canonical_url = ?,
                    title = ?,
                    title_normalised = ?,
                    company = ?,
                    company_normalised = ?,
                    location_json = ?,
                    salary_json = ?,
                    employment_types_json = ?,
                    sponsorship_status = ?,
                    sponsorship_evidence_json = ?,
                    description = ?,
                    responsibilities_json = ?,
                    requirements_json = ?,
                    preferred_skills_json = ?,
                    benefits_json = ?,
                    posted_date = ?,
                    closing_date = ?,
                    date_found = ?,
                    status = ?,
                    description_hash = ?,
                    deduplication_key = ?,
                    recruiter_name = ?,
                    recruiter_email = ?,
                    raw_source_data_json = ?,
                    updated_at = ?
                WHERE job_id = ?
                """,
                self._job_update_row(job, now),
            )

            if cursor.rowcount == 0:
                raise KeyError(f"job does not exist: {job.job_id}")

    def get_job(self, job_id: UUID | str) -> NormalisedJob | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (str(job_id),),
            ).fetchone()

        return self._row_to_job(row) if row else None

    def get_job_by_canonical_url(self, canonical_url: str) -> NormalisedJob | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE canonical_url = ?",
                (canonical_url,),
            ).fetchone()

        return self._row_to_job(row) if row else None

    def list_jobs(self, *, limit: int | None = None) -> list[NormalisedJob]:
        query = "SELECT * FROM jobs ORDER BY created_at DESC"
        params: tuple[object, ...] = ()

        if limit is not None:
            query += " LIMIT ?"
            params = (limit,)

        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [self._row_to_job(row) for row in rows]

    def count_jobs(self) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM jobs").fetchone()
        return int(row["count"])

    def save_ingestion_run(self, run: IngestionRun) -> None:
        payload = run.model_dump(mode="json")

        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO ingestion_runs (
                    run_id, started_at, completed_at, input_count,
                    fetched_count, parsed_count, inserted_count,
                    updated_count, duplicate_count, skipped_count,
                    failed_count, results_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    completed_at = excluded.completed_at,
                    input_count = excluded.input_count,
                    fetched_count = excluded.fetched_count,
                    parsed_count = excluded.parsed_count,
                    inserted_count = excluded.inserted_count,
                    updated_count = excluded.updated_count,
                    duplicate_count = excluded.duplicate_count,
                    skipped_count = excluded.skipped_count,
                    failed_count = excluded.failed_count,
                    results_json = excluded.results_json
                """,
                (
                    str(run.run_id),
                    run.started_at.isoformat(),
                    run.completed_at.isoformat() if run.completed_at else None,
                    run.input_count,
                    run.fetched_count,
                    run.parsed_count,
                    run.inserted_count,
                    run.updated_count,
                    run.duplicate_count,
                    run.skipped_count,
                    run.failed_count,
                    json.dumps(payload["results"]),
                ),
            )

    def _job_to_row(self, job: NormalisedJob, now: str) -> tuple:
        return (
            str(job.job_id),
            str(job.source),
            job.source_job_id,
            str(job.application_url),
            job.canonical_url,
            job.title,
            job.title_normalised,
            job.company,
            job.company_normalised,
            json.dumps(job.location.model_dump(mode="json")),
            json.dumps(job.salary.model_dump(mode="json")) if job.salary else None,
            json.dumps(job.employment_types),
            str(job.sponsorship_status),
            json.dumps(job.sponsorship_evidence),
            job.description,
            json.dumps(job.responsibilities),
            json.dumps(job.requirements),
            json.dumps(job.preferred_skills),
            json.dumps(job.benefits),
            job.posted_date.isoformat() if job.posted_date else None,
            job.closing_date.isoformat() if job.closing_date else None,
            job.date_found.isoformat(),
            str(job.status),
            job.description_hash,
            job.deduplication_key,
            job.recruiter_name,
            job.recruiter_email,
            json.dumps(job.raw_source_data, default=str),
            now,
            now,
        )

    def _job_update_row(self, job: NormalisedJob, now: str) -> tuple:
        inserted = self._job_to_row(job, now)
        return inserted[1:28] + (now, str(job.job_id))

    def _row_to_job(self, row: sqlite3.Row) -> NormalisedJob:
        salary_raw = json.loads(row["salary_json"]) if row["salary_json"] else None

        return NormalisedJob(
            job_id=row["job_id"],
            source=row["source"],
            source_job_id=row["source_job_id"],
            application_url=row["application_url"],
            canonical_url=row["canonical_url"],
            title=row["title"],
            title_normalised=row["title_normalised"],
            company=row["company"],
            company_normalised=row["company_normalised"],
            location=JobLocation.model_validate(
                json.loads(row["location_json"])
            ),
            salary=SalaryRange.model_validate(salary_raw) if salary_raw else None,
            employment_types=json.loads(row["employment_types_json"]),
            sponsorship_status=row["sponsorship_status"],
            sponsorship_evidence=json.loads(
                row["sponsorship_evidence_json"]
            ),
            description=row["description"],
            responsibilities=json.loads(row["responsibilities_json"]),
            requirements=json.loads(row["requirements_json"]),
            preferred_skills=json.loads(row["preferred_skills_json"]),
            benefits=json.loads(row["benefits_json"]),
            posted_date=row["posted_date"],
            closing_date=row["closing_date"],
            date_found=row["date_found"],
            status=row["status"],
            description_hash=row["description_hash"],
            deduplication_key=row["deduplication_key"],
            recruiter_name=row["recruiter_name"],
            recruiter_email=row["recruiter_email"],
            raw_source_data=json.loads(row["raw_source_data_json"]),
        )
