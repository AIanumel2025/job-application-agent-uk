"""Self-contained helpers for Phase 5 tests."""

from __future__ import annotations

from uuid import uuid4

from src.application_models import (
    EvidenceDecision,
    SelectedEvidence,
)
from src.matching_models import (
    CareerEvidence,
    CareerMatchingProfile,
    EligibilityResult,
    EligibilityStatus,
    ExperienceMatchResult,
    ExtractedJobRequirements,
    FitStatus,
    JobMatchResult,
    LocationFit,
    MatchExplanation,
    MatchRecommendation,
    MatchScoreBreakdown,
    PreferenceFitResult,
    RequirementCategory,
    RequirementPriority,
    SalaryFit,
    ScoreBand,
    SkillMatchResult,
)
from src.matching_models import JobRequirement


def make_profile(**overrides) -> CareerMatchingProfile:
    data = {
        "name": "Anthony L. Anumel",
        "target_roles": ["Data Engineer", "AI Engineer"],
        "skills": ["Python", "SQL", "Power BI", "Machine Learning"],
        "tools": ["PostgreSQL", "AWS S3", "Docker", "GitHub Actions"],
        "industries": ["Education", "Civil Engineering"],
        "certifications": ["PL-300 Power BI"],
        "education_levels": [
            "MSc Artificial Intelligence",
            "BSc Civil Engineering",
        ],
        "years_of_experience": 7.0,
        "preferred_locations": ["London", "Richmond"],
        "preferred_work_models": ["Remote", "Hybrid"],
        "preferred_employment_types": ["Permanent", "Contract"],
        "minimum_salary": 50000,
        "right_to_work_uk": True,
        "future_sponsorship_required": True,
        "earliest_start_date": "2026-09-07",
        "driving_licence_status": "N/A",
        "willing_to_relocate": True,
        "evidence": [
            CareerEvidence(
                evidence_id="exp_1",
                evidence_type="experience",
                source_record_id="experience_teacher",
                title="Algebra Teacher",
                description=(
                    "Used Excel and Power BI dashboards to improve student "
                    "performance and communicate insights."
                ),
                verified=True,
                approved_for_application=True,
            ),
            CareerEvidence(
                evidence_id="project_1",
                evidence_type="project",
                source_record_id="project_pipeline",
                title="Document Intelligence Pipeline",
                description=(
                    "Built a Python and AWS document-processing pipeline "
                    "using Docker and GitHub Actions."
                ),
                verified=True,
                approved_for_application=True,
            ),
            CareerEvidence(
                evidence_id="skill_1",
                evidence_type="skill",
                source_record_id="skill_python",
                title="Python",
                description="Python, Pandas and NumPy data analysis.",
                verified=True,
                approved_for_application=True,
            ),
        ],
    }
    data.update(overrides)
    return CareerMatchingProfile(**data)


def make_match(**overrides) -> JobMatchResult:
    job_id = overrides.pop("job_id", uuid4())

    requirements = ExtractedJobRequirements(
        job_id=job_id,
        requirements=[
            JobRequirement(
                requirement_id="req_python",
                category=RequirementCategory.SKILL,
                priority=RequirementPriority.REQUIRED,
                text="Python is required.",
                normalised_value="python",
            ),
            JobRequirement(
                requirement_id="req_aws",
                category=RequirementCategory.SKILL,
                priority=RequirementPriority.PREFERRED,
                text="AWS experience is preferred.",
                normalised_value="aws",
            ),
        ],
        required_tools=["python", "aws"],
    )

    eligibility = EligibilityResult(
        checks=[],
        overall_status=EligibilityStatus.PASSED,
        hard_stop_triggered=False,
        score=100,
    )

    preference = PreferenceFitResult(
        salary=SalaryFit(
            candidate_minimum=50000,
            job_minimum=55000,
            job_maximum=65000,
            status=FitStatus.MEETS,
            score=95,
            explanation="Salary meets the requirement.",
        ),
        location=LocationFit(
            candidate_locations=["London"],
            job_location="London",
            candidate_work_models=["Hybrid"],
            job_work_model="Hybrid",
            status=FitStatus.MEETS,
            score=100,
            explanation="Location and work model match.",
        ),
        employment_type_status=FitStatus.MEETS,
        employment_type_score=100,
        overall_score=95,
    )

    breakdown = MatchScoreBreakdown(
        components=[],
        total_score=85,
        score_band=ScoreBand.STRONG,
    )

    data = {
        "job_id": job_id,
        "job_title": "Data Engineer",
        "company": "Example AI Ltd",
        "application_url": "https://jobs.example.com/data-engineer",
        "requirements": requirements,
        "skill_result": SkillMatchResult(matches=[], score=85),
        "experience_result": ExperienceMatchResult(matches=[], score=80),
        "eligibility_result": eligibility,
        "preference_result": preference,
        "score_breakdown": breakdown,
        "explanation": MatchExplanation(
            summary="Strong match.",
            strengths=["Python and AWS evidence."],
            gaps=[],
            risks=[],
            eligibility_notes=[],
            recommended_actions=["Proceed to application tailoring."],
            evidence_ids=["exp_1", "project_1"],
        ),
        "recommendation": MatchRecommendation.STRONG_MATCH,
        "final_score": 85,
        "requires_manual_review": False,
        "blocked_reason": None,
    }
    data.update(overrides)
    return JobMatchResult(**data)


def make_selected_evidence() -> list[SelectedEvidence]:
    return [
        SelectedEvidence(
            evidence_id="exp_1",
            source_record_id="experience_teacher",
            title="Algebra Teacher",
            description=(
                "Used Excel and Power BI dashboards to improve student "
                "performance and communicate insights."
            ),
            evidence_type="experience",
            relevance_score=0.8,
            verified=True,
            approved_for_application=True,
            decision=EvidenceDecision.SELECTED,
            reasons=["Relevant and verified."],
        ),
        SelectedEvidence(
            evidence_id="project_1",
            source_record_id="project_pipeline",
            title="Document Intelligence Pipeline",
            description=(
                "Built a Python and AWS document-processing pipeline "
                "using Docker and GitHub Actions."
            ),
            evidence_type="project",
            relevance_score=0.9,
            verified=True,
            approved_for_application=True,
            decision=EvidenceDecision.SELECTED,
            reasons=["Relevant and verified."],
        ),
    ]
