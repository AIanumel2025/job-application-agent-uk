"""Command-line scoring pipeline for stored job vacancies."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

from src.career_data_loader import find_repository_root, load_career_data
from src.career_profile_builder import build_career_matching_profile
from src.eligibility_checker import check_eligibility
from src.experience_matcher import match_experience
from src.job_database import JobDatabase
from src.job_ranker import rank_jobs
from src.job_requirement_extractor import extract_job_requirements
from src.match_explainer import build_match_explanation
from src.match_scoring import calculate_match_score, recommendation_for
from src.matching_models import JobMatchResult
from src.salary_location_matcher import assess_preference_fit
from src.skill_matcher import match_skills


console = Console()


def _evidence_quality_score(profile) -> float:
    if not profile.evidence:
        return 0.0

    approved = [
        item
        for item in profile.evidence
        if item.approved_for_application
    ]
    verified = [
        item
        for item in approved
        if item.verified
    ]

    approval_score = len(approved) / len(profile.evidence)
    verification_score = (
        len(verified) / len(approved)
        if approved
        else 0.0
    )

    return round(
        (approval_score * 50.0) + (verification_score * 50.0),
        2,
    )


def score_stored_jobs(
    *,
    repository_root: str | Path | None = None,
    db_path: str | Path | None = None,
    json_report_path: str | Path | None = None,
    csv_report_path: str | Path | None = None,
) -> list[JobMatchResult]:
    root = (
        Path(repository_root).expanduser().resolve()
        if repository_root
        else find_repository_root(Path.cwd())
    )

    database_path = (
        Path(db_path).expanduser().resolve()
        if db_path
        else root / "data" / "jobs.db"
    )
    json_path = (
        Path(json_report_path).expanduser().resolve()
        if json_report_path
        else root / "reports" / "job_match_scores.json"
    )
    csv_path = (
        Path(csv_report_path).expanduser().resolve()
        if csv_report_path
        else root / "reports" / "ranked_jobs.csv"
    )

    bundle = load_career_data(root)
    profile = build_career_matching_profile(bundle)

    database = JobDatabase(database_path)
    database.initialise()
    jobs = database.list_jobs()

    results: list[JobMatchResult] = []
    closing_dates: dict[str, str | None] = {}

    for job in jobs:
        requirements = extract_job_requirements(job)
        skill_result = match_skills(requirements, profile)
        experience_result = match_experience(requirements, profile)
        eligibility_result = check_eligibility(
            job,
            requirements,
            profile,
        )
        preference_result = assess_preference_fit(
            job,
            profile,
        )

        score_breakdown = calculate_match_score(
            skill_result=skill_result,
            experience_result=experience_result,
            eligibility_result=eligibility_result,
            preference_result=preference_result,
            evidence_quality_score=_evidence_quality_score(profile),
        )

        recommendation = recommendation_for(
            score_breakdown.total_score,
            eligibility_result,
        )

        explanation = build_match_explanation(
            skill_result=skill_result,
            experience_result=experience_result,
            eligibility_result=eligibility_result,
            preference_result=preference_result,
            score_breakdown=score_breakdown,
        )

        hard_stops = eligibility_result.hard_stops
        blocked_reason = (
            hard_stops[0].explanation
            if hard_stops
            else None
        )

        result = JobMatchResult(
            job_id=job.job_id,
            job_title=job.title,
            company=job.company,
            application_url=job.application_url,
            requirements=requirements,
            skill_result=skill_result,
            experience_result=experience_result,
            eligibility_result=eligibility_result,
            preference_result=preference_result,
            score_breakdown=score_breakdown,
            explanation=explanation,
            recommendation=recommendation,
            final_score=score_breakdown.total_score,
            requires_manual_review=(
                str(eligibility_result.overall_status)
                in {"review_required", "unclear"}
            ),
            blocked_reason=blocked_reason,
        )

        results.append(result)
        closing_dates[str(job.job_id)] = (
            job.closing_date.isoformat()
            if job.closing_date
            else None
        )

    ranking_report = rank_jobs(
        results,
        closing_dates,
    )

    json_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    json_path.write_text(
        json.dumps(
            {
                "profile": profile.model_dump(mode="json"),
                "matches": [
                    item.model_dump(mode="json")
                    for item in results
                ],
                "ranking": ranking_report.model_dump(mode="json"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    csv_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "rank",
                "job_id",
                "job_title",
                "company",
                "final_score",
                "recommendation",
                "eligibility_status",
                "closing_date",
                "urgency_score",
                "strategic_value_score",
                "ranking_score",
            ],
        )
        writer.writeheader()

        for item in ranking_report.ranked_jobs:
            row = item.model_dump(mode="json")
            writer.writerow(
                {
                    field: row.get(field)
                    for field in writer.fieldnames
                }
            )

    return results


def print_results(
    results: list[JobMatchResult],
) -> None:
    table = Table(
        title="Job match results",
    )
    table.add_column("Company")
    table.add_column("Role")
    table.add_column(
        "Score",
        justify="right",
    )
    table.add_column("Recommendation")
    table.add_column("Eligibility")

    for result in sorted(
        results,
        key=lambda item: item.final_score,
        reverse=True,
    ):
        table.add_row(
            result.company,
            result.job_title,
            f"{result.final_score:.1f}",
            str(result.recommendation),
            str(result.eligibility_result.overall_status),
        )

    console.print(table)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Score and rank jobs stored in data/jobs.db."
    )
    parser.add_argument(
        "--root",
        dest="repository_root",
    )
    parser.add_argument(
        "--db",
        dest="db_path",
    )
    parser.add_argument(
        "--json-report",
        dest="json_report_path",
    )
    parser.add_argument(
        "--csv-report",
        dest="csv_report_path",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    results = score_stored_jobs(
        repository_root=args.repository_root,
        db_path=args.db_path,
        json_report_path=args.json_report_path,
        csv_report_path=args.csv_report_path,
    )

    if not args.quiet:
        print_results(results)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
