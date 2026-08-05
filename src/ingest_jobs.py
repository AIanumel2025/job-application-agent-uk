"""Command-line job ingestion pipeline."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.table import Table

from src.job_database import JobDatabase
from src.job_deduplicator import find_duplicate
from src.job_models import (
    IngestionAction,
    IngestionItemResult,
    IngestionRun,
)
from src.job_normaliser import normalise_parsed_job
from src.job_page_fetcher import fetch_job_page
from src.job_parser import parse_job_page
from src.job_url_loader import (
    default_job_urls_path,
    find_repository_root,
    load_job_urls,
)


console = Console()


def run_ingestion(
    *,
    csv_path: str | Path | None = None,
    db_path: str | Path | None = None,
    report_path: str | Path | None = None,
    timeout_seconds: int = 20,
    max_bytes: int = 5_000_000,
) -> IngestionRun:
    """Run the complete Phase 3 ingestion pipeline."""

    root = find_repository_root()
    resolved_csv = Path(csv_path) if csv_path else default_job_urls_path(root)
    resolved_db = Path(db_path) if db_path else root / "data" / "jobs.db"
    resolved_report = (
        Path(report_path)
        if report_path
        else root / "reports" / "job_ingestion_report.json"
    )

    database = JobDatabase(resolved_db)
    database.initialise()

    load_result = load_job_urls(resolved_csv)

    run = IngestionRun(
        started_at=datetime.now(timezone.utc),
        input_count=load_result.valid_count,
    )

    for issue in load_result.issues:
        run.results.append(
            IngestionItemResult(
                input_url="https://invalid.local/",
                action=IngestionAction.FAILED,
                message=f"CSV row {issue.row_number}: {issue.message}",
                errors=[issue.code],
            )
        )

    for record in load_result.records:
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
                    errors=[f"fetch_{fetched.fetch_status}"],
                )
            )
            continue

        run.fetched_count += 1

        try:
            parsed = parse_job_page(fetched)
            run.parsed_count += 1
            normalised = normalise_parsed_job(parsed)
        except Exception as exc:
            run.results.append(
                IngestionItemResult(
                    input_url=record.url,
                    source=record.source,
                    action=IngestionAction.FAILED,
                    message=str(exc),
                    errors=["parse_or_normalise_failed"],
                )
            )
            continue

        existing_jobs = database.list_jobs()
        duplicate_result = find_duplicate(normalised, existing_jobs)

        if duplicate_result.is_duplicate and duplicate_result.best_match:
            run.results.append(
                IngestionItemResult(
                    input_url=record.url,
                    source=record.source,
                    action=IngestionAction.DUPLICATE,
                    job_id=normalised.job_id,
                    duplicate_of=duplicate_result.best_match.existing_job_id,
                    message=duplicate_result.best_match.reason,
                    warnings=[
                        "matching fields: "
                        + ", ".join(
                            duplicate_result.best_match.matching_fields
                        )
                    ],
                )
            )
            continue

        try:
            database.insert_job(normalised)
        except Exception as exc:
            run.results.append(
                IngestionItemResult(
                    input_url=record.url,
                    source=record.source,
                    action=IngestionAction.FAILED,
                    job_id=normalised.job_id,
                    message=str(exc),
                    errors=["database_insert_failed"],
                )
            )
            continue

        run.results.append(
            IngestionItemResult(
                input_url=record.url,
                source=record.source,
                action=IngestionAction.INSERTED,
                job_id=normalised.job_id,
                message=f"{normalised.title} at {normalised.company}",
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

    database.save_ingestion_run(run)

    resolved_report.parent.mkdir(parents=True, exist_ok=True)
    resolved_report.write_text(
        json.dumps(run.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    return run


def print_run_summary(run: IngestionRun) -> None:
    table = Table(title="Job ingestion summary")
    table.add_column("Metric")
    table.add_column("Count", justify="right")

    metrics = {
        "Input": run.input_count,
        "Fetched": run.fetched_count,
        "Parsed": run.parsed_count,
        "Inserted": run.inserted_count,
        "Updated": run.updated_count,
        "Duplicates": run.duplicate_count,
        "Skipped": run.skipped_count,
        "Failed": run.failed_count,
    }

    for label, count in metrics.items():
        table.add_row(label, str(count))

    console.print(table)

    for item in run.results:
        console.print(
            f"[bold]{item.action}[/bold] "
            f"{item.input_url} "
            f"{'- ' + item.message if item.message else ''}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest public job vacancy URLs into the local database."
    )
    parser.add_argument("--csv", dest="csv_path")
    parser.add_argument("--db", dest="db_path")
    parser.add_argument("--report", dest="report_path")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--max-bytes", type=int, default=5_000_000)
    parser.add_argument("--quiet", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    run = run_ingestion(
        csv_path=args.csv_path,
        db_path=args.db_path,
        report_path=args.report_path,
        timeout_seconds=args.timeout,
        max_bytes=args.max_bytes,
    )

    if not args.quiet:
        print_run_summary(run)

    return 1 if run.failed_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
