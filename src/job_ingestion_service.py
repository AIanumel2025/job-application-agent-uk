"""Reusable PostgreSQL-backed job ingestion service."""

from __future__ import annotations

from datetime import datetime, timezone

from src.job_deduplicator import find_duplicate
from src.job_models import (
    IngestionAction,
    IngestionItemResult,
    IngestionRun,
    JobInputRecord,
    JobSource,
)
from src.job_normaliser import normalise_parsed_job
from src.job_page_fetcher import fetch_job_page
from src.job_parser import parse_job_page
from src.postgres_job_database import PostgresJobDatabase


def ingest_job_url(
    *,
    url: str,
    source: JobSource = JobSource.MANUAL,
    notes: str | None = None,
    company_hint: str | None = None,
    source_job_id_hint: str | None = None,
    timeout_seconds: int = 20,
    max_bytes: int = 5_000_000,
    database: PostgresJobDatabase | None = None,
) -> IngestionRun:
    """Ingest one public vacancy URL into PostgreSQL."""

    db = database or PostgresJobDatabase()
    db.initialise()

    record = JobInputRecord(
        url=url,
        source=source,
        notes=notes,
        enabled=True,
    )

    run = IngestionRun(
        started_at=datetime.now(timezone.utc),
        input_count=1,
    )

    fetched = fetch_job_page(
        record,
        timeout_seconds=timeout_seconds,
        max_bytes=max_bytes,
    )

    if fetched.fetch_status != "success":
        run.results.append(
            IngestionItemResult(
                input_url=record.url,
                source=record.source,
                action=IngestionAction.FAILED,
                message=fetched.error_message,
                errors=[
                    f"fetch_{fetched.fetch_status}"
                ],
            )
        )

        run.completed_at = datetime.now(timezone.utc)
        run.recalculate_counts()
        db.save_ingestion_run(run)

        return run

    try:
        parsed = parse_job_page(
    fetched,
    company_hint=company_hint,
    source_job_id_hint=source_job_id_hint,
)
        normalised = normalise_parsed_job(parsed)

    except Exception as exc:
        run.results.append(
            IngestionItemResult(
                input_url=record.url,
                source=record.source,
                action=IngestionAction.FAILED,
                message=str(exc),
                errors=[
                    "parse_or_normalise_failed"
                ],
            )
        )

        run.completed_at = datetime.now(timezone.utc)
        run.recalculate_counts()
        db.save_ingestion_run(run)

        return run

    existing_jobs = db.list_jobs()

    duplicate_result = find_duplicate(
        normalised,
        existing_jobs,
    )

    if (
        duplicate_result.is_duplicate
        and duplicate_result.best_match
    ):
        run.results.append(
            IngestionItemResult(
                input_url=record.url,
                source=record.source,
                action=IngestionAction.DUPLICATE,
                job_id=normalised.job_id,
                duplicate_of=(
                    duplicate_result
                    .best_match
                    .existing_job_id
                ),
                message=(
                    duplicate_result
                    .best_match
                    .reason
                ),
                warnings=[
                    "matching fields: "
                    + ", ".join(
                        duplicate_result
                        .best_match
                        .matching_fields
                    )
                ],
            )
        )

    else:
        try:
            db.insert_job(normalised)

            run.results.append(
                IngestionItemResult(
                    input_url=record.url,
                    source=record.source,
                    action=IngestionAction.INSERTED,
                    job_id=normalised.job_id,
                    message=(
                        f"{normalised.title} "
                        f"at {normalised.company}"
                    ),
                )
            )

        except Exception as exc:
            run.results.append(
                IngestionItemResult(
                    input_url=record.url,
                    source=record.source,
                    action=IngestionAction.FAILED,
                    job_id=normalised.job_id,
                    message=str(exc),
                    errors=[
                        "database_insert_failed"
                    ],
                )
            )

    run.completed_at = datetime.now(timezone.utc)
    run.recalculate_counts()

    run.fetched_count = sum(
        1
        for item in run.results
        if item.action
        in {
            IngestionAction.INSERTED,
            IngestionAction.DUPLICATE,
        }
    )

    run.parsed_count = run.fetched_count

    db.save_ingestion_run(run)

    return run
