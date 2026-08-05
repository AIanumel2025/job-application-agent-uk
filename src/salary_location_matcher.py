"""Assess salary, location, work-model, and employment-type fit."""

from __future__ import annotations

from src.job_models import NormalisedJob
from src.matching_models import (
    CareerMatchingProfile,
    FitStatus,
    LocationFit,
    PreferenceFitResult,
    SalaryFit,
)


def _normalise(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(
        value.casefold()
        .replace("-", " ")
        .replace("_", " ")
        .replace("/", " ")
        .split()
    )


def assess_salary_fit(
    job: NormalisedJob,
    profile: CareerMatchingProfile,
) -> SalaryFit:
    candidate_minimum = profile.minimum_salary
    salary = job.salary

    if candidate_minimum is None:
        return SalaryFit(
            candidate_minimum=None,
            job_minimum=salary.minimum if salary else None,
            job_maximum=salary.maximum if salary else None,
            currency=str(salary.currency) if salary else "GBP",
            status=FitStatus.UNCLEAR,
            score=50.0,
            explanation="No candidate minimum salary is configured.",
        )

    if salary is None or (
        salary.minimum is None and salary.maximum is None
    ):
        return SalaryFit(
            candidate_minimum=candidate_minimum,
            job_minimum=None,
            job_maximum=None,
            currency=str(salary.currency) if salary else "GBP",
            status=FitStatus.UNCLEAR,
            score=50.0,
            explanation="The vacancy does not disclose a usable salary range.",
        )

    job_minimum = salary.minimum
    job_maximum = salary.maximum

    if job_minimum is not None and job_minimum >= candidate_minimum:
        difference = job_minimum - candidate_minimum
        if candidate_minimum and difference >= candidate_minimum * 0.15:
            status = FitStatus.EXCEEDS
            score = 100.0
            explanation = (
                f"The stated minimum salary exceeds the candidate minimum "
                f"by £{difference:,}."
            )
        else:
            status = FitStatus.MEETS
            score = 95.0
            explanation = "The stated minimum salary meets the candidate requirement."

    elif (
        job_maximum is not None
        and job_maximum >= candidate_minimum
    ):
        status = FitStatus.ACCEPTABLE
        score = 75.0
        explanation = (
            "The salary range can meet the candidate minimum, but only toward "
            "the upper part of the range."
        )

    else:
        highest = job_maximum if job_maximum is not None else job_minimum
        shortfall = candidate_minimum - (highest or 0)
        status = FitStatus.BELOW_REQUIREMENT
        score = 20.0
        explanation = (
            f"The highest disclosed salary is £{shortfall:,} below the "
            "candidate minimum."
        )

    return SalaryFit(
        candidate_minimum=candidate_minimum,
        job_minimum=job_minimum,
        job_maximum=job_maximum,
        currency=str(salary.currency),
        status=status,
        score=score,
        explanation=explanation,
    )


def assess_location_fit(
    job: NormalisedJob,
    profile: CareerMatchingProfile,
) -> LocationFit:
    candidate_locations = profile.preferred_locations
    candidate_models = profile.preferred_work_models

    job_location = (
        job.location.raw_text
        or job.location.city
        or job.location.region
        or ""
    )
    job_work_model = str(job.location.work_model)

    normalised_job_location = _normalise(job_location)
    normalised_preferences = [_normalise(item) for item in candidate_locations]
    normalised_job_model = _normalise(job_work_model)
    normalised_models = [_normalise(item) for item in candidate_models]

    location_match = any(
        preference
        and (
            preference in normalised_job_location
            or normalised_job_location in preference
        )
        for preference in normalised_preferences
    )

    work_model_match = any(
        model
        and (
            model == normalised_job_model
            or model in normalised_job_model
            or normalised_job_model in model
        )
        for model in normalised_models
    )

    remote_or_flexible = normalised_job_model in {
        "remote",
        "hybrid",
        "flexible",
    }

    if location_match and (work_model_match or not candidate_models):
        status = FitStatus.MEETS
        score = 100.0
        explanation = "The location and work model match the candidate preferences."

    elif location_match:
        status = FitStatus.ACCEPTABLE
        score = 80.0
        explanation = (
            "The location matches, but the work model is not a direct preference match."
        )

    elif work_model_match and remote_or_flexible:
        status = FitStatus.ACCEPTABLE
        score = 80.0
        explanation = (
            "The physical location is not preferred, but the work model is suitable."
        )

    elif profile.willing_to_relocate:
        status = FitStatus.ACCEPTABLE
        score = 65.0
        explanation = (
            "The location is outside the preferred list, but relocation is acceptable."
        )

    elif not candidate_locations and not candidate_models:
        status = FitStatus.UNCLEAR
        score = 50.0
        explanation = "No location or work-model preferences are configured."

    else:
        status = FitStatus.MISMATCH
        score = 20.0
        explanation = (
            "The vacancy location and work model do not match the configured preferences."
        )

    return LocationFit(
        candidate_locations=candidate_locations,
        job_location=job_location or None,
        candidate_work_models=candidate_models,
        job_work_model=job_work_model or None,
        willing_to_relocate=profile.willing_to_relocate,
        status=status,
        score=score,
        explanation=explanation,
    )


def assess_employment_type_fit(
    job: NormalisedJob,
    profile: CareerMatchingProfile,
) -> tuple[FitStatus, float]:
    preferences = {
        _normalise(item)
        for item in profile.preferred_employment_types
        if _normalise(item)
    }
    job_types = {
        _normalise(str(item))
        for item in job.employment_types
        if _normalise(str(item))
    }

    if not preferences:
        return FitStatus.UNCLEAR, 50.0

    if not job_types:
        return FitStatus.UNCLEAR, 50.0

    if preferences & job_types:
        return FitStatus.MEETS, 100.0

    return FitStatus.MISMATCH, 25.0


def assess_preference_fit(
    job: NormalisedJob,
    profile: CareerMatchingProfile,
) -> PreferenceFitResult:
    salary = assess_salary_fit(job, profile)
    location = assess_location_fit(job, profile)
    employment_status, employment_score = assess_employment_type_fit(
        job,
        profile,
    )

    overall = round(
        (salary.score * 0.45)
        + (location.score * 0.40)
        + (employment_score * 0.15),
        2,
    )

    return PreferenceFitResult(
        salary=salary,
        location=location,
        employment_type_status=employment_status,
        employment_type_score=employment_score,
        overall_score=overall,
    )
