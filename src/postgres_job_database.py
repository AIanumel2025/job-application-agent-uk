"""PostgreSQL persistence for normalised vacancies and ingestion runs."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, RowMapping

from src.job_models import (
    IngestionRun,
    JobLocation,
    NormalisedJob,
    SalaryRange,
)


SCHEMA_VERSION = 1


def _load_database_url() -> str:
    """Load DATABASE_URL from the repository .env file or environment."""

    root = Path(__file__).resolve().parents[1]
    load_dotenv(dotenv_path=root / ".env")

    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not configured. "
            "Add it to the repository .env file."
        )

    return url


class PostgresJobDatabase:
    """PostgreSQL repository matching the existing SQLite JobDatabase interface."""

    def __init__(
        self,
        database_url: str | None = None,
    ) -> None:
        self.database_url = database_url or _load_database_url()
        self.engine: Engine = create_engine(
            self.database_url,
            pool_pre_ping=True,
        )

    def initialise(self) -> None:
        """Create the Phase 3 persistence schema when it does not exist."""

        statements = [
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """,
            """
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
                location_json JSONB NOT NULL,
                salary_json JSONB,
                employment_types_json JSONB NOT NULL,
                sponsorship_status TEXT NOT NULL,
                sponsorship_evidence_json JSONB NOT NULL,
                description TEXT NOT NULL,
                responsibilities_json JSONB NOT NULL,
                requirements_json JSONB NOT NULL,
                preferred_skills_json JSONB NOT NULL,
                benefits_json JSONB NOT NULL,
                posted_date DATE,
                closing_date DATE,
                date_found TIMESTAMPTZ NOT NULL,
                status TEXT NOT NULL,
                description_hash TEXT,
                deduplication_key TEXT,
                recruiter_name TEXT,
                recruiter_email TEXT,
                raw_source_data_json JSONB NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL
            )
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_canonical_url
                ON jobs(canonical_url)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_jobs_source_job_id
                ON jobs(source, source_job_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_jobs_description_hash
                ON jobs(description_hash)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_jobs_company_title
                ON jobs(company_normalised, title_normalised)
            """,
            """
            CREATE TABLE IF NOT EXISTS ingestion_runs (
                run_id TEXT PRIMARY KEY,
                started_at TIMESTAMPTZ NOT NULL,
                completed_at TIMESTAMPTZ,
                input_count INTEGER NOT NULL,
                fetched_count INTEGER NOT NULL,
                parsed_count INTEGER NOT NULL,
                inserted_count INTEGER NOT NULL,
                updated_count INTEGER NOT NULL,
                duplicate_count INTEGER NOT NULL,
                skipped_count INTEGER NOT NULL,
                failed_count INTEGER NOT NULL,
                results_json JSONB NOT NULL
            )
            """,
        ]

        with self.engine.begin() as conn:
            for statement in statements:
                conn.execute(text(statement))

            conn.execute(
                text(
                    """
                    INSERT INTO metadata(key, value)
                    VALUES('schema_version', :value)
                    ON CONFLICT(key)
                    DO UPDATE SET value = EXCLUDED.value
                    """
                ),
                {"value": str(SCHEMA_VERSION)},
            )

    def insert_job(self, job: NormalisedJob) -> None:
        now = datetime.now(timezone.utc)

        sql = text(
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
                :job_id, :source, :source_job_id, :application_url,
                :canonical_url, :title, :title_normalised, :company,
                :company_normalised, CAST(:location_json AS JSONB),
                CAST(:salary_json AS JSONB),
                CAST(:employment_types_json AS JSONB),
                :sponsorship_status,
                CAST(:sponsorship_evidence_json AS JSONB),
                :description,
                CAST(:responsibilities_json AS JSONB),
                CAST(:requirements_json AS JSONB),
                CAST(:preferred_skills_json AS JSONB),
                CAST(:benefits_json AS JSONB),
                :posted_date, :closing_date, :date_found, :status,
                :description_hash, :deduplication_key,
                :recruiter_name, :recruiter_email,
                CAST(:raw_source_data_json AS JSONB),
                :created_at, :updated_at
            )
            """
        )

        with self.engine.begin() as conn:
            conn.execute(sql, self._job_to_params(job, now))

    def update_job(self, job: NormalisedJob) -> None:
        now = datetime.now(timezone.utc)
        params = self._job_to_params(job, now)

        sql = text(
            """
            UPDATE jobs SET
                source = :source,
                source_job_id = :source_job_id,
                application_url = :application_url,
                canonical_url = :canonical_url,
                title = :title,
                title_normalised = :title_normalised,
                company = :company,
                company_normalised = :company_normalised,
                location_json = CAST(:location_json AS JSONB),
                salary_json = CAST(:salary_json AS JSONB),
                employment_types_json = CAST(:employment_types_json AS JSONB),
                sponsorship_status = :sponsorship_status,
                sponsorship_evidence_json =
                    CAST(:sponsorship_evidence_json AS JSONB),
                description = :description,
                responsibilities_json =
                    CAST(:responsibilities_json AS JSONB),
                requirements_json = CAST(:requirements_json AS JSONB),
                preferred_skills_json =
                    CAST(:preferred_skills_json AS JSONB),
                benefits_json = CAST(:benefits_json AS JSONB),
                posted_date = :posted_date,
                closing_date = :closing_date,
                date_found = :date_found,
                status = :status,
                description_hash = :description_hash,
                deduplication_key = :deduplication_key,
                recruiter_name = :recruiter_name,
                recruiter_email = :recruiter_email,
                raw_source_data_json =
                    CAST(:raw_source_data_json AS JSONB),
                updated_at = :updated_at
            WHERE job_id = :job_id
            """
        )

        with self.engine.begin() as conn:
            result = conn.execute(sql, params)

        if result.rowcount == 0:
            raise KeyError(f"job does not exist: {job.job_id}")

    def get_job(
        self,
        job_id: UUID | str,
    ) -> NormalisedJob | None:
        with self.engine.connect() as conn:
            row = (
                conn.execute(
                    text(
                        """
                        SELECT *
                        FROM jobs
                        WHERE job_id = :job_id
                        """
                    ),
                    {"job_id": str(job_id)},
                )
                .mappings()
                .first()
            )

        return self._row_to_job(row) if row else None

    def get_job_by_canonical_url(
        self,
        canonical_url: str,
    ) -> NormalisedJob | None:
        with self.engine.connect() as conn:
            row = (
                conn.execute(
                    text(
                        """
                        SELECT *
                        FROM jobs
                        WHERE canonical_url = :canonical_url
                        """
                    ),
                    {"canonical_url": canonical_url},
                )
                .mappings()
                .first()
            )

        return self._row_to_job(row) if row else None

    def list_jobs(
        self,
        *,
        limit: int | None = None,
    ) -> list[NormalisedJob]:
        if limit is None:
            sql = text(
                """
                SELECT *
                FROM jobs
                ORDER BY created_at DESC
                """
            )
            params: dict[str, Any] = {}
        else:
            sql = text(
                """
                SELECT *
                FROM jobs
                ORDER BY created_at DESC
                LIMIT :limit
                """
            )
            params = {"limit": limit}

        with self.engine.connect() as conn:
            rows = conn.execute(
                sql,
                params,
            ).mappings().all()

        return [
            self._row_to_job(row)
            for row in rows
        ]

    def count_jobs(self) -> int:
        with self.engine.connect() as conn:
            count = conn.execute(
                text("SELECT COUNT(*) FROM jobs")
            ).scalar_one()

        return int(count)

    def save_ingestion_run(
        self,
        run: IngestionRun,
    ) -> None:
        payload = run.model_dump(mode="json")

        params = {
            "run_id": str(run.run_id),
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "input_count": run.input_count,
            "fetched_count": run.fetched_count,
            "parsed_count": run.parsed_count,
            "inserted_count": run.inserted_count,
            "updated_count": run.updated_count,
            "duplicate_count": run.duplicate_count,
            "skipped_count": run.skipped_count,
            "failed_count": run.failed_count,
            "results_json": json.dumps(payload["results"]),
        }

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ingestion_runs (
                        run_id, started_at, completed_at, input_count,
                        fetched_count, parsed_count, inserted_count,
                        updated_count, duplicate_count, skipped_count,
                        failed_count, results_json
                    ) VALUES (
                        :run_id, :started_at, :completed_at, :input_count,
                        :fetched_count, :parsed_count, :inserted_count,
                        :updated_count, :duplicate_count, :skipped_count,
                        :failed_count, CAST(:results_json AS JSONB)
                    )
                    ON CONFLICT(run_id)
                    DO UPDATE SET
                        completed_at = EXCLUDED.completed_at,
                        input_count = EXCLUDED.input_count,
                        fetched_count = EXCLUDED.fetched_count,
                        parsed_count = EXCLUDED.parsed_count,
                        inserted_count = EXCLUDED.inserted_count,
                        updated_count = EXCLUDED.updated_count,
                        duplicate_count = EXCLUDED.duplicate_count,
                        skipped_count = EXCLUDED.skipped_count,
                        failed_count = EXCLUDED.failed_count,
                        results_json = EXCLUDED.results_json
                    """
                ),
                params,
            )

    def _job_to_params(
        self,
        job: NormalisedJob,
        now: datetime,
    ) -> dict[str, Any]:
        return {
            "job_id": str(job.job_id),
            "source": str(job.source),
            "source_job_id": job.source_job_id,
            "application_url": str(job.application_url),
            "canonical_url": job.canonical_url,
            "title": job.title,
            "title_normalised": job.title_normalised,
            "company": job.company,
            "company_normalised": job.company_normalised,
            "location_json": json.dumps(
                job.location.model_dump(mode="json")
            ),
            "salary_json": (
                json.dumps(job.salary.model_dump(mode="json"))
                if job.salary
                else None
            ),
            "employment_types_json": json.dumps(job.employment_types),
            "sponsorship_status": str(job.sponsorship_status),
            "sponsorship_evidence_json": json.dumps(
                job.sponsorship_evidence
            ),
            "description": job.description,
            "responsibilities_json": json.dumps(job.responsibilities),
            "requirements_json": json.dumps(job.requirements),
            "preferred_skills_json": json.dumps(job.preferred_skills),
            "benefits_json": json.dumps(job.benefits),
            "posted_date": job.posted_date,
            "closing_date": job.closing_date,
            "date_found": job.date_found,
            "status": str(job.status),
            "description_hash": job.description_hash,
            "deduplication_key": job.deduplication_key,
            "recruiter_name": job.recruiter_name,
            "recruiter_email": job.recruiter_email,
            "raw_source_data_json": json.dumps(
                job.raw_source_data,
                default=str,
            ),
            "created_at": now,
            "updated_at": now,
        }

    @staticmethod
    def _json_value(value: Any) -> Any:
        if isinstance(value, str):
            return json.loads(value)
        return value

    def _row_to_job(
        self,
        row: RowMapping,
    ) -> NormalisedJob:
        salary_raw = self._json_value(row["salary_json"])

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
                self._json_value(row["location_json"])
            ),
            salary=(
                SalaryRange.model_validate(salary_raw)
                if salary_raw
                else None
            ),
            employment_types=self._json_value(
                row["employment_types_json"]
            ),
            sponsorship_status=row["sponsorship_status"],
            sponsorship_evidence=self._json_value(
                row["sponsorship_evidence_json"]
            ),
            description=row["description"],
            responsibilities=self._json_value(
                row["responsibilities_json"]
            ),
            requirements=self._json_value(
                row["requirements_json"]
            ),
            preferred_skills=self._json_value(
                row["preferred_skills_json"]
            ),
            benefits=self._json_value(
                row["benefits_json"]
            ),
            posted_date=row["posted_date"],
            closing_date=row["closing_date"],
            date_found=row["date_found"],
            status=row["status"],
            description_hash=row["description_hash"],
            deduplication_key=row["deduplication_key"],
            recruiter_name=row["recruiter_name"],
            recruiter_email=row["recruiter_email"],
            raw_source_data=self._json_value(
                row["raw_source_data_json"]
            ),
        )
