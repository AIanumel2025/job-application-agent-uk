"""Business and cross-file validation rules for career data.

Pydantic validates field types and basic constraints. This module validates
relationships and project-specific rules across the complete CareerDataBundle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Iterable
from urllib.parse import urlsplit

from src.models import CareerDataBundle, VerificationStatus


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class ValidationIssue:
    """One validation result produced by a rule."""

    code: str
    severity: Severity
    message: str
    file_name: str | None = None
    field_path: str | None = None
    record_id: str | None = None


@dataclass
class ValidationResult:
    """Aggregate results from all validation rules."""

    issues: list[ValidationIssue] = field(default_factory=list)

    def add(
        self,
        code: str,
        severity: Severity,
        message: str,
        *,
        file_name: str | None = None,
        field_path: str | None = None,
        record_id: str | None = None,
    ) -> None:
        self.issues.append(
            ValidationIssue(
                code=code,
                severity=severity,
                message=message,
                file_name=file_name,
                field_path=field_path,
                record_id=record_id,
            )
        )

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [
            issue for issue in self.issues
            if issue.severity == Severity.WARNING
        ]

    @property
    def infos(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == Severity.INFO]

    @property
    def passed(self) -> bool:
        return not self.errors

    @property
    def status(self) -> str:
        if self.errors:
            return "failed"
        if self.warnings:
            return "passed_with_warnings"
        return "passed"

    def summary(self) -> dict[str, int | str]:
        return {
            "status": self.status,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "infos": len(self.infos),
            "total_issues": len(self.issues),
        }


def _find_duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()

    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)

    return duplicates


def _normalise_url(value: object) -> str | None:
    if value is None:
        return None
    return str(value).rstrip("/")


def _url_is_http(value: str) -> bool:
    parsed = urlsplit(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_unique_ids(
    bundle: CareerDataBundle,
    result: ValidationResult,
) -> None:
    """Check all record identifiers that must be unique within their files."""

    groups = {
        "experience.yaml": [
            record.experience_id
            for record in bundle.experience.experience
        ],
        "projects.yaml": [
            record.project_id
            for record in bundle.projects.projects
        ],
        "education.yaml": [
            record.education_id
            for record in bundle.education.education
        ],
        "certifications.yaml": [
            record.certification_id
            for record in bundle.certifications.certifications
        ],
        "achievements.yaml": [
            record.claim_id
            for record in bundle.achievements.claims
        ],
        "article_links.yaml": [
            record.article_id
            for record in bundle.article_links.articles
        ],
        "project_links.yaml": [
            record.project_id
            for record in bundle.project_links.projects
        ],
        "certification_index.yaml": [
            record.certification_id
            for record in bundle.certification_index.certifications
        ],
    }

    for file_name, identifiers in groups.items():
        for duplicate in sorted(_find_duplicates(identifiers)):
            result.add(
                "duplicate_id",
                Severity.ERROR,
                f"Duplicate identifier found: {duplicate}",
                file_name=file_name,
                record_id=duplicate,
            )


def validate_claim_references(
    bundle: CareerDataBundle,
    result: ValidationResult,
) -> None:
    """Ensure all project and experience claims exist in achievements.yaml."""

    known_claims = {
        claim.claim_id: claim
        for claim in bundle.achievements.claims
    }

    references: list[tuple[str, str, str]] = []

    for project in bundle.projects.projects:
        for outcome in project.outcomes:
            references.append(
                ("projects.yaml", project.project_id, outcome.claim_id)
            )

    for experience in bundle.experience.experience:
        for achievement in experience.achievements:
            references.append(
                ("experience.yaml", experience.experience_id, achievement.claim_id)
            )

    for file_name, record_id, claim_id in references:
        if claim_id not in known_claims:
            result.add(
                "missing_claim_reference",
                Severity.ERROR,
                f"Referenced claim does not exist in achievements.yaml: {claim_id}",
                file_name=file_name,
                record_id=record_id,
                field_path="outcomes_or_achievements",
            )

    referenced_claim_ids = {claim_id for _, _, claim_id in references}
    for claim_id in sorted(set(known_claims) - referenced_claim_ids):
        result.add(
            "unreferenced_claim",
            Severity.INFO,
            f"Claim is not currently referenced by an experience or project record: {claim_id}",
            file_name="achievements.yaml",
            record_id=claim_id,
        )


def validate_project_references(
    bundle: CareerDataBundle,
    result: ValidationResult,
) -> None:
    """Ensure project IDs referenced by articles and experience records exist."""

    known_projects = {
        project.project_id
        for project in bundle.projects.projects
    }

    for article in bundle.article_links.articles:
        for project_id in article.related_project_ids:
            if project_id not in known_projects:
                result.add(
                    "missing_project_reference",
                    Severity.ERROR,
                    f"Article references an unknown project: {project_id}",
                    file_name="article_links.yaml",
                    record_id=article.article_id,
                    field_path="related_project_ids",
                )

    for experience in bundle.experience.experience:
        for project_id in experience.related_project_ids:
            if project_id not in known_projects:
                result.add(
                    "missing_project_reference",
                    Severity.ERROR,
                    f"Experience record references an unknown project: {project_id}",
                    file_name="experience.yaml",
                    record_id=experience.experience_id,
                    field_path="related_project_ids",
                )


def validate_project_link_consistency(
    bundle: CareerDataBundle,
    result: ValidationResult,
) -> None:
    """Compare project records with the project-link index."""

    projects = {
        project.project_id: project
        for project in bundle.projects.projects
    }
    links = {
        link.project_id: link
        for link in bundle.project_links.projects
    }

    for project_id in sorted(set(projects) - set(links)):
        result.add(
            "missing_project_link_entry",
            Severity.WARNING,
            f"Project has no matching entry in project_links.yaml: {project_id}",
            file_name="projects.yaml",
            record_id=project_id,
        )

    for project_id in sorted(set(links) - set(projects)):
        result.add(
            "orphan_project_link_entry",
            Severity.ERROR,
            f"project_links.yaml refers to an unknown project: {project_id}",
            file_name="project_links.yaml",
            record_id=project_id,
        )

    for project_id in sorted(set(projects) & set(links)):
        project_url = _normalise_url(projects[project_id].repository_url)
        link_url = _normalise_url(links[project_id].repository_url)

        if project_url != link_url:
            result.add(
                "repository_url_mismatch",
                Severity.ERROR,
                (
                    "Repository URL differs between projects.yaml and "
                    f"project_links.yaml for {project_id}"
                ),
                file_name="project_links.yaml",
                record_id=project_id,
                field_path="repository_url",
            )


def validate_certification_consistency(
    bundle: CareerDataBundle,
    result: ValidationResult,
) -> None:
    """Compare the career certification file with its source index."""

    career = {
        cert.certification_id: cert
        for cert in bundle.certifications.certifications
    }
    index = {
        cert.certification_id: cert
        for cert in bundle.certification_index.certifications
    }

    for certification_id in sorted(set(career) - set(index)):
        result.add(
            "missing_certification_index_entry",
            Severity.ERROR,
            f"Certification is missing from certification_index.yaml: {certification_id}",
            file_name="certifications.yaml",
            record_id=certification_id,
        )

    for certification_id in sorted(set(index) - set(career)):
        result.add(
            "orphan_certification_index_entry",
            Severity.ERROR,
            f"Certification index refers to an unknown career certification: {certification_id}",
            file_name="certification_index.yaml",
            record_id=certification_id,
        )

    comparable_fields = (
        "name",
        "provider",
        "earned_date",
        "expiry_date",
        "credential_id",
        "certification_number",
        "credential_url",
    )

    for certification_id in sorted(set(career) & set(index)):
        left = career[certification_id]
        right = index[certification_id]

        for field_name in comparable_fields:
            left_value = getattr(left, field_name)
            right_value = getattr(right, field_name)

            if _normalise_url(left_value) != _normalise_url(right_value):
                result.add(
                    "certification_mismatch",
                    Severity.ERROR,
                    (
                        f"Field {field_name!r} differs between certifications.yaml "
                        "and certification_index.yaml"
                    ),
                    file_name="certification_index.yaml",
                    record_id=certification_id,
                    field_path=field_name,
                )


def validate_claim_safety(
    bundle: CareerDataBundle,
    result: ValidationResult,
) -> None:
    """Classify claims and ensure unsafe claims are not approved."""

    blocked_statuses = {
        VerificationStatus.NEEDS_CLARIFICATION.value,
        VerificationStatus.NEEDS_BASELINE_DEFINITION.value,
    }

    review_statuses = {
        VerificationStatus.SOURCE_SUPPORTED_NEEDS_UNDERLYING_EVIDENCE.value,
        VerificationStatus.SOURCE_SUPPORTED_NEEDS_BASELINE_CONFIRMATION.value,
        VerificationStatus.NEEDS_CONFIRMATION.value,
        VerificationStatus.PROVISIONAL.value,
    }

    for claim in bundle.achievements.claims:
        status = str(claim.verification_status)

        if status in blocked_statuses:
            if claim.approved_for_application:
                result.add(
                    "blocked_claim_approved",
                    Severity.ERROR,
                    "A blocked claim is marked as approved for application use.",
                    file_name="achievements.yaml",
                    record_id=claim.claim_id,
                    field_path="approved_for_application",
                )
            else:
                result.add(
                    "blocked_claim",
                    Severity.WARNING,
                    f"Claim is blocked from use pending clarification: {claim.statement}",
                    file_name="achievements.yaml",
                    record_id=claim.claim_id,
                )

        elif status in review_statuses:
            result.add(
                "claim_requires_review",
                Severity.WARNING,
                f"Claim requires evidence or review before strong use: {claim.statement}",
                file_name="achievements.yaml",
                record_id=claim.claim_id,
            )

        elif claim.approved_for_application is not True:
            result.add(
                "verified_claim_not_approved",
                Severity.WARNING,
                "A verified or source-supported claim is not approved for application use.",
                file_name="achievements.yaml",
                record_id=claim.claim_id,
            )


def validate_confidential_projects(
    bundle: CareerDataBundle,
    result: ValidationResult,
) -> None:
    """Enforce repository and source rules for confidential or private work."""

    confidential_terms = {
        "confidential",
        "nda",
        "not_shareable_due_to_nda",
        "confidential_not_shareable_due_to_nda",
    }

    for project in bundle.projects.projects:
        visibility = (project.repository_visibility or "").lower()
        status = (project.status or "").lower()

        is_confidential = any(
            term in visibility or term in status
            for term in confidential_terms
        )

        if is_confidential and project.repository_url is not None:
            result.add(
                "confidential_repository_exposed",
                Severity.ERROR,
                "Confidential or NDA-covered project contains a repository URL.",
                file_name="projects.yaml",
                record_id=project.project_id,
                field_path="repository_url",
            )

    for project_link in bundle.project_links.projects:
        status = project_link.status.lower()
        scope = project_link.repository_scope.lower()

        is_confidential = any(
            term in status or term in scope
            for term in confidential_terms
        )

        if is_confidential and project_link.repository_url is not None:
            result.add(
                "confidential_repository_exposed",
                Severity.ERROR,
                "Confidential or NDA-covered project link contains a repository URL.",
                file_name="project_links.yaml",
                record_id=project_link.project_id,
                field_path="repository_url",
            )


def validate_dates_and_expiry(
    bundle: CareerDataBundle,
    result: ValidationResult,
    *,
    as_of: date | None = None,
) -> None:
    """Check chronological consistency and certification expiry."""

    reference_date = as_of or date.today()

    for certification in bundle.certifications.certifications:
        if (
            certification.expiry_date is not None
            and certification.expiry_date < reference_date
        ):
            result.add(
                "expired_certification",
                Severity.WARNING,
                (
                    f"Certification expired on {certification.expiry_date.isoformat()}: "
                    f"{certification.name}"
                ),
                file_name="certifications.yaml",
                record_id=certification.certification_id,
                field_path="expiry_date",
            )

    for education in bundle.education.education:
        if (
            education.start_date
            and education.end_date
            and education.start_date > education.end_date
        ):
            result.add(
                "education_date_order",
                Severity.ERROR,
                "Education start date occurs after end date.",
                file_name="education.yaml",
                record_id=education.education_id,
            )

    for experience in bundle.experience.experience:
        if (
            experience.start_date
            and experience.end_date
            and experience.start_date > experience.end_date
        ):
            result.add(
                "experience_date_order",
                Severity.ERROR,
                "Experience start date occurs after end date.",
                file_name="experience.yaml",
                record_id=experience.experience_id,
            )


def validate_application_answers(
    bundle: CareerDataBundle,
    result: ValidationResult,
) -> None:
    """Check the minimum set of answers needed for later application generation."""

    required_answers = {
        "right_to_work_in_uk",
        "requires_current_or_future_sponsorship",
        "notice_period",
        "earliest_start_date",
        "salary_expectation_gbp",
        "willing_to_relocate",
        "remote_hybrid_onsite_preference",
        "preferred_locations",
    }

    actual = set(bundle.application_answers.answers)
    missing = sorted(required_answers - actual)

    for key in missing:
        result.add(
            "missing_application_answer",
            Severity.ERROR,
            f"Required application answer is missing: {key}",
            file_name="application_answers.yaml",
            record_id=key,
        )

    for key in sorted(required_answers & actual):
        answer = bundle.application_answers.answers[key]

        if answer.answer is None:
            result.add(
                "empty_application_answer",
                Severity.ERROR,
                f"Required application answer has no value: {key}",
                file_name="application_answers.yaml",
                record_id=key,
                field_path="answer",
            )

        if answer.requires_user_input:
            result.add(
                "application_answer_needs_input",
                Severity.WARNING,
                f"Application answer still requires user input: {key}",
                file_name="application_answers.yaml",
                record_id=key,
            )

    sensitive_keys = {
        "right_to_work_in_uk",
        "requires_current_or_future_sponsorship",
        "salary_expectation_gbp",
    }

    for key in sorted(sensitive_keys & actual):
        answer = bundle.application_answers.answers[key]

        if answer.review_before_submission is not True:
            result.add(
                "sensitive_answer_not_reviewed",
                Severity.ERROR,
                (
                    "Sensitive application answer must require review before "
                    f"submission: {key}"
                ),
                file_name="application_answers.yaml",
                record_id=key,
                field_path="review_before_submission",
            )


def validate_salary_consistency(
    bundle: CareerDataBundle,
    result: ValidationResult,
) -> None:
    """Check salary values across profile, targets, and application answers."""

    profile_salary = bundle.profile.career_preferences.minimum_salary_gbp
    target_salary = bundle.target_roles.minimum_salary_gbp

    salary_answer = bundle.application_answers.answers.get(
        "salary_expectation_gbp"
    )

    answer_salary: int | None = None
    if salary_answer and isinstance(salary_answer.answer, dict):
        raw_minimum = salary_answer.answer.get("minimum")
        if isinstance(raw_minimum, int):
            answer_salary = raw_minimum

    values = {
        "profile.yaml": profile_salary,
        "target_roles.yaml": target_salary,
        "application_answers.yaml": answer_salary,
    }

    populated = {name: value for name, value in values.items() if value is not None}

    if len(set(populated.values())) > 1:
        result.add(
            "salary_mismatch",
            Severity.ERROR,
            f"Minimum salary values are inconsistent: {populated}",
            field_path="minimum_salary_gbp",
        )


def validate_urls(
    bundle: CareerDataBundle,
    result: ValidationResult,
) -> None:
    """Perform an additional lightweight HTTP/HTTPS URL check."""

    urls: list[tuple[str, str, str | None]] = []

    for name, value in bundle.profile.profiles.items():
        if value is not None:
            urls.append(("profile.yaml", str(value), name))

    for project in bundle.projects.projects:
        if project.repository_url is not None:
            urls.append(
                ("projects.yaml", str(project.repository_url), project.project_id)
            )
        if project.article_url is not None:
            urls.append(
                ("projects.yaml", str(project.article_url), project.project_id)
            )

    for article in bundle.article_links.articles:
        urls.append(
            ("article_links.yaml", str(article.url), article.article_id)
        )

    for file_name, value, record_id in urls:
        if not _url_is_http(value):
            result.add(
                "invalid_http_url",
                Severity.ERROR,
                f"URL must use HTTP or HTTPS: {value}",
                file_name=file_name,
                record_id=record_id,
            )


def validate_open_questions(
    bundle: CareerDataBundle,
    result: ValidationResult,
) -> None:
    """Surface unresolved project and target-role questions as warnings."""

    for project in bundle.projects.projects:
        for question in project.open_questions:
            result.add(
                "open_project_question",
                Severity.WARNING,
                question,
                file_name="projects.yaml",
                record_id=project.project_id,
                field_path="open_questions",
            )

    for question in bundle.target_roles.open_questions:
        result.add(
            "open_target_role_question",
            Severity.WARNING,
            question,
            file_name="target_roles.yaml",
            field_path="open_questions",
        )


def run_all_validation_rules(
    bundle: CareerDataBundle,
    *,
    as_of: date | None = None,
) -> ValidationResult:
    """Run every Phase 2 business and cross-file validation rule."""

    result = ValidationResult()

    validate_unique_ids(bundle, result)
    validate_claim_references(bundle, result)
    validate_project_references(bundle, result)
    validate_project_link_consistency(bundle, result)
    validate_certification_consistency(bundle, result)
    validate_claim_safety(bundle, result)
    validate_confidential_projects(bundle, result)
    validate_dates_and_expiry(bundle, result, as_of=as_of)
    validate_application_answers(bundle, result)
    validate_salary_consistency(bundle, result)
    validate_urls(bundle, result)
    validate_open_questions(bundle, result)

    return result
