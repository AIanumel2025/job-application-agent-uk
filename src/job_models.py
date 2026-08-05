"""Pydantic models for UK job vacancy ingestion."""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import StrEnum
from hashlib import sha256
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class JobModel(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )


class JobSource(StrEnum):
    COMPANY_SITE = "company_site"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    WORKABLE = "workable"
    ASHBY = "ashby"
    SMARTRECRUITERS = "smartrecruiters"
    LINKEDIN_ALERT = "linkedin_alert"
    INDEED_ALERT = "indeed_alert"
    REED = "reed"
    TOTALJOBS = "totaljobs"
    CIVIL_SERVICE_JOBS = "civil_service_jobs"
    NHS_JOBS = "nhs_jobs"
    MANUAL = "manual"
    OTHER = "other"


class EmploymentType(StrEnum):
    PERMANENT = "Permanent"
    CONTRACT = "Contract"
    FIXED_TERM = "Fixed-term"
    TEMPORARY = "Temporary"
    INTERNSHIP = "Internship"
    PLACEMENT = "Placement"
    GRADUATE = "Graduate"
    APPRENTICESHIP = "Apprenticeship"
    PART_TIME = "Part-time"
    FULL_TIME = "Full-time"
    UNKNOWN = "Unknown"


class WorkModel(StrEnum):
    REMOTE = "Remote"
    HYBRID = "Hybrid"
    ONSITE = "Onsite"
    FLEXIBLE = "Flexible"
    UNKNOWN = "Unknown"


class SponsorshipStatus(StrEnum):
    CONFIRMED = "confirmed"
    LIKELY = "likely"
    UNCLEAR = "unclear"
    EXPLICITLY_UNAVAILABLE = "explicitly_unavailable"
    SECURITY_RESTRICTED = "security_restricted"


class JobStatus(StrEnum):
    NEW = "new"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    SKIPPED = "skipped"
    PREPARING = "preparing"
    READY_TO_APPLY = "ready_to_apply"
    APPLIED = "applied"
    ASSESSMENT = "assessment"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    CLOSED = "closed"
    EXPIRED = "expired"


class FetchStatus(StrEnum):
    NOT_ATTEMPTED = "not_attempted"
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"
    UNSUPPORTED = "unsupported"


class ParseStatus(StrEnum):
    NOT_ATTEMPTED = "not_attempted"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class IngestionAction(StrEnum):
    INSERTED = "inserted"
    UPDATED = "updated"
    DUPLICATE = "duplicate"
    SKIPPED = "skipped"
    FAILED = "failed"


class CurrencyCode(StrEnum):
    GBP = "GBP"
    USD = "USD"
    EUR = "EUR"
    UNKNOWN = "UNKNOWN"


def canonicalise_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    netloc = f"{hostname}:{parsed.port}" if parsed.port else hostname
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")

    tracking_prefixes = ("utm_",)
    tracking_names = {
        "fbclid", "gclid", "msclkid", "ref", "referrer",
        "source", "trk", "trackingid",
    }
    cleaned_query = [
        (key, val)
        for key, val in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith(tracking_prefixes)
        and key.lower() not in tracking_names
    ]
    cleaned_query.sort()
    return urlunsplit((scheme, netloc, path, urlencode(cleaned_query), ""))


class SalaryRange(JobModel):
    minimum: int | None = Field(default=None, ge=0)
    maximum: int | None = Field(default=None, ge=0)
    currency: CurrencyCode = CurrencyCode.GBP
    period: str = "annual"
    raw_text: str | None = None
    is_estimated: bool = False

    @model_validator(mode="after")
    def maximum_must_not_be_below_minimum(self) -> "SalaryRange":
        if self.minimum is not None and self.maximum is not None and self.maximum < self.minimum:
            raise ValueError("salary maximum cannot be below salary minimum")
        return self


class JobLocation(JobModel):
    raw_text: str | None = None
    city: str | None = None
    region: str | None = None
    country: str = "United Kingdom"
    postcode: str | None = None
    work_model: WorkModel = WorkModel.UNKNOWN
    remote_restriction: str | None = None


class JobInputRecord(JobModel):
    url: HttpUrl
    source: JobSource = JobSource.MANUAL
    notes: str | None = None
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    enabled: bool = True

    @field_validator("url")
    @classmethod
    def url_must_be_http_or_https(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme not in {"http", "https"}:
            raise ValueError("job URL must use HTTP or HTTPS")
        return value


class FetchedJobPage(JobModel):
    requested_url: HttpUrl
    final_url: HttpUrl | None = None
    source: JobSource
    fetch_status: FetchStatus = FetchStatus.NOT_ATTEMPTED
    status_code: int | None = Field(default=None, ge=100, le=599)
    content_type: str | None = None
    html: str | None = None
    fetched_at: datetime | None = None
    elapsed_ms: int | None = Field(default=None, ge=0)
    error_message: str | None = None

    @model_validator(mode="after")
    def successful_fetch_requires_content(self) -> "FetchedJobPage":
        if self.fetch_status == FetchStatus.SUCCESS:
            if self.status_code is None:
                raise ValueError("successful fetch requires an HTTP status code")
            if not self.html:
                raise ValueError("successful fetch requires non-empty HTML")
        return self


class ParsedJobRecord(JobModel):
    source: JobSource
    source_job_id: str | None = None
    application_url: HttpUrl
    canonical_url: str | None = None
    title: str = Field(min_length=1)
    company: str = Field(min_length=1)
    location_text: str | None = None
    salary_text: str | None = None
    employment_type_text: str | None = None
    work_model_text: str | None = None
    sponsorship_text: str | None = None
    description: str = Field(min_length=1)
    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    posted_date: date | None = None
    closing_date: date | None = None
    recruiter_name: str | None = None
    recruiter_email: str | None = None
    parse_status: ParseStatus = ParseStatus.SUCCESS
    parser_name: str | None = None
    raw_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("responsibilities", "requirements", "preferred_skills", "benefits")
    @classmethod
    def remove_blank_list_items(cls, values: list[str]) -> list[str]:
        return [value.strip() for value in values if value.strip()]

    @model_validator(mode="after")
    def closing_date_must_not_precede_posting_date(self) -> "ParsedJobRecord":
        if self.posted_date and self.closing_date and self.closing_date < self.posted_date:
            raise ValueError("closing_date cannot be earlier than posted_date")
        return self


class NormalisedJob(JobModel):
    job_id: UUID = Field(default_factory=uuid4)
    source: JobSource
    source_job_id: str | None = None
    application_url: HttpUrl
    canonical_url: str
    title: str = Field(min_length=1)
    title_normalised: str = Field(min_length=1)
    company: str = Field(min_length=1)
    company_normalised: str = Field(min_length=1)
    location: JobLocation = Field(default_factory=JobLocation)
    salary: SalaryRange | None = None
    employment_types: list[EmploymentType] = Field(default_factory=list)
    sponsorship_status: SponsorshipStatus = SponsorshipStatus.UNCLEAR
    sponsorship_evidence: list[str] = Field(default_factory=list)
    description: str = Field(min_length=1)
    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    posted_date: date | None = None
    closing_date: date | None = None
    date_found: date = Field(default_factory=date.today)
    status: JobStatus = JobStatus.NEW
    description_hash: str | None = None
    deduplication_key: str | None = None
    recruiter_name: str | None = None
    recruiter_email: str | None = None
    raw_source_data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("employment_types", mode="before")
    @classmethod
    def deduplicate_employment_types(cls, values):
        if not values:
            return []
        seen = set()
        output = []
        for value in values:
            key = str(value)
            if key not in seen:
                output.append(value)
                seen.add(key)
        return output

    @model_validator(mode="before")
    @classmethod
    def populate_derived_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        application_url = data.get("application_url")
        if application_url and not data.get("canonical_url"):
            data["canonical_url"] = canonicalise_url(str(application_url))

        description = data.get("description")
        if description and not data.get("description_hash"):
            normalised_description = " ".join(str(description).split()).lower()
            data["description_hash"] = sha256(
                normalised_description.encode("utf-8")
            ).hexdigest()

        title = data.get("title_normalised") or data.get("title")
        company = data.get("company_normalised") or data.get("company")
        canonical_url = data.get("canonical_url")
        if title and company and canonical_url and not data.get("deduplication_key"):
            key_material = "|".join([
                " ".join(str(company).lower().split()),
                " ".join(str(title).lower().split()),
                str(canonical_url).lower(),
            ])
            data["deduplication_key"] = sha256(
                key_material.encode("utf-8")
            ).hexdigest()

        return data

    @model_validator(mode="after")
    def validate_dates_and_sponsorship(self) -> "NormalisedJob":
        if self.posted_date and self.closing_date and self.closing_date < self.posted_date:
            raise ValueError("closing_date cannot be earlier than posted_date")

        if (
            self.sponsorship_status
            in {
                SponsorshipStatus.CONFIRMED,
                SponsorshipStatus.EXPLICITLY_UNAVAILABLE,
                SponsorshipStatus.SECURITY_RESTRICTED,
            }
            and not self.sponsorship_evidence
        ):
            raise ValueError("definitive sponsorship classifications require evidence")
        return self


class DuplicateMatch(JobModel):
    incoming_job_id: UUID
    existing_job_id: UUID
    reason: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    matching_fields: list[str] = Field(default_factory=list)


class IngestionItemResult(JobModel):
    input_url: HttpUrl
    action: IngestionAction
    job_id: UUID | None = None
    source: JobSource | None = None
    message: str | None = None
    duplicate_of: UUID | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class IngestionRun(JobModel):
    run_id: UUID = Field(default_factory=uuid4)
    started_at: datetime
    completed_at: datetime | None = None
    input_count: int = Field(default=0, ge=0)
    fetched_count: int = Field(default=0, ge=0)
    parsed_count: int = Field(default=0, ge=0)
    inserted_count: int = Field(default=0, ge=0)
    updated_count: int = Field(default=0, ge=0)
    duplicate_count: int = Field(default=0, ge=0)
    skipped_count: int = Field(default=0, ge=0)
    failed_count: int = Field(default=0, ge=0)
    results: list[IngestionItemResult] = Field(default_factory=list)

    @model_validator(mode="after")
    def completed_run_must_have_valid_timing(self) -> "IngestionRun":
        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError("completed_at cannot be earlier than started_at")
        return self

    def recalculate_counts(self) -> None:
        self.input_count = len(self.results)
        self.inserted_count = sum(
            item.action == IngestionAction.INSERTED for item in self.results
        )
        self.updated_count = sum(
            item.action == IngestionAction.UPDATED for item in self.results
        )
        self.duplicate_count = sum(
            item.action == IngestionAction.DUPLICATE for item in self.results
        )
        self.skipped_count = sum(
            item.action == IngestionAction.SKIPPED for item in self.results
        )
        self.failed_count = sum(
            item.action == IngestionAction.FAILED for item in self.results
        )
