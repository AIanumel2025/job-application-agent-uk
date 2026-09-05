"""Discover matching vacancies and ingest them into PostgreSQL."""

from __future__ import annotations

from dataclasses import dataclass

from src.job_discovery_service import (
    DiscoveredJob,
    discover_greenhouse_jobs,
)
from src.job_ingestion_service import ingest_job_url
from src.job_models import JobSource
from src.postgres_job_database import PostgresJobDatabase


@dataclass(slots=True)
class DiscoveryIngestionResult:
    discovered: DiscoveredJob
    action: str
    job_id: str | None
    duplicate_of: str | None
    message: str | None


def discover_and_ingest_greenhouse_jobs(
    *,
    board_tokens: list[str],
    role_terms: list[str] | None = None,
    location_terms: list[str] | None = None,
    limit: int = 20,
    database: PostgresJobDatabase | None = None,
) -> list[DiscoveryIngestionResult]:
    """Discover Greenhouse vacancies and pass each through ingestion."""

    db = database or PostgresJobDatabase()
    db.initialise()

    discovered_jobs = discover_greenhouse_jobs(
        board_tokens=board_tokens,
        role_terms=role_terms or [],
        location_terms=location_terms or [],
        limit=limit,
    )

    results: list[DiscoveryIngestionResult] = []

    for discovered in discovered_jobs:
        run = ingest_job_url(
    url=discovered.url,
    source=JobSource.COMPANY_SITE,
    notes=(
        "Automatically discovered from Greenhouse "
        f"board: {discovered.company_token}"
    ),
    company_hint=discovered.company_token.replace("_", " ").title(),
    source_job_id_hint=discovered.source_job_id,
    database=db,
)

        item = run.results[0] if run.results else None

        results.append(
            DiscoveryIngestionResult(
                discovered=discovered,
                action=(
                    str(item.action)
                    if item
                    else "unknown"
                ),
                job_id=(
                    str(item.job_id)
                    if item and item.job_id
                    else None
                ),
                duplicate_of=(
                    str(item.duplicate_of)
                    if item and item.duplicate_of
                    else None
                ),
                message=(
                    item.message
                    if item
                    else "No ingestion result returned."
                ),
            )
        )

    return results
