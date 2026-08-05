"""Load and validate vacancy URLs from input/job_urls.csv."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.job_models import JobInputRecord, JobSource


EXPECTED_COLUMNS = {
    "url",
    "source",
    "notes",
    "enabled",
    "added_at",
}


@dataclass(slots=True)
class JobURLLoadIssue:
    """One non-fatal problem found while reading the CSV."""

    row_number: int
    code: str
    message: str
    raw_row: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class JobURLLoadResult:
    """Structured output from loading the job URL queue."""

    records: list[JobInputRecord] = field(default_factory=list)
    issues: list[JobURLLoadIssue] = field(default_factory=list)
    total_rows: int = 0
    blank_rows: int = 0
    disabled_rows: int = 0

    @property
    def valid_count(self) -> int:
        return len(self.records)

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def passed(self) -> bool:
        return self.issue_count == 0

    def summary(self) -> dict[str, int | bool]:
        return {
            "total_rows": self.total_rows,
            "valid_records": self.valid_count,
            "blank_rows": self.blank_rows,
            "disabled_rows": self.disabled_rows,
            "issues": self.issue_count,
            "passed": self.passed,
        }


def find_repository_root(start_path: Path | None = None) -> Path:
    """Find the repository root by searching for pyproject.toml."""

    current = (start_path or Path.cwd()).resolve()

    if current.is_file():
        current = current.parent

    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate

    raise FileNotFoundError(
        "Could not locate repository root. "
        "Expected to find pyproject.toml in the current directory or a parent."
    )


def default_job_urls_path(start_path: Path | None = None) -> Path:
    """Return the expected path to input/job_urls.csv."""

    return find_repository_root(start_path) / "input" / "job_urls.csv"


def parse_boolean(value: str | None, *, default: bool = True) -> bool:
    """Parse common CSV boolean values."""

    if value is None or not value.strip():
        return default

    normalised = value.strip().lower()

    truthy = {"true", "1", "yes", "y", "on"}
    falsy = {"false", "0", "no", "n", "off"}

    if normalised in truthy:
        return True

    if normalised in falsy:
        return False

    raise ValueError(
        f"invalid boolean value: {value!r}; "
        "expected true/false, yes/no, 1/0, or on/off"
    )


def parse_optional_datetime(value: str | None) -> datetime | None:
    """Parse an optional ISO-8601 datetime."""

    if value is None or not value.strip():
        return None

    cleaned = value.strip()

    if cleaned.endswith("Z"):
        cleaned = f"{cleaned[:-1]}+00:00"

    try:
        return datetime.fromisoformat(cleaned)
    except ValueError as exc:
        raise ValueError(
            f"invalid added_at value: {value!r}; expected ISO-8601 format"
        ) from exc


def row_is_blank(row: dict[str, str | None]) -> bool:
    """Return True when every CSV cell in a row is empty."""

    return all(value is None or not value.strip() for value in row.values())


def normalise_source(value: str | None) -> JobSource:
    """Convert a CSV source label into a JobSource enum."""

    if value is None or not value.strip():
        return JobSource.MANUAL

    normalised = (
        value.strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )

    aliases = {
        "company": JobSource.COMPANY_SITE,
        "company_careers": JobSource.COMPANY_SITE,
        "employer_site": JobSource.COMPANY_SITE,
        "linkedin": JobSource.LINKEDIN_ALERT,
        "indeed": JobSource.INDEED_ALERT,
        "civil_service": JobSource.CIVIL_SERVICE_JOBS,
        "nhs": JobSource.NHS_JOBS,
    }

    if normalised in aliases:
        return aliases[normalised]

    try:
        return JobSource(normalised)
    except ValueError as exc:
        valid_values = ", ".join(source.value for source in JobSource)
        raise ValueError(
            f"unsupported source {value!r}; expected one of: {valid_values}"
        ) from exc


def _clean_cell(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()
    return cleaned or None


def _validation_error_message(exc: ValidationError) -> str:
    messages: list[str] = []

    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", ()))
        message = error.get("msg", "invalid value")

        if location:
            messages.append(f"{location}: {message}")
        else:
            messages.append(message)

    return "; ".join(messages)


def load_job_urls(csv_path: str | Path | None = None) -> JobURLLoadResult:
    """Read and validate a job URL CSV file.

    Invalid rows are reported in ``issues`` rather than raising immediately.
    Completely blank rows are ignored. Disabled rows are counted but omitted
    from the returned records.
    """

    path = Path(csv_path) if csv_path is not None else default_job_urls_path()
    path = path.expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(f"Job URL file does not exist: {path}")

    if not path.is_file():
        raise ValueError(f"Job URL path is not a file: {path}")

    result = JobURLLoadResult()

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            raise ValueError(f"CSV file has no header row: {path}")

        fieldnames = {
            field.strip() for field in reader.fieldnames if field is not None
        }

        missing_columns = EXPECTED_COLUMNS - fieldnames
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(
                f"CSV file is missing required columns: {missing}"
            )

        for row_number, raw_row in enumerate(reader, start=2):
            result.total_rows += 1

            row = {
                (key.strip() if key else ""): value
                for key, value in raw_row.items()
            }

            if row_is_blank(row):
                result.blank_rows += 1
                continue

            try:
                enabled = parse_boolean(row.get("enabled"), default=True)
            except ValueError as exc:
                result.issues.append(
                    JobURLLoadIssue(
                        row_number=row_number,
                        code="invalid_enabled_value",
                        message=str(exc),
                        raw_row=row,
                    )
                )
                continue

            if not enabled:
                result.disabled_rows += 1
                continue

            url = _clean_cell(row.get("url"))
            if url is None:
                result.issues.append(
                    JobURLLoadIssue(
                        row_number=row_number,
                        code="missing_url",
                        message="enabled row must contain a job URL",
                        raw_row=row,
                    )
                )
                continue

            try:
                source = normalise_source(row.get("source"))
            except ValueError as exc:
                result.issues.append(
                    JobURLLoadIssue(
                        row_number=row_number,
                        code="invalid_source",
                        message=str(exc),
                        raw_row=row,
                    )
                )
                continue

            try:
                added_at = parse_optional_datetime(row.get("added_at"))
            except ValueError as exc:
                result.issues.append(
                    JobURLLoadIssue(
                        row_number=row_number,
                        code="invalid_added_at",
                        message=str(exc),
                        raw_row=row,
                    )
                )
                continue

            payload: dict[str, Any] = {
                "url": url,
                "source": source,
                "notes": _clean_cell(row.get("notes")),
                "enabled": enabled,
            }

            if added_at is not None:
                payload["added_at"] = added_at

            try:
                record = JobInputRecord.model_validate(payload)
            except ValidationError as exc:
                result.issues.append(
                    JobURLLoadIssue(
                        row_number=row_number,
                        code="invalid_job_url_record",
                        message=_validation_error_message(exc),
                        raw_row=row,
                    )
                )
                continue

            result.records.append(record)

    return result


def load_enabled_job_urls(
    csv_path: str | Path | None = None,
) -> list[JobInputRecord]:
    """Convenience wrapper returning only valid, enabled records."""

    return load_job_urls(csv_path).records
