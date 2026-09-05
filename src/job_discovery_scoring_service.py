"""Discover, ingest, score, and rank public job vacancies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.job_discovery_ingestion_service import (
    DiscoveryIngestionResult,
    discover_and_ingest_greenhouse_jobs,
)
from src.job_scoring_service import (
    load_matching_profile,
    score_job,
)
from src.postgres_job_database import PostgresJobDatabase


@dataclass(slots=True)
class RankedDiscoveredJob:
    rank: int
    job_id: str
    company: str
    title: str
    location: str | None
    url: str
    ingestion_action: str
    final_score: float
    recommendation: str
    score_details: dict[str, Any]

    # Pre-application opportunity scores.
    interview_fit_score: float | None = None
    must_have_coverage: float | None = None
    must_have_known: bool = False


def _resolve_stored_job_id(
    result: DiscoveryIngestionResult,
) -> str | None:
    """Return the PostgreSQL job ID that should be scored.

    Inserted jobs use their own job_id.

    Duplicate discovery attempts should score the already-stored job
    referenced by duplicate_of rather than the temporary incoming ID.
    """

    if result.action == "inserted":
        return result.job_id

    if result.action == "duplicate":
        return (
            result.duplicate_of
            or result.job_id
        )

    return None


def discover_ingest_score_greenhouse_jobs(
    *,
    board_tokens: list[str],
    role_terms: list[str] | None = None,
    location_terms: list[str] | None = None,
    limit: int = 20,
    shortlist_limit: int = 10,
    database: PostgresJobDatabase | None = None,
) -> list[RankedDiscoveredJob]:
    """Discover Greenhouse jobs, ingest them, score them, and rank them."""

    db = (
        database
        or PostgresJobDatabase()
    )

    db.initialise()

    profile = load_matching_profile()

    ingestion_results = discover_and_ingest_greenhouse_jobs(
        board_tokens=board_tokens,
        role_terms=role_terms or [],
        location_terms=location_terms or [],
        limit=limit,
        database=db,
    )

    scored_jobs: list[RankedDiscoveredJob] = []

    for result in ingestion_results:
        stored_job_id = _resolve_stored_job_id(
            result
        )

        if not stored_job_id:
            continue

        job = db.get_job(
            stored_job_id
        )

        if job is None:
            continue

        match = score_job(
            job,
            profile,
        )

        if hasattr(
            match,
            "model_dump",
        ):
            score_details = match.model_dump(
                mode="json"
            )
        else:
            score_details = {}

        final_score = float(
            getattr(
                match,
                "final_score",
                0.0,
            )
            or 0.0
        )

        recommendation_value = getattr(
            match,
            "recommendation",
            "",
        )

        recommendation = (
            recommendation_value.value
            if hasattr(
                recommendation_value,
                "value",
            )
            else str(
                recommendation_value
            )
        )

        location_value = None

        if job.location:
            city = getattr(
                job.location,
                "city",
                None,
            )

            region = getattr(
                job.location,
                "region",
                None,
            )

            country = getattr(
                job.location,
                "country",
                None,
            )

            location_parts = [
                str(part).strip()
                for part in (
                    city,
                    region,
                    country,
                )
                if part
            ]

            if location_parts:
                location_value = ", ".join(
                    location_parts
                )

        scored_jobs.append(
            RankedDiscoveredJob(
                rank=0,
                job_id=str(
                    job.job_id
                ),
                company=job.company,
                title=job.title,
                location=location_value,
                url=str(
                    job.application_url
                ),
                ingestion_action=result.action,
                final_score=final_score,
                recommendation=recommendation,
                score_details=score_details,
            )
        )

    scored_jobs.sort(
        key=lambda item: item.final_score,
        reverse=True,
    )

    shortlisted = scored_jobs[
        :shortlist_limit
    ]

    for index, item in enumerate(
        shortlisted,
        start=1,
    ):
        item.rank = index

    return shortlisted
