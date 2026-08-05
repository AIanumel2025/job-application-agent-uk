"""Evaluate hard eligibility requirements for a vacancy."""

from __future__ import annotations

from datetime import date

from src.job_models import NormalisedJob, SponsorshipStatus
from src.matching_models import (
    CareerMatchingProfile,
    EligibilityCheck,
    EligibilityResult,
    EligibilityStatus,
    ExtractedJobRequirements,
    HardStopType,
)


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(phrase in lowered for phrase in phrases)


def _check_right_to_work(
    profile: CareerMatchingProfile,
) -> EligibilityCheck:
    if profile.right_to_work_uk is True:
        return EligibilityCheck(
            check_id="right_to_work",
            label="UK right to work",
            status=EligibilityStatus.PASSED,
            is_hard_stop=False,
            candidate_value=True,
            explanation="The career profile confirms current UK right to work.",
        )

    if profile.right_to_work_uk is False:
        return EligibilityCheck(
            check_id="right_to_work",
            label="UK right to work",
            status=EligibilityStatus.FAILED,
            hard_stop_type=HardStopType.RIGHT_TO_WORK,
            is_hard_stop=True,
            candidate_value=False,
            explanation="The career profile does not confirm UK right to work.",
        )

    return EligibilityCheck(
        check_id="right_to_work",
        label="UK right to work",
        status=EligibilityStatus.REVIEW_REQUIRED,
        is_hard_stop=False,
        candidate_value=None,
        explanation="UK right-to-work status is not explicit in the profile.",
    )


def _check_sponsorship(
    job: NormalisedJob,
    profile: CareerMatchingProfile,
) -> EligibilityCheck:
    requires_future_sponsorship = profile.future_sponsorship_required

    if not requires_future_sponsorship:
        return EligibilityCheck(
            check_id="sponsorship",
            label="Future sponsorship",
            status=EligibilityStatus.NOT_APPLICABLE,
            is_hard_stop=False,
            candidate_value=requires_future_sponsorship,
            job_requirement=str(job.sponsorship_status),
            explanation="The profile does not indicate a future sponsorship need.",
        )

    if job.sponsorship_status == SponsorshipStatus.EXPLICITLY_UNAVAILABLE:
        return EligibilityCheck(
            check_id="sponsorship",
            label="Future sponsorship",
            status=EligibilityStatus.FAILED,
            hard_stop_type=HardStopType.NO_SPONSORSHIP,
            is_hard_stop=True,
            candidate_value=True,
            job_requirement="Sponsorship explicitly unavailable",
            evidence=job.sponsorship_evidence,
            explanation=(
                "The candidate requires future sponsorship, but the vacancy "
                "explicitly says sponsorship is unavailable."
            ),
        )

    if job.sponsorship_status == SponsorshipStatus.CONFIRMED:
        return EligibilityCheck(
            check_id="sponsorship",
            label="Future sponsorship",
            status=EligibilityStatus.PASSED,
            is_hard_stop=False,
            candidate_value=True,
            job_requirement="Sponsorship confirmed",
            evidence=job.sponsorship_evidence,
            explanation="The vacancy indicates that sponsorship is available.",
        )

    if job.sponsorship_status == SponsorshipStatus.SECURITY_RESTRICTED:
        return EligibilityCheck(
            check_id="sponsorship",
            label="Future sponsorship",
            status=EligibilityStatus.FAILED,
            hard_stop_type=HardStopType.SECURITY_CLEARANCE,
            is_hard_stop=True,
            candidate_value=True,
            job_requirement="Security or nationality restriction",
            evidence=job.sponsorship_evidence,
            explanation=(
                "The vacancy carries a security or nationality restriction "
                "that conflicts with the candidate's sponsorship need."
            ),
        )

    return EligibilityCheck(
        check_id="sponsorship",
        label="Future sponsorship",
        status=EligibilityStatus.REVIEW_REQUIRED,
        is_hard_stop=False,
        candidate_value=True,
        job_requirement=str(job.sponsorship_status),
        evidence=job.sponsorship_evidence,
        explanation=(
            "The candidate needs future sponsorship, but the vacancy does not "
            "provide a definite answer."
        ),
    )


def _check_security(
    requirements: ExtractedJobRequirements,
) -> EligibilityCheck:
    statement = requirements.security_statement

    if not statement:
        return EligibilityCheck(
            check_id="security",
            label="Security restrictions",
            status=EligibilityStatus.NOT_APPLICABLE,
            is_hard_stop=False,
            explanation="No explicit security restriction was extracted.",
        )

    if _contains_any(
        statement,
        (
            "uk national only",
            "british citizen only",
            "sole uk national",
            "developed vetting",
            "dv clearance",
            "sc clearance required",
        ),
    ):
        return EligibilityCheck(
            check_id="security",
            label="Security restrictions",
            status=EligibilityStatus.REVIEW_REQUIRED,
            hard_stop_type=HardStopType.SECURITY_CLEARANCE,
            is_hard_stop=False,
            job_requirement=statement,
            evidence=[statement],
            explanation=(
                "The vacancy contains a security or nationality condition that "
                "must be checked manually before applying."
            ),
        )

    return EligibilityCheck(
        check_id="security",
        label="Security restrictions",
        status=EligibilityStatus.REVIEW_REQUIRED,
        is_hard_stop=False,
        job_requirement=statement,
        evidence=[statement],
        explanation="A security requirement was found and needs manual review.",
    )


def _check_driving_licence(
    job: NormalisedJob,
    profile: CareerMatchingProfile,
) -> EligibilityCheck:
    text = " ".join(
        [
            job.description,
            *job.requirements,
            *job.responsibilities,
        ]
    )

    required = _contains_any(
        text,
        (
            "full uk driving licence",
            "valid driving licence",
            "valid driver's licence",
            "driving license required",
            "driving licence required",
        ),
    )

    if not required:
        return EligibilityCheck(
            check_id="driving_licence",
            label="Driving licence",
            status=EligibilityStatus.NOT_APPLICABLE,
            is_hard_stop=False,
            explanation="No mandatory driving-licence requirement was found.",
        )

    status = (profile.driving_licence_status or "").casefold()

    if status in {"yes", "full", "valid", "full uk", "held"}:
        return EligibilityCheck(
            check_id="driving_licence",
            label="Driving licence",
            status=EligibilityStatus.PASSED,
            is_hard_stop=False,
            candidate_value=profile.driving_licence_status,
            job_requirement="Valid driving licence required",
            explanation="The candidate profile indicates a suitable licence.",
        )

    if status in {"no", "none", "n/a", "not applicable"}:
        return EligibilityCheck(
            check_id="driving_licence",
            label="Driving licence",
            status=EligibilityStatus.FAILED,
            hard_stop_type=HardStopType.DRIVING_LICENCE,
            is_hard_stop=True,
            candidate_value=profile.driving_licence_status,
            job_requirement="Valid driving licence required",
            explanation=(
                "The vacancy requires a driving licence, but the profile does "
                "not provide one."
            ),
        )

    return EligibilityCheck(
        check_id="driving_licence",
        label="Driving licence",
        status=EligibilityStatus.REVIEW_REQUIRED,
        is_hard_stop=False,
        candidate_value=profile.driving_licence_status,
        job_requirement="Valid driving licence required",
        explanation="Driving-licence eligibility needs manual confirmation.",
    )


def _check_education(
    requirements: ExtractedJobRequirements,
    profile: CareerMatchingProfile,
) -> EligibilityCheck:
    requirement = requirements.required_degree_level

    if not requirement:
        return EligibilityCheck(
            check_id="education",
            label="Mandatory education",
            status=EligibilityStatus.NOT_APPLICABLE,
            is_hard_stop=False,
            explanation="No mandatory degree requirement was extracted.",
        )

    candidate_text = " ".join(profile.education_levels).casefold()
    requirement_text = requirement.casefold()

    degree_terms = {
        "bachelor": ("bachelor", "bsc", "undergraduate"),
        "master": ("master", "msc", "postgraduate"),
        "phd": ("phd", "doctorate"),
        "degree": ("degree", "bachelor", "master", "msc", "bsc", "phd"),
    }

    matched = False
    for key, candidates in degree_terms.items():
        if key in requirement_text:
            matched = any(term in candidate_text for term in candidates)
            break

    if matched:
        return EligibilityCheck(
            check_id="education",
            label="Mandatory education",
            status=EligibilityStatus.PASSED,
            is_hard_stop=False,
            candidate_value=", ".join(profile.education_levels),
            job_requirement=requirement,
            explanation="The profile appears to meet the degree requirement.",
        )

    return EligibilityCheck(
        check_id="education",
        label="Mandatory education",
        status=EligibilityStatus.REVIEW_REQUIRED,
        is_hard_stop=False,
        candidate_value=", ".join(profile.education_levels) or None,
        job_requirement=requirement,
        explanation=(
            "The extracted degree requirement could not be confirmed "
            "automatically from the profile."
        ),
    )


def _check_closing_date(job: NormalisedJob) -> EligibilityCheck:
    if job.closing_date is None:
        return EligibilityCheck(
            check_id="closing_date",
            label="Vacancy closing date",
            status=EligibilityStatus.UNCLEAR,
            is_hard_stop=False,
            explanation="The vacancy does not provide a closing date.",
        )

    if job.closing_date < date.today():
        return EligibilityCheck(
            check_id="closing_date",
            label="Vacancy closing date",
            status=EligibilityStatus.FAILED,
            hard_stop_type=HardStopType.START_DATE,
            is_hard_stop=True,
            job_requirement=job.closing_date.isoformat(),
            explanation="The vacancy closing date has already passed.",
        )

    return EligibilityCheck(
        check_id="closing_date",
        label="Vacancy closing date",
        status=EligibilityStatus.PASSED,
        is_hard_stop=False,
        job_requirement=job.closing_date.isoformat(),
        explanation="The vacancy is still within its stated application window.",
    )


def check_eligibility(
    job: NormalisedJob,
    requirements: ExtractedJobRequirements,
    profile: CareerMatchingProfile,
) -> EligibilityResult:
    """Run all current Phase 4 eligibility checks."""

    checks = [
        _check_right_to_work(profile),
        _check_sponsorship(job, profile),
        _check_security(requirements),
        _check_driving_licence(job, profile),
        _check_education(requirements, profile),
        _check_closing_date(job),
    ]

    scored_checks = [
        item
        for item in checks
        if item.status != EligibilityStatus.NOT_APPLICABLE
    ]

    score_map = {
        EligibilityStatus.PASSED: 100.0,
        EligibilityStatus.NOT_APPLICABLE: 100.0,
        EligibilityStatus.UNCLEAR: 50.0,
        EligibilityStatus.REVIEW_REQUIRED: 50.0,
        EligibilityStatus.FAILED: 0.0,
    }

    result = EligibilityResult(
        checks=checks,
        score=(
            round(
                sum(score_map[item.status] for item in scored_checks)
                / len(scored_checks),
                2,
            )
            if scored_checks
            else 100.0
        ),
    )
    result.recalculate()
    return result
