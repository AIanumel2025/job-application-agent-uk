"""Explainable interview-fit scoring for discovered jobs."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class InterviewFitBreakdown:
    role_family_score: float
    technical_evidence_score: float
    project_relevance_score: float
    seniority_score: float
    location_score: float
    education_score: float
    experience_gap_penalty: float
    final_score: float
    reasons: list[str] = field(default_factory=list)


def _normalise(value: str | None) -> str:
    if not value:
        return ""

    return " ".join(
        str(value)
        .lower()
        .strip()
        .split()
    )


def _contains_any(
    text: str | None,
    terms: list[str],
) -> bool:
    haystack = _normalise(text)

    return any(
        _normalise(term) in haystack
        for term in terms
        if _normalise(term)
    )


def _overlap_ratio(
    required_terms: list[str],
    candidate_terms: list[str],
) -> float:
    """
    Return fraction of required terms represented
    in candidate evidence.
    """

    required = {
        _normalise(term)
        for term in required_terms
        if _normalise(term)
    }

    candidate = {
        _normalise(term)
        for term in candidate_terms
        if _normalise(term)
    }

    if not required:
        return 1.0

    matches = sum(
        1
        for requirement in required
        if any(
            requirement in evidence
            or evidence in requirement
            for evidence in candidate
        )
    )

    return matches / len(required)


def score_interview_fit(
    *,
    job_title: str,
    job_location: str | None,
    target_role_terms: list[str],
    preferred_locations: list[str],
    preferred_seniority: list[str],
    avoided_seniority: list[str],
    required_skills: list[str],
    candidate_skills: list[str],
    relevant_project_terms: list[str],
    candidate_project_terms: list[str],
    education_match: bool = True,
    required_years_experience: int | None = None,
    candidate_relevant_years: float | None = None,
) -> InterviewFitBreakdown:
    """
    Score how likely the candidate is to be substantively
    competitive for an interview.

    Maximum before penalties: 100.
    """

    reasons: list[str] = []

    # ---------------------------------------------------------
    # 1. Role-family fit — 20 points
    # ---------------------------------------------------------

    if _contains_any(
        job_title,
        target_role_terms,
    ):
        role_family_score = 20.0
        reasons.append(
            "Job title aligns with a target role family."
        )
    else:
        role_family_score = 8.0
        reasons.append(
            "Job title has weak direct alignment with target roles."
        )

    # ---------------------------------------------------------
    # 2. Technical evidence — 25 points
    # ---------------------------------------------------------

    skill_overlap = _overlap_ratio(
        required_skills,
        candidate_skills,
    )

    technical_evidence_score = round(
        skill_overlap * 25.0,
        2,
    )

    reasons.append(
        "Technical requirement coverage: "
        f"{round(skill_overlap * 100, 1)}%."
    )

    # ---------------------------------------------------------
    # 3. Project relevance — 20 points
    # ---------------------------------------------------------

    project_overlap = _overlap_ratio(
        relevant_project_terms,
        candidate_project_terms,
    )

    project_relevance_score = round(
        project_overlap * 20.0,
        2,
    )

    reasons.append(
        "Relevant project evidence coverage: "
        f"{round(project_overlap * 100, 1)}%."
    )

    # ---------------------------------------------------------
    # 4. Seniority fit — 15 points
    # ---------------------------------------------------------

    if _contains_any(
        job_title,
        avoided_seniority,
    ):
        seniority_score = 0.0
        reasons.append(
            "Job title contains avoided seniority language."
        )

    elif _contains_any(
        job_title,
        preferred_seniority,
    ):
        seniority_score = 15.0
        reasons.append(
            "Job seniority directly matches preferred level."
        )

    else:
        # Many UK adverts simply say "AI Engineer" or
        # "Data Engineer" without junior/graduate wording.
        seniority_score = 11.0
        reasons.append(
            "No explicit preferred or avoided seniority marker."
        )

    # ---------------------------------------------------------
    # 5. Location fit — 10 points
    # ---------------------------------------------------------

    if not job_location:
        location_score = 6.0
        reasons.append(
            "Job location is unknown."
        )

    elif _contains_any(
        job_location,
        preferred_locations,
    ):
        location_score = 10.0
        reasons.append(
            "Job location matches preferred locations."
        )

    elif _contains_any(
        job_location,
        [
            "united kingdom",
            "uk",
            "gb",
            "remote",
        ],
    ):
        location_score = 8.0
        reasons.append(
            "Job is broadly compatible with UK search geography."
        )

    else:
        location_score = 2.0
        reasons.append(
            "Job location is outside preferred search geography."
        )

    # ---------------------------------------------------------
    # 6. Education fit — 10 points
    # ---------------------------------------------------------

    if education_match:
        education_score = 10.0
        reasons.append(
            "Education appears compatible with the role."
        )
    else:
        education_score = 4.0
        reasons.append(
            "Education does not clearly satisfy the stated requirement."
        )

    # ---------------------------------------------------------
    # 7. Experience-gap penalty
    # ---------------------------------------------------------

    experience_gap_penalty = 0.0

    if (
        required_years_experience is not None
        and candidate_relevant_years is not None
        and required_years_experience
        > candidate_relevant_years
    ):
        gap = (
            required_years_experience
            - candidate_relevant_years
        )

        experience_gap_penalty = min(
            gap * 5.0,
            20.0,
        )

        reasons.append(
            "Experience requirement exceeds verified "
            f"relevant experience by {gap:g} year(s)."
        )

    # ---------------------------------------------------------
    # Final score
    # ---------------------------------------------------------

    raw_score = (
        role_family_score
        + technical_evidence_score
        + project_relevance_score
        + seniority_score
        + location_score
        + education_score
        - experience_gap_penalty
    )

    final_score = round(
        max(
            0.0,
            min(
                raw_score,
                100.0,
            ),
        ),
        2,
    )

    return InterviewFitBreakdown(
        role_family_score=role_family_score,
        technical_evidence_score=technical_evidence_score,
        project_relevance_score=project_relevance_score,
        seniority_score=seniority_score,
        location_score=location_score,
        education_score=education_score,
        experience_gap_penalty=experience_gap_penalty,
        final_score=final_score,
        reasons=reasons,
    )
