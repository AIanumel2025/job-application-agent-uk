"""Reusable job-scoring service independent of the persistence layer."""

from __future__ import annotations

from pathlib import Path

from src.career_data_loader import (
    find_repository_root,
    load_career_data,
)
from src.career_profile_builder import build_career_matching_profile
from src.eligibility_checker import check_eligibility
from src.experience_matcher import match_experience
from src.job_models import NormalisedJob
from src.job_requirement_extractor import extract_job_requirements
from src.match_explainer import build_match_explanation
from src.match_scoring import (
    calculate_match_score,
    recommendation_for,
)
from src.matching_models import (
    CareerMatchingProfile,
    JobMatchResult,
)
from src.salary_location_matcher import assess_preference_fit
from src.skill_matcher import match_skills


def evidence_quality_score(
    profile: CareerMatchingProfile,
) -> float:
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

    approval_score = (
        len(approved) / len(profile.evidence)
    )

    verification_score = (
        len(verified) / len(approved)
        if approved
        else 0.0
    )

    return round(
        (approval_score * 50.0)
        + (verification_score * 50.0),
        2,
    )


def load_matching_profile(
    repository_root: str | Path | None = None,
) -> CareerMatchingProfile:
    root = (
        Path(repository_root).expanduser().resolve()
        if repository_root
        else find_repository_root(Path.cwd())
    )

    bundle = load_career_data(root)

    return build_career_matching_profile(bundle)


def score_job(
    job: NormalisedJob,
    profile: CareerMatchingProfile,
) -> JobMatchResult:
    """Score one normalised vacancy against one career profile."""

    requirements = extract_job_requirements(job)

    skill_result = match_skills(
        requirements,
        profile,
    )

    experience_result = match_experience(
        requirements,
        profile,
    )

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
        evidence_quality_score=evidence_quality_score(profile),
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

    return JobMatchResult(
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
