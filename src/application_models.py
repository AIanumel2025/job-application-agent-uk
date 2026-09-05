"""Pydantic models for Phase 5 application-material generation."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class ApplicationModel(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )


class ApplicationDocumentType(StrEnum):
    CV = "cv"
    COVER_LETTER = "cover_letter"
    APPLICATION_ANSWER = "application_answer"
    INTERVIEW_EVIDENCE = "interview_evidence"
    MANIFEST = "manifest"


class EvidenceDecision(StrEnum):
    SELECTED = "selected"
    REJECTED = "rejected"
    REVIEW_REQUIRED = "review_required"


class ClaimStatus(StrEnum):
    APPROVED = "approved"
    BLOCKED = "blocked"
    REVIEW_REQUIRED = "review_required"


class QualitySeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ApplicationPackStatus(StrEnum):
    DRAFT = "draft"
    REVIEW_REQUIRED = "review_required"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    BLOCKED = "blocked"


class SelectedEvidence(ApplicationModel):
    evidence_id: str = Field(min_length=1)
    source_record_id: str | None = None
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    evidence_type: str = Field(min_length=1)
    relevance_score: float = Field(ge=0.0, le=1.0)
    verified: bool = False
    approved_for_application: bool = True
    decision: EvidenceDecision = EvidenceDecision.SELECTED
    reasons: list[str] = Field(default_factory=list)


class TailoredBullet(ApplicationModel):
    bullet_id: str = Field(min_length=1)
    source_evidence_ids: list[str] = Field(default_factory=list)
    text: str = Field(min_length=1)
    keywords: list[str] = Field(default_factory=list)
    relevance_score: float = Field(ge=0.0, le=1.0)
    approved: bool = True


class TailoredExperienceSection(ApplicationModel):
    source_record_id: str | None = None
    role_title: str = Field(min_length=1)
    organisation: str | None = None
    dates: str | None = None
    bullets: list[TailoredBullet] = Field(default_factory=list)


class TailoredProjectSection(ApplicationModel):
    source_record_id: str | None = None
    project_name: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    technologies: list[str] = Field(default_factory=list)
    source_evidence_ids: list[str] = Field(default_factory=list)


class TailoredCV(ApplicationModel):
    candidate_name: str = Field(min_length=1)
    target_role: str = Field(min_length=1)
    company: str = Field(min_length=1)
    professional_summary: str = Field(min_length=1)
    skills: list[str] = Field(default_factory=list)
    experience: list[TailoredExperienceSection] = Field(default_factory=list)
    projects: list[TailoredProjectSection] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    markdown: str = Field(min_length=1)


class CoverLetter(ApplicationModel):
    candidate_name: str = Field(min_length=1)
    company: str = Field(min_length=1)
    role_title: str = Field(min_length=1)
    salutation: str = Field(default="Dear Hiring Manager,")
    paragraphs: list[str] = Field(min_length=3)
    closing: str = Field(default="Yours sincerely,")
    source_evidence_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    markdown: str = Field(min_length=1)


class ApplicationQuestion(ApplicationModel):
    question_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    category: str | None = None
    maximum_words: int | None = Field(default=None, ge=1)
    sensitive: bool = False


class GeneratedApplicationAnswer(ApplicationModel):
    question_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    word_count: int = Field(ge=1)
    source_evidence_ids: list[str] = Field(default_factory=list)
    requires_review: bool = False
    warnings: list[str] = Field(default_factory=list)


class ClaimCheck(ApplicationModel):
    claim_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    status: ClaimStatus
    source_evidence_ids: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class QualityFinding(ApplicationModel):
    code: str = Field(min_length=1)
    severity: QualitySeverity
    document_type: ApplicationDocumentType
    message: str = Field(min_length=1)
    location: str | None = None
    suggestion: str | None = None


class DocumentQualityResult(ApplicationModel):
    document_type: ApplicationDocumentType
    passed: bool
    score: float = Field(ge=0.0, le=100.0)
    findings: list[QualityFinding] = Field(default_factory=list)
    keyword_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    repetition_ratio: float = Field(default=0.0, ge=0.0, le=1.0)


class ApplicationPackManifest(ApplicationModel):
    pack_id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    company: str = Field(min_length=1)
    role_title: str = Field(min_length=1)
    application_url: HttpUrl | None = None
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    status: ApplicationPackStatus = ApplicationPackStatus.DRAFT
    files: dict[str, str] = Field(default_factory=dict)
    selected_evidence_ids: list[str] = Field(default_factory=list)
    claim_checks: list[ClaimCheck] = Field(default_factory=list)
    quality_results: list[DocumentQualityResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    human_review_required: bool = True
    review_notes: list[str] = Field(
    default_factory=list
    )

    reviewed_at: datetime | None = None

    regeneration_count: int = Field(
    default=0,
    ge=0,

    )

    last_regenerated_at: datetime | None = None

    @model_validator(mode="after")
    def blocked_claims_block_pack(self) -> "ApplicationPackManifest":
        if any(check.status == ClaimStatus.BLOCKED for check in self.claim_checks):
            object.__setattr__(
                self,
                "status",
                ApplicationPackStatus.BLOCKED,
            )
        return self


class ApplicationPack(ApplicationModel):
    manifest: ApplicationPackManifest
    cv: TailoredCV
    cover_letter: CoverLetter
    application_answers: list[GeneratedApplicationAnswer] = Field(
        default_factory=list
    )
    interview_evidence_markdown: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
