"""Pydantic models for Phase 4 job matching, scoring, and ranking."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class MatchingModel(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )


class RequirementPriority(StrEnum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    UNCLEAR = "unclear"


class RequirementCategory(StrEnum):
    SKILL = "skill"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    CERTIFICATION = "certification"
    ELIGIBILITY = "eligibility"
    LOCATION = "location"
    SALARY = "salary"
    EMPLOYMENT_TYPE = "employment_type"
    WORK_MODEL = "work_model"
    INDUSTRY = "industry"
    SECURITY = "security"
    OTHER = "other"


class MatchStrength(StrEnum):
    EXACT = "exact"
    STRONG_RELATED = "strong_related"
    TRANSFERABLE = "transferable"
    WEAK = "weak"
    MISSING = "missing"
    NOT_APPLICABLE = "not_applicable"


class EvidenceType(StrEnum):
    EXPERIENCE = "experience"
    PROJECT = "project"
    SKILL = "skill"
    CERTIFICATION = "certification"
    EDUCATION = "education"
    ACHIEVEMENT = "achievement"
    APPLICATION_ANSWER = "application_answer"
    OTHER = "other"


class ExperienceEvidenceLevel(StrEnum):
    DIRECT = "direct"
    TRANSFERABLE = "transferable"
    PROJECT_BASED = "project_based"
    ACADEMIC = "academic"
    INSUFFICIENT = "insufficient"


class EligibilityStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    UNCLEAR = "unclear"
    REVIEW_REQUIRED = "review_required"
    NOT_APPLICABLE = "not_applicable"


class FitStatus(StrEnum):
    EXCEEDS = "exceeds"
    MEETS = "meets"
    ACCEPTABLE = "acceptable"
    UNCLEAR = "unclear"
    BELOW_REQUIREMENT = "below_requirement"
    MISMATCH = "mismatch"
    NOT_APPLICABLE = "not_applicable"


class MatchRecommendation(StrEnum):
    STRONG_MATCH = "strong_match"
    GOOD_MATCH = "good_match"
    POSSIBLE_MATCH = "possible_match"
    WEAK_MATCH = "weak_match"
    DO_NOT_APPLY = "do_not_apply"
    NOT_ELIGIBLE = "not_eligible"
    MANUAL_REVIEW = "manual_review"


class ScoreBand(StrEnum):
    STRONG = "strong"
    GOOD = "good"
    POSSIBLE = "possible"
    WEAK = "weak"
    POOR = "poor"


class HardStopType(StrEnum):
    NO_SPONSORSHIP = "no_sponsorship"
    CITIZENSHIP_RESTRICTION = "citizenship_restriction"
    SECURITY_CLEARANCE = "security_clearance"
    MANDATORY_CERTIFICATION = "mandatory_certification"
    MANDATORY_EDUCATION = "mandatory_education"
    DRIVING_LICENCE = "driving_licence"
    START_DATE = "start_date"
    SALARY_FLOOR = "salary_floor"
    RIGHT_TO_WORK = "right_to_work"
    OTHER = "other"


class JobRequirement(MatchingModel):
    requirement_id: str = Field(min_length=1)
    category: RequirementCategory
    priority: RequirementPriority
    text: str = Field(min_length=1)
    normalised_value: str | None = None
    source_section: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_text: str | None = None


class ExtractedJobRequirements(MatchingModel):
    job_id: UUID
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    requirements: list[JobRequirement] = Field(default_factory=list)
    minimum_years_experience: float | None = Field(default=None, ge=0)
    required_degree_level: str | None = None
    required_certifications: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    required_industries: list[str] = Field(default_factory=list)
    sponsorship_statement: str | None = None
    security_statement: str | None = None
    extraction_notes: list[str] = Field(default_factory=list)

    @property
    def required_items(self) -> list[JobRequirement]:
        return [x for x in self.requirements if x.priority == RequirementPriority.REQUIRED]

    @property
    def preferred_items(self) -> list[JobRequirement]:
        return [x for x in self.requirements if x.priority == RequirementPriority.PREFERRED]


class CareerEvidence(MatchingModel):
    evidence_id: str = Field(min_length=1)
    evidence_type: EvidenceType
    source_record_id: str | None = None
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    verified: bool = False
    approved_for_application: bool = True
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)


class CareerMatchingProfile(MatchingModel):
    profile_id: str = Field(default="primary_profile", min_length=1)
    name: str = Field(min_length=1)
    target_roles: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    education_levels: list[str] = Field(default_factory=list)
    years_of_experience: float | None = Field(default=None, ge=0)
    preferred_locations: list[str] = Field(default_factory=list)
    preferred_work_models: list[str] = Field(default_factory=list)
    preferred_employment_types: list[str] = Field(default_factory=list)
    minimum_salary: int | None = Field(default=None, ge=0)
    right_to_work_uk: bool | None = None
    future_sponsorship_required: bool | None = None
    earliest_start_date: str | None = None
    driving_licence_status: str | None = None
    willing_to_relocate: bool | None = None
    evidence: list[CareerEvidence] = Field(default_factory=list)


class SkillMatch(MatchingModel):
    requirement_id: str = Field(min_length=1)
    required_skill: str = Field(min_length=1)
    priority: RequirementPriority
    match_strength: MatchStrength
    matched_skill: str | None = None
    similarity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: list[CareerEvidence] = Field(default_factory=list)
    explanation: str = Field(min_length=1)


class SkillMatchResult(MatchingModel):
    matches: list[SkillMatch] = Field(default_factory=list)
    exact_matches: int = Field(default=0, ge=0)
    related_matches: int = Field(default=0, ge=0)
    transferable_matches: int = Field(default=0, ge=0)
    missing_required: int = Field(default=0, ge=0)
    missing_preferred: int = Field(default=0, ge=0)
    score: float = Field(default=0.0, ge=0.0, le=100.0)

    def recalculate_counts(self) -> None:
        self.exact_matches = sum(x.match_strength == MatchStrength.EXACT for x in self.matches)
        self.related_matches = sum(x.match_strength == MatchStrength.STRONG_RELATED for x in self.matches)
        self.transferable_matches = sum(x.match_strength == MatchStrength.TRANSFERABLE for x in self.matches)
        self.missing_required = sum(
            x.match_strength == MatchStrength.MISSING and x.priority == RequirementPriority.REQUIRED
            for x in self.matches
        )
        self.missing_preferred = sum(
            x.match_strength == MatchStrength.MISSING and x.priority == RequirementPriority.PREFERRED
            for x in self.matches
        )


class ExperienceMatch(MatchingModel):
    requirement_id: str = Field(min_length=1)
    requirement_text: str = Field(min_length=1)
    priority: RequirementPriority
    evidence_level: ExperienceEvidenceLevel
    years_required: float | None = Field(default=None, ge=0)
    years_evidenced: float | None = Field(default=None, ge=0)
    evidence: list[CareerEvidence] = Field(default_factory=list)
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    explanation: str = Field(min_length=1)


class ExperienceMatchResult(MatchingModel):
    matches: list[ExperienceMatch] = Field(default_factory=list)
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    direct_matches: int = Field(default=0, ge=0)
    transferable_matches: int = Field(default=0, ge=0)
    project_based_matches: int = Field(default=0, ge=0)
    insufficient_matches: int = Field(default=0, ge=0)


class EligibilityCheck(MatchingModel):
    check_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    status: EligibilityStatus
    hard_stop_type: HardStopType | None = None
    is_hard_stop: bool = False
    candidate_value: str | bool | int | float | None = None
    job_requirement: str | None = None
    evidence: list[str] = Field(default_factory=list)
    explanation: str = Field(min_length=1)

    @model_validator(mode="after")
    def hard_stop_requires_type(self) -> "EligibilityCheck":
        if self.is_hard_stop and self.hard_stop_type is None:
            raise ValueError("hard-stop eligibility checks require a type")
        return self


class EligibilityResult(MatchingModel):
    checks: list[EligibilityCheck] = Field(default_factory=list)
    overall_status: EligibilityStatus = EligibilityStatus.UNCLEAR
    hard_stop_triggered: bool = False
    hard_stops: list[EligibilityCheck] = Field(default_factory=list)
    score: float = Field(default=0.0, ge=0.0, le=100.0)

    def recalculate(self) -> None:
        self.hard_stops = [
            x for x in self.checks
            if x.is_hard_stop and x.status == EligibilityStatus.FAILED
        ]
        self.hard_stop_triggered = bool(self.hard_stops)
        if self.hard_stop_triggered:
            self.overall_status = EligibilityStatus.FAILED
        elif any(x.status == EligibilityStatus.REVIEW_REQUIRED for x in self.checks):
            self.overall_status = EligibilityStatus.REVIEW_REQUIRED
        elif any(x.status == EligibilityStatus.UNCLEAR for x in self.checks):
            self.overall_status = EligibilityStatus.UNCLEAR
        elif self.checks:
            self.overall_status = EligibilityStatus.PASSED


class SalaryFit(MatchingModel):
    candidate_minimum: int | None = Field(default=None, ge=0)
    job_minimum: int | None = Field(default=None, ge=0)
    job_maximum: int | None = Field(default=None, ge=0)
    currency: str = "GBP"
    status: FitStatus = FitStatus.UNCLEAR
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    explanation: str = Field(min_length=1)


class LocationFit(MatchingModel):
    candidate_locations: list[str] = Field(default_factory=list)
    job_location: str | None = None
    candidate_work_models: list[str] = Field(default_factory=list)
    job_work_model: str | None = None
    willing_to_relocate: bool | None = None
    status: FitStatus = FitStatus.UNCLEAR
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    explanation: str = Field(min_length=1)


class PreferenceFitResult(MatchingModel):
    salary: SalaryFit
    location: LocationFit
    employment_type_status: FitStatus = FitStatus.UNCLEAR
    employment_type_score: float = Field(default=0.0, ge=0.0, le=100.0)
    overall_score: float = Field(default=0.0, ge=0.0, le=100.0)


class ScoreComponent(MatchingModel):
    name: str = Field(min_length=1)
    raw_score: float = Field(ge=0.0, le=100.0)
    weight: float = Field(ge=0.0, le=1.0)
    weighted_score: float = Field(ge=0.0, le=100.0)
    explanation: str | None = None

    @model_validator(mode="after")
    def validate_weighted_score(self) -> "ScoreComponent":
        if abs(self.weighted_score - (self.raw_score * self.weight)) > 0.01:
            raise ValueError("weighted_score must equal raw_score multiplied by weight")
        return self


class MatchScoreBreakdown(MatchingModel):
    components: list[ScoreComponent] = Field(default_factory=list)
    total_score: float = Field(default=0.0, ge=0.0, le=100.0)
    score_band: ScoreBand = ScoreBand.POOR

    @field_validator("components")
    @classmethod
    def total_weight_must_not_exceed_one(cls, components: list[ScoreComponent]) -> list[ScoreComponent]:
        if sum(x.weight for x in components) > 1.0001:
            raise ValueError("score component weights cannot exceed 1.0")
        return components


class MatchExplanation(MatchingModel):
    summary: str = Field(min_length=1)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    eligibility_notes: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class JobMatchResult(MatchingModel):
    match_id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    job_title: str = Field(min_length=1)
    company: str = Field(min_length=1)
    application_url: HttpUrl | None = None
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    requirements: ExtractedJobRequirements
    skill_result: SkillMatchResult
    experience_result: ExperienceMatchResult
    eligibility_result: EligibilityResult
    preference_result: PreferenceFitResult
    score_breakdown: MatchScoreBreakdown
    explanation: MatchExplanation
    recommendation: MatchRecommendation
    final_score: float = Field(ge=0.0, le=100.0)
    requires_manual_review: bool = False
    blocked_reason: str | None = None

    @model_validator(mode="after")
    def enforce_hard_stop_recommendation(self) -> "JobMatchResult":
        if self.eligibility_result.hard_stop_triggered:
            if self.recommendation not in {
                MatchRecommendation.DO_NOT_APPLY,
                MatchRecommendation.NOT_ELIGIBLE,
            }:
                raise ValueError("hard-stop results must use a non-application recommendation")
            if not self.blocked_reason:
                raise ValueError("hard-stop results require a blocked_reason")
        return self


class RankedJob(MatchingModel):
    rank: int = Field(ge=1)
    job_id: UUID
    match_id: UUID
    job_title: str = Field(min_length=1)
    company: str = Field(min_length=1)
    final_score: float = Field(ge=0.0, le=100.0)
    recommendation: MatchRecommendation
    eligibility_status: EligibilityStatus
    closing_date: str | None = None
    urgency_score: float = Field(default=0.0, ge=0.0, le=100.0)
    strategic_value_score: float = Field(default=0.0, ge=0.0, le=100.0)
    ranking_score: float = Field(default=0.0, ge=0.0, le=100.0)


class JobRankingReport(MatchingModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_jobs: int = Field(default=0, ge=0)
    eligible_jobs: int = Field(default=0, ge=0)
    blocked_jobs: int = Field(default=0, ge=0)
    ranked_jobs: list[RankedJob] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def counts_must_match_ranked_jobs(self) -> "JobRankingReport":
        if self.total_jobs < len(self.ranked_jobs):
            raise ValueError("total_jobs cannot be lower than the number of ranked jobs")
        return self
