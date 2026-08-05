"""Pydantic data models for the UK Job Application Agent.

These models describe the structure of the YAML files created during Phase 1.
They perform type checking and a small number of safety validations. Loading
files from disk and cross-file validation are handled by later modules.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)


class StrictModel(BaseModel):
    """Base configuration shared by all project models."""

    model_config = ConfigDict(
        extra="allow",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class VerificationStatus(StrEnum):
    """Known evidence and verification states used by career claims."""

    VERIFIED_CREDENTIAL = "verified_credential"
    VERIFIED_CREDENTIAL_AND_USER_CONFIRMATION = (
        "verified_credential_and_user_confirmation"
    )
    VERIFIED_FROM_UPLOADED_CREDENTIAL = "verified_from_uploaded_credential"
    VERIFIED_FROM_UPLOADED_CREDENTIAL_AND_USER_CONFIRMATION = (
        "verified_from_uploaded_credential_and_user_confirmation"
    )
    SOURCE_SUPPORTED = "source_supported"
    SOURCE_SUPPORTED_NEEDS_UNDERLYING_EVIDENCE = (
        "source_supported_needs_underlying_evidence"
    )
    SOURCE_SUPPORTED_NEEDS_BASELINE_CONFIRMATION = (
        "source_supported_needs_baseline_confirmation"
    )
    NEEDS_BASELINE_DEFINITION = "needs_baseline_definition"
    NEEDS_CLARIFICATION = "needs_clarification"
    NEEDS_CONFIRMATION = "needs_confirmation"
    CONFIRMED = "confirmed"
    PROVISIONAL = "provisional"


class WorkModel(StrEnum):
    REMOTE = "Remote"
    HYBRID = "Hybrid"
    ONSITE = "Onsite"


class EmploymentType(StrEnum):
    PERMANENT = "Permanent"
    CONTRACT = "Contract"
    FIXED_TERM = "Fixed-term"
    GRADUATE = "Graduate"
    PLACEMENT = "Placement"
    INTERNSHIP = "Internship"


class SchemaMetadata(StrictModel):
    schema_version: str = Field(min_length=1)
    generated_on: date
    status: str = Field(min_length=1)


class ContactDetails(StrictModel):
    email: str = Field(min_length=3)
    phone: str | None = None
    privacy_note: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email_shape(cls, value: str) -> str:
        local, separator, domain = value.partition("@")
        if not separator or not local or "." not in domain:
            raise ValueError("email must resemble a valid email address")
        return value


class Location(StrictModel):
    city_or_area: str = Field(min_length=1)
    country: str = Field(min_length=1)
    source: str | None = None


class RightToWork(StrictModel):
    authorised_to_work_in_uk: bool
    visa_route: str | None = None
    future_sponsorship_required: bool
    review_before_submission: bool = True


class Availability(StrictModel):
    notice_period: str | None = None
    earliest_start_date: date | None = None


class CareerPreferences(StrictModel):
    primary_role: str = Field(min_length=1)
    preferred_locations: list[str] = Field(default_factory=list)
    work_model: list[WorkModel] | None = None
    employment_types: list[EmploymentType] | None = None
    minimum_salary_gbp: int | None = Field(default=None, ge=0)
    availability: Availability | None = None
    relocation: bool | None = None
    right_to_work: RightToWork | None = None
    driving_licence: str | None = None
    status: str | None = None

    @field_validator("preferred_locations")
    @classmethod
    def preferred_locations_must_not_contain_blanks(
        cls, values: list[str]
    ) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("preferred_locations cannot contain blank values")
        return values


class ProfessionalIdentity(StrictModel):
    primary_title: str = Field(min_length=1)
    headline: str | None = None
    summary: str = Field(min_length=1)
    summary_status: str | None = None


class Person(StrictModel):
    full_name: str = Field(min_length=1)
    name_variants: list[str] = Field(default_factory=list)
    location: Location
    contact: ContactDetails


class ProfileFile(SchemaMetadata):
    person: Person
    professional_identity: ProfessionalIdentity
    profiles: dict[str, HttpUrl | None] = Field(default_factory=dict)
    career_preferences: CareerPreferences
    source_files: list[str] = Field(default_factory=list)


class ClaimReference(StrictModel):
    claim_id: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    verification_status: VerificationStatus | str
    approved_for_application: bool | None = None
    reason: str | None = None
    recommended_wording: str | None = None

    @model_validator(mode="after")
    def unsafe_claim_cannot_be_approved(self) -> "ClaimReference":
        blocked_statuses = {
            VerificationStatus.NEEDS_BASELINE_DEFINITION,
            VerificationStatus.NEEDS_CLARIFICATION,
        }

        try:
            status = VerificationStatus(self.verification_status)
        except ValueError:
            return self

        if status in blocked_statuses and self.approved_for_application is True:
            raise ValueError(
                f"Claim {self.claim_id!r} has status {status.value!r} "
                "and cannot be approved for application use."
            )
        return self


class ExperienceRecord(StrictModel):
    experience_id: str = Field(min_length=1)
    employer: str = Field(min_length=1)
    role: str = Field(min_length=1)
    location: str | None = None
    employment_type: str | None = None
    start_date: str
    end_date: str | None = None
    date_precision: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    achievements: list[ClaimReference] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    related_project_ids: list[str] = Field(default_factory=list)
    source_files: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_year_month_date(cls, value: str | None) -> str | None:
        if value is None:
            return value

        parts = value.split("-")
        if len(parts) not in {1, 2, 3}:
            raise ValueError("Dates must use YYYY, YYYY-MM or YYYY-MM-DD")

        if not all(part.isdigit() for part in parts):
            raise ValueError("Dates must contain numeric components")

        year = int(parts[0])
        if year < 1900 or year > 2100:
            raise ValueError("Date year is outside the accepted range")

        if len(parts) >= 2:
            month = int(parts[1])
            if not 1 <= month <= 12:
                raise ValueError("Date month must be between 01 and 12")

        if len(parts) == 3:
            date.fromisoformat(value)

        return value


class ExperienceFile(SchemaMetadata):
    experience: list[ExperienceRecord]
    coverage_note: str | None = None


class DatasetDescription(StrictModel):
    name: str | None = None


class ProjectRecord(StrictModel):
    project_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    context: str | None = None
    status: str | None = None
    summary: str = Field(min_length=1)
    problem: str | None = None
    workflow: list[str] = Field(default_factory=list)
    architecture: list[str] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    models: list[dict[str, Any]] = Field(default_factory=list)
    dataset: dict[str, Any] | None = None
    outcomes: list[ClaimReference] = Field(default_factory=list)
    deployment: list[str] = Field(default_factory=list)
    target_roles: list[str] = Field(default_factory=list)
    repository_url: HttpUrl | None = None
    repository_visibility: str | None = None
    article_url: HttpUrl | None = None
    source_files: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class ProjectsFile(SchemaMetadata):
    projects: list[ProjectRecord]


class ThesisDetails(StrictModel):
    title: str = Field(min_length=1)
    status: str | None = None


class EducationRecord(StrictModel):
    education_id: str = Field(min_length=1)
    institution: str = Field(min_length=1)
    location: str | None = None
    qualification: str = Field(min_length=1)
    start_date: str
    end_date: str | None = None
    status: str
    classification: str | None = None
    relevant_coursework: list[str] = Field(default_factory=list)
    thesis: ThesisDetails | None = None
    source_files: list[str] = Field(default_factory=list)


class EducationFile(SchemaMetadata):
    education: list[EducationRecord]
    open_questions: list[str] = Field(default_factory=list)


class CertificationRecord(StrictModel):
    certification_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    exam_or_code: str | None = None
    earned_date: date | None = None
    expiry_date: date | None = None
    earned_date_original: str | None = None
    earned_date_interpretation: str | None = None
    credential_id: str | None = None
    certification_number: str | None = None
    course_hours: int | None = Field(default=None, ge=0)
    credential_url: HttpUrl | None = None
    local_file: str | None = None
    badge_image: str | None = None
    verification_status: VerificationStatus | str

    @model_validator(mode="after")
    def expiry_must_follow_award(self) -> "CertificationRecord":
        if (
            self.earned_date is not None
            and self.expiry_date is not None
            and self.expiry_date <= self.earned_date
        ):
            raise ValueError("expiry_date must be later than earned_date")
        return self


class CertificationsFile(SchemaMetadata):
    certifications: list[CertificationRecord]
    application_notes: list[str] = Field(default_factory=list)


class SkillItem(StrictModel):
    name: str = Field(min_length=1)
    proficiency: str | None = None
    evidence_level: str | None = None


class SkillsFile(SchemaMetadata):
    skills: dict[str, list[SkillItem]]
    usage_rules: list[str] = Field(default_factory=list)


class AchievementClaim(ClaimReference):
    category: str = Field(min_length=1)
    source_files: list[str] = Field(default_factory=list)


class AchievementPolicy(StrictModel):
    allowed_statuses: list[str] = Field(default_factory=list)
    generation_rule: str = Field(min_length=1)


class AchievementsFile(SchemaMetadata):
    claims: list[AchievementClaim]
    policy: AchievementPolicy


class ApplicationAnswer(StrictModel):
    answer: Any = None
    display_answer: str | None = None
    requires_user_input: bool
    review_before_submission: bool | None = None
    sensitivity: str | None = None
    instruction: str | None = None
    confirmed_on: date | None = None


class ApplicationAnswersFile(SchemaMetadata):
    identity: dict[str, Any]
    answers: dict[str, ApplicationAnswer]
    employment_types: dict[str, Any] | None = None
    approved_general_statements: dict[str, str] = Field(default_factory=dict)
    review_rule: str = Field(min_length=1)


class RoleTarget(StrictModel):
    title: str = Field(min_length=1)
    basis: str | None = None
    priority: int = Field(ge=1)


class RoleStrategy(StrictModel):
    primary_roles: list[RoleTarget]
    secondary_roles: list[str] = Field(default_factory=list)
    roles_to_avoid_without_strong_exception: list[str] = Field(default_factory=list)


class SeniorityPreferences(StrictModel):
    preferred: list[str] = Field(default_factory=list)
    consider_selectively: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)


class TargetRolesFile(SchemaMetadata):
    role_strategy: RoleStrategy
    seniority: SeniorityPreferences
    location_preferences: dict[str, Any]
    employment_preferences: dict[str, Any]
    search_keywords: list[str] = Field(default_factory=list)
    minimum_salary_gbp: int | None = Field(default=None, ge=0)
    sponsorship_filter: dict[str, Any] | None = None
    open_questions: list[str] = Field(default_factory=list)


class ProfileLink(StrictModel):
    url: HttpUrl | None = None
    username: str | None = None
    slug: str | None = None
    source: str | None = None
    status: str


class ProfileLinksFile(SchemaMetadata):
    owner: str = Field(min_length=1)
    profiles: dict[str, ProfileLink]


class ProjectLinkRecord(StrictModel):
    project_id: str = Field(min_length=1)
    project_name: str = Field(min_length=1)
    repository_url: HttpUrl | None = None
    repository_scope: str
    repository_path: str | None = None
    local_readme: str | None = None
    status: str
    notes: str | None = None
    article_id: str | None = None


class ProjectLinksFile(SchemaMetadata):
    owner: str = Field(min_length=1)
    github_profile: HttpUrl
    projects: list[ProjectLinkRecord]


class ArticleRecord(StrictModel):
    article_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: HttpUrl
    published_date: date | None = None
    date_status: str | None = None
    related_project_ids: list[str] = Field(default_factory=list)
    local_file: str
    topics: list[str] = Field(default_factory=list)
    status: str


class ArticleLinksFile(SchemaMetadata):
    owner: str = Field(min_length=1)
    medium_profile: HttpUrl
    articles: list[ArticleRecord]


class CertificationIndexFile(SchemaMetadata):
    owner: str = Field(min_length=1)
    certifications: list[CertificationRecord]


class CareerDataBundle(StrictModel):
    """Container returned later by the YAML loader."""

    profile: ProfileFile
    experience: ExperienceFile
    projects: ProjectsFile
    education: EducationFile
    certifications: CertificationsFile
    skills: SkillsFile
    achievements: AchievementsFile
    application_answers: ApplicationAnswersFile
    target_roles: TargetRolesFile
    profile_links: ProfileLinksFile
    project_links: ProjectLinksFile
    article_links: ArticleLinksFile
    certification_index: CertificationIndexFile
