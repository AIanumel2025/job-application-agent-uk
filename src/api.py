"""FastAPI entry point for the Job Application Agent."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query

from src.job_models import NormalisedJob
from src.postgres_job_database import PostgresJobDatabase
from src.job_scoring_service import (
    load_matching_profile,
    score_job,
)
from src.matching_models import JobMatchResult

from src.application_pack_service import (
    generate_application_pack_for_job,
)
from pydantic import BaseModel, HttpUrl

from src.job_ingestion_service import ingest_job_url
from src.job_models import IngestionRun, JobSource

class JobIngestionRequest(BaseModel):
    url: HttpUrl
    source: JobSource = JobSource.MANUAL
    notes: str | None = None

app = FastAPI(
    title="Job Application Agent API",
    description=(
        "API layer for job ingestion, scoring, "
        "application generation, and human review."
    ),
    version="0.2.0",
)


db = PostgresJobDatabase()


@app.get("/health")
def health_check() -> dict[str, str]:
    """Confirm that the API service is running."""

    return {
        "status": "ok",
        "service": "job-application-agent",
        "database": "postgresql",
    }


@app.get(
    "/jobs",
    response_model=list[NormalisedJob],
)
def list_jobs(
    limit: int | None = Query(
        default=None,
        ge=1,
        le=500,
    ),
) -> list[NormalisedJob]:
    """Return jobs stored in PostgreSQL."""

    return db.list_jobs(limit=limit)


@app.get(
    "/jobs/{job_id}",
    response_model=NormalisedJob,
)
def get_job(job_id: str) -> NormalisedJob:
    """Return one stored job by ID."""

    job = db.get_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}",
        )

    return job

@app.post(
    "/jobs/{job_id}/score",
    response_model=JobMatchResult,
)
def score_job_endpoint(
    job_id: str,
) -> JobMatchResult:
    """Score one PostgreSQL job against the career profile."""

    job = db.get_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}",
        )

    profile = load_matching_profile()

    return score_job(
        job,
        profile,
    )

@app.post(
    "/jobs/{job_id}/application-pack",
)
def generate_application_pack_endpoint(
    job_id: str,
) -> dict:
    """Generate a human-review application pack for one PostgreSQL job."""

    job = db.get_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}",
        )

    pack, folder = generate_application_pack_for_job(
        job,
    )

    return {
        "job_id": str(job.job_id),
        "company": job.company,
        "role_title": job.title,
        "status": str(pack.manifest.status),
        "human_review_required": (
            pack.manifest.human_review_required
        ),
        "final_score": pack.metadata.get(
            "final_score"
        ),
        "recommendation": pack.metadata.get(
            "recommendation"
        ),
        "selected_evidence_ids": (
            pack.manifest.selected_evidence_ids
        ),
        "files": pack.manifest.files,
        "output_folder": str(folder),
    }

@app.post(
    "/jobs/ingest",
    response_model=IngestionRun,
)
def ingest_job_endpoint(
    request: JobIngestionRequest,
) -> IngestionRun:
    """Fetch, parse, normalise and store one vacancy in PostgreSQL."""

    return ingest_job_url(
        url=str(request.url),
        source=request.source,
        notes=request.notes,
        database=db,
    )
