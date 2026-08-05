"""Command-line validation entry point for the career-data repository.

Run from the repository root with:

    python3 -m src.validate_career_data

This command:

1. Loads and validates all required YAML files.
2. Runs business and cross-file validation rules.
3. Runs the privacy and secret scanner.
4. Prints a readable terminal summary.
5. Writes reports/career_data_validation.json.
6. Exits with code 1 only when validation fails.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.text import Text

from src.career_data_loader import (
    CareerDataLoadError,
    find_repository_root,
    get_loaded_file_summary,
    load_career_data,
)
from src.privacy_scanner import (
    PrivacyFinding,
    PrivacyScanResult,
    scan_required_yaml_files,
)
from src.validation_rules import (
    Severity,
    ValidationIssue,
    ValidationResult,
    run_all_validation_rules,
)


console = Console()


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""

    parser = argparse.ArgumentParser(
        description="Validate all career-data YAML files and produce a JSON report."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help=(
            "Repository root. If omitted, the command searches upward from "
            "the current directory."
        ),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help=(
            "Optional report path. Defaults to "
            "reports/career_data_validation.json under the repository root."
        ),
    )
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=None,
        metavar="YYYY-MM-DD",
        help=(
            "Reference date for expiry checks. Defaults to today's date."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed issue tables and print only the final status.",
    )
    return parser


def resolve_repository_root(root_argument: Path | None) -> Path:
    """Resolve an explicit root or discover one automatically."""

    if root_argument is None:
        return find_repository_root()

    root = root_argument.expanduser().resolve()

    if not root.is_dir():
        raise CareerDataLoadError(
            f"Repository root does not exist or is not a directory: {root}"
        )

    return root


def issue_to_dict(issue: ValidationIssue) -> dict[str, Any]:
    return {
        "code": issue.code,
        "severity": issue.severity.value,
        "message": issue.message,
        "file_name": issue.file_name,
        "field_path": issue.field_path,
        "record_id": issue.record_id,
    }


def privacy_finding_to_dict(finding: PrivacyFinding) -> dict[str, Any]:
    return {
        "code": finding.code,
        "severity": finding.severity.value,
        "message": finding.message,
        "file_path": finding.file_path,
        "line_number": finding.line_number,
        "matched_preview": finding.matched_preview,
    }


def determine_overall_status(
    validation: ValidationResult,
    privacy: PrivacyScanResult,
) -> str:
    """Combine structural and privacy outcomes into one final status."""

    if not validation.passed or not privacy.passed:
        return "failed"

    if validation.warnings or privacy.warnings:
        return "passed_with_warnings"

    return "passed"


def build_report(
    *,
    repository_root: Path,
    file_summary: dict[str, int],
    validation: ValidationResult,
    privacy: PrivacyScanResult,
    as_of: date,
) -> dict[str, Any]:
    """Create the machine-readable validation report."""

    overall_status = determine_overall_status(validation, privacy)

    approved_claims = 0
    review_claims = 0
    blocked_claims = 0

    for issue in validation.issues:
        if issue.code == "blocked_claim":
            blocked_claims += 1
        elif issue.code == "claim_requires_review":
            review_claims += 1

    total_claims = file_summary.get("achievement_claims", 0)
    approved_claims = max(
        total_claims - review_claims - blocked_claims,
        0,
    )

    return {
        "report_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository_root": str(repository_root),
        "as_of_date": as_of.isoformat(),
        "status": overall_status,
        "summary": {
            **file_summary,
            "validation_errors": len(validation.errors),
            "validation_warnings": len(validation.warnings),
            "validation_infos": len(validation.infos),
            "privacy_critical": len(privacy.critical),
            "privacy_warnings": len(privacy.warnings),
            "privacy_infos": len(privacy.infos),
            "approved_claims_estimate": approved_claims,
            "review_claims": review_claims,
            "blocked_claims": blocked_claims,
        },
        "validation": {
            "status": validation.status,
            "issues": [
                issue_to_dict(issue)
                for issue in validation.issues
            ],
        },
        "privacy": {
            "status": privacy.status,
            "findings": [
                privacy_finding_to_dict(finding)
                for finding in privacy.findings
            ],
        },
    }


def write_report(
    report: dict[str, Any],
    report_path: Path,
) -> None:
    """Write the JSON report atomically."""

    report_path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = report_path.with_suffix(
        report_path.suffix + ".tmp"
    )

    temporary_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    temporary_path.replace(report_path)


def print_header() -> None:
    console.print()
    console.print(
        "[bold]CAREER DATA VALIDATION[/bold]"
    )
    console.print("=" * 42)


def print_file_summary(summary: dict[str, int]) -> None:
    table = Table(
        title="Loaded career data",
        show_header=False,
        box=None,
    )
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    labels = {
        "yaml_files": "YAML files loaded",
        "experience_records": "Experience records",
        "projects": "Projects",
        "education_records": "Education records",
        "certifications": "Certifications",
        "achievement_claims": "Achievement claims",
        "articles": "Articles",
        "project_links": "Project links",
    }

    for key, value in summary.items():
        table.add_row(labels.get(key, key), str(value))

    console.print(table)


def print_validation_table(validation: ValidationResult) -> None:
    if not validation.issues:
        console.print("[green]No validation issues found.[/green]")
        return

    table = Table(
        title="Business and cross-file validation",
        show_lines=False,
    )
    table.add_column("Level", width=9)
    table.add_column("Code", style="cyan")
    table.add_column("Record")
    table.add_column("Message")

    severity_styles = {
        Severity.ERROR: "bold red",
        Severity.WARNING: "yellow",
        Severity.INFO: "blue",
    }

    for issue in validation.issues:
        record = issue.record_id or issue.file_name or "-"
        table.add_row(
            Text(issue.severity.value.upper(), style=severity_styles[issue.severity]),
            issue.code,
            record,
            issue.message,
        )

    console.print(table)


def print_privacy_table(privacy: PrivacyScanResult) -> None:
    if not privacy.findings:
        console.print("[green]No privacy findings detected.[/green]")
        return

    table = Table(
        title="Privacy and secret scan",
        show_lines=False,
    )
    table.add_column("Level", width=9)
    table.add_column("Code", style="cyan")
    table.add_column("Location")
    table.add_column("Message")

    severity_styles = {
        "critical": "bold red",
        "warning": "yellow",
        "info": "blue",
    }

    for finding in privacy.findings:
        location = finding.file_path
        if finding.line_number is not None:
            location += f":{finding.line_number}"

        table.add_row(
            Text(
                finding.severity.value.upper(),
                style=severity_styles[finding.severity.value],
            ),
            finding.code,
            location,
            finding.message,
        )

    console.print(table)


def print_final_status(
    *,
    overall_status: str,
    validation: ValidationResult,
    privacy: PrivacyScanResult,
    report_path: Path,
) -> None:
    console.print()
    console.print(
        f"Validation errors:  {len(validation.errors)}"
    )
    console.print(
        f"Validation warnings:{len(validation.warnings):>3}"
    )
    console.print(
        f"Privacy critical:   {len(privacy.critical)}"
    )
    console.print(
        f"Privacy warnings:   {len(privacy.warnings)}"
    )
    console.print(f"Report: {report_path}")

    if overall_status == "failed":
        console.print("\n[bold red]RESULT: FAILED[/bold red]")
    elif overall_status == "passed_with_warnings":
        console.print(
            "\n[bold yellow]RESULT: PASSED WITH WARNINGS[/bold yellow]"
        )
    else:
        console.print("\n[bold green]RESULT: PASSED[/bold green]")


def print_loader_failure(
    error: Exception,
    *,
    report_path: Path | None = None,
) -> None:
    console.print()
    console.print("[bold red]CAREER DATA VALIDATION FAILED[/bold red]")
    console.print(str(error))

    if report_path is not None:
        failure_report = {
            "report_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "failed",
            "loader_error": str(error),
        }

        try:
            write_report(failure_report, report_path)
            console.print(f"Failure report: {report_path}")
        except OSError:
            pass


def main(argv: list[str] | None = None) -> int:
    """Run the complete validation workflow."""

    parser = build_parser()
    arguments = parser.parse_args(argv)

    report_path: Path | None = None

    try:
        repository_root = resolve_repository_root(arguments.root)

        if arguments.report is None:
            report_path = (
                repository_root
                / "reports"
                / "career_data_validation.json"
            )
        else:
            report_path = arguments.report.expanduser()
            if not report_path.is_absolute():
                report_path = repository_root / report_path
            report_path = report_path.resolve()

        reference_date = arguments.as_of or date.today()

        bundle = load_career_data(repository_root)
        file_summary = get_loaded_file_summary(bundle)

        validation = run_all_validation_rules(
            bundle,
            as_of=reference_date,
        )
        privacy = scan_required_yaml_files(repository_root)

        overall_status = determine_overall_status(
            validation,
            privacy,
        )

        report = build_report(
            repository_root=repository_root,
            file_summary=file_summary,
            validation=validation,
            privacy=privacy,
            as_of=reference_date,
        )
        write_report(report, report_path)

        print_header()
        print_file_summary(file_summary)

        if not arguments.quiet:
            console.print()
            print_validation_table(validation)
            console.print()
            print_privacy_table(privacy)

        print_final_status(
            overall_status=overall_status,
            validation=validation,
            privacy=privacy,
            report_path=report_path,
        )

        return 1 if overall_status == "failed" else 0

    except (CareerDataLoadError, OSError, ValueError) as exc:
        print_loader_failure(
            exc,
            report_path=report_path,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
