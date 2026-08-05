"""Self-contained helpers for Phase 4 tests.

This is deliberately not a conftest.py file. It avoids changing the shared
fixtures already used by the Phase 2 and Phase 3 test suites.
"""

from __future__ import annotations

from datetime import date
from uuid import uuid4

from src.job_models import (
    EmploymentType,
    JobLocation,
    JobSource,
    NormalisedJob,
    SalaryRange,
    SponsorshipStatus,
    WorkModel,
)
from src.matching_models import (
    CareerEvidence,
    CareerMatchingProfile,
    EligibilityResult,
    EligibilityStatus,
    EvidenceType,
    ExperienceMatchResult,
    ExtractedJobRequirements,
    FitStatus,
    JobRequirement,
    LocationFit,
    PreferenceFitResult,
    RequirementCategory,
    RequirementPriority,
    SalaryFit,
    SkillMatchResult,
)


def make_profile(**overrides) -> CareerMatchingProfile:
    data = {
        "name": "Anthony L. Anumel",
        "target_roles": ["Data Engineer", "AI Engineer"],
        "skills": ["Python", "SQL", "Power BI", "Machine Learning"],
        "tools": ["PostgreSQL", "AWS S3", "Docker", "GitHub Actions"],
        "industries": ["Education", "Civil Engineering"],
        "certifications": ["PL-300 Power BI"],
        "education_levels": ["MSc Artificial Intelligence", "BSc Civil Engineering"],
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
                evidence_id="skill_python",
                evidence_type=EvidenceType.SKILL,
                title="Python",
                description="Python, Pandas and NumPy data analysis.",
                verified=True,
            ),
            CareerEvidence(
                evidence_id="project_pipeline",
                evidence_type=EvidenceType.PROJECT,
                title="Document Intelligence Pipeline",
                description="Built an AWS and Python data-processing pipeline.",
                verified=True,
            ),
            CareerEvidence(
                evidence_id="experience_teacher",
                evidence_type=EvidenceType.EXPERIENCE,
                title="Algebra Teacher",
                description="Used Excel and Power BI dashboards to improve outcomes.",
                verified=True,
            ),
        ],
    }
    data.update(overrides)
    return CareerMatchingProfile(**data)


def make_job(**overrides) -> NormalisedJob:
    data = {
        "job_id": uuid4(),
        "source": JobSource.COMPANY_SITE,
        "source_job_id": "JOB-123",
        "application_url": "https://jobs.example.com/job-123",
        "canonical_url": "https://jobs.example.com/job-123",
        "title": "Data Engineer",
        "title_normalised": "data engineer",
        "company": "Example AI Ltd",
        "company_normalised": "example ai",
        "location": JobLocation(
            raw_text="London, United Kingdom",
            city="London",
            region="Greater London",
            work_model=WorkModel.HYBRID,
        ),
        "salary": SalaryRange(
            minimum=55000,
            maximum=65000,
            currency="GBP",
        ),
        "employment_types": [
            EmploymentType.PERMANENT,
            EmploymentType.FULL_TIME,
        ],
        "sponsorship_status": SponsorshipStatus.CONFIRMED,
        "sponsorship_evidence": ["Skilled Worker sponsorship can be provided."],
        "description": (
            "We require Python, SQL and three years of data engineering "
            "experience. Skilled Worker sponsorship can be provided."
        ),
        "requirements": [
            "Python and SQL are required.",
            "At least 3 years of data engineering experience.",
        ],
        "preferred_skills": ["AWS is preferred."],
        "responsibilities": ["Build reliable data pipelines."],
        "posted_date": date(2026, 8, 1),
        "closing_date": date(2099, 8, 31),
    }
    data.update(overrides)
    return NormalisedJob(**data)


def make_requirements(job_id=None) -> ExtractedJobRequirements:
    return ExtractedJobRequirements(
        job_id=job_id or uuid4(),
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
                text="AWS is preferred.",
                normalised_value="aws",
            ),
            JobRequirement(
                requirement_id="req_exp",
                category=RequirementCategory.EXPERIENCE,
                priority=RequirementPriority.REQUIRED,
                text="At least 3 years of data engineering experience.",
                normalised_value="3",
            ),
        ],
        minimum_years_experience=3.0,
        required_tools=["python", "aws"],
    )


def make_preference_result(score=85.0) -> PreferenceFitResult:
    return PreferenceFitResult(
        salary=SalaryFit(
            candidate_minimum=50000,
            job_minimum=55000,
            job_maximum=65000,
            status=FitStatus.MEETS,
            score=95.0,
            explanation="Salary meets the requirement.",
        ),
        location=LocationFit(
            candidate_locations=["London"],
            job_location="London",
            candidate_work_models=["Hybrid"],
            job_work_model="Hybrid",
            status=FitStatus.MEETS,
            score=100.0,
            explanation="Location and work model match.",
        ),
        employment_type_status=FitStatus.MEETS,
        employment_type_score=100.0,
        overall_score=score,
    )


def make_eligibility(score=100.0) -> EligibilityResult:
    return EligibilityResult(
        checks=[],
        overall_status=EligibilityStatus.PASSED,
        hard_stop_triggered=False,
        score=score,
    )


def empty_skill_result(score=80.0) -> SkillMatchResult:
    return SkillMatchResult(matches=[], score=score)


def empty_experience_result(score=75.0) -> ExperienceMatchResult:
    return ExperienceMatchResult(matches=[], score=score)
