"""Live multi-score evaluation for job opportunities and application packs."""

from __future__ import annotations

from dataclasses import dataclass

from src.application_models import (
    ApplicationPack,
    ClaimStatus,
)
from src.matching_models import (
    JobMatchResult,
    MatchStrength,
    RequirementPriority,
)
from src.opportunity_evaluator import (
    OpportunityEvaluation,
    classify_opportunity,
)


@dataclass(slots=True)
class PreApplicationScores:
    interview_fit_score: float
    must_have_coverage: float
    must_have_known: bool


@dataclass(slots=True)
class FinalApplicationScores:
    ats_keyword_score: float
    interview_fit_score: float
    must_have_coverage: float
    must_have_known: bool
    claim_integrity: float
    claim_approval_readiness: float
    critical_red_flags: int
    evaluation: OpportunityEvaluation


def _clamp_score(value: float) -> float:
    return round(
        max(
            0.0,
            min(float(value), 100.0),
        ),
        2,
    )

def calculate_interview_fit(
    match: JobMatchResult,
) -> float:
    """
    Calculate interview fit using only dimensions that were
    actually evaluated.

    Missing dimensions are not treated as zero.
    """

    components: list[tuple[float, float]] = []

    # Technical skill alignment.
    components.append(
        (
            float(match.skill_result.score or 0.0),
            0.50,
        )
    )

    # Only count experience if experience requirements
    # were actually extracted and evaluated.
    if match.experience_result.matches:
        components.append(
            (
                float(
                    match.experience_result.score
                    or 0.0
                ),
                0.25,
            )
        )

    # Eligibility contributes, but should not dominate.
    components.append(
        (
            float(
                match.eligibility_result.score
                or 0.0
            ),
            0.10,
        )
    )

    preference_scores: list[float] = []

    salary = getattr(
        match.preference_result,
        "salary",
        None,
    )

    location = getattr(
        match.preference_result,
        "location",
        None,
    )

    if salary is not None:
        preference_scores.append(
            float(
                getattr(
                    salary,
                    "score",
                    0.0,
                )
                or 0.0
            )
        )

    if location is not None:
        preference_scores.append(
            float(
                getattr(
                    location,
                    "score",
                    0.0,
                )
                or 0.0
            )
        )

    if preference_scores:
        components.append(
            (
                sum(preference_scores)
                / len(preference_scores),
                0.15,
            )
        )

    if (
        match.eligibility_result
        .hard_stop_triggered
    ):
        return 0.0

    total_weight = sum(
        weight
        for _, weight in components
    )

    if total_weight == 0:
        return 0.0

    score = (
        sum(
            value * weight
            for value, weight in components
        )
        / total_weight
    )

    return _clamp_score(score)

def calculate_must_have_coverage(
    match: JobMatchResult,
) -> float:
    """
    Calculate coverage of REQUIRED requirements using the
    existing structured matching results.
    """

    required_ids = {
        requirement.requirement_id
        for requirement
        in match.requirements.requirements
        if (
            requirement.priority
            == RequirementPriority.REQUIRED
        )
    }

    # Some adverts do not explicitly mark requirements.
    # Missing structured must-haves should not be treated
    # as zero coverage.
    if not required_ids:
        return 100.0

    covered_ids: set[str] = set()

    for item in match.skill_result.matches:
        if item.requirement_id not in required_ids:
            continue

        if item.match_strength in {
            MatchStrength.EXACT,
            MatchStrength.STRONG_RELATED,
            MatchStrength.TRANSFERABLE,
        }:
            covered_ids.add(
                item.requirement_id
            )

    for item in match.experience_result.matches:
        if item.requirement_id not in required_ids:
            continue

        if float(item.score or 0.0) >= 60.0:
            covered_ids.add(
                item.requirement_id
            )

    coverage = (
        len(covered_ids)
        / len(required_ids)
        * 100.0
    )

    return _clamp_score(
        coverage
    )


def calculate_pre_application_scores(
    match: JobMatchResult,
) -> PreApplicationScores:
    required_items = (
        match.requirements.required_items
    )

    return PreApplicationScores(
        interview_fit_score=(
            calculate_interview_fit(
                match
            )
        ),
        must_have_coverage=(
            calculate_must_have_coverage(
                match
            )
        ),
        must_have_known=bool(
            required_items
        ),
    )


def calculate_ats_keyword_score(
    pack: ApplicationPack,
) -> float:
    """
    Use the actual tailored CV quality result.

    keyword_coverage is stored as 0.0–1.0,
    so convert it to a percentage.
    """

    for result in (
        pack.manifest.quality_results
    ):
        document_type = str(
            result.document_type
        )

        if document_type == "cv":
            return _clamp_score(
                float(
                    result.keyword_coverage
                    or 0.0
                )
                * 100.0
            )

    return 0.0


def calculate_claim_integrity(
    pack: ApplicationPack,
) -> float:
    """
    Claim integrity measures whether generated content contains
    blocked claims.

    REVIEW_REQUIRED means human verification is still needed;
    it does not automatically mean the claim is false.
    """

    checks = list(
        pack.manifest.claim_checks
    )

    if not checks:
        return 100.0

    blocked = sum(
        1
        for check in checks
        if check.status == ClaimStatus.BLOCKED
    )

    return _clamp_score(
        (
            len(checks) - blocked
        )
        / len(checks)
        * 100.0
    )

def calculate_claim_approval_readiness(
    pack: ApplicationPack,
) -> float:
    """
    Percentage of generated claims already approved without
    requiring human review.
    """

    checks = list(
        pack.manifest.claim_checks
    )

    if not checks:
        return 100.0

    approved = sum(
        1
        for check in checks
        if check.status == ClaimStatus.APPROVED
    )

    return _clamp_score(
        approved
        / len(checks)
        * 100.0
    )


def count_critical_red_flags(
    match: JobMatchResult,
    pack: ApplicationPack,
) -> int:
    red_flags = 0

    if (
        match.eligibility_result
        .hard_stop_triggered
    ):
        red_flags += 1

    if any(
        check.status == ClaimStatus.BLOCKED
        for check
        in pack.manifest.claim_checks
    ):
        red_flags += 1

    return red_flags


def calculate_final_application_scores(
    *,
    match: JobMatchResult,
    pack: ApplicationPack,
) -> FinalApplicationScores:
    pre = calculate_pre_application_scores(
        match
    )

    ats = calculate_ats_keyword_score(
        pack
    )

    integrity = calculate_claim_integrity(
        pack
    )

    approval_readiness = (
    calculate_claim_approval_readiness(
        pack
    )

    )

    red_flags = count_critical_red_flags(
        match,
        pack,
    )

    evaluation = classify_opportunity(
        ats_keyword_score=ats,
        interview_fit_score=(
            pre.interview_fit_score
        ),
        must_have_coverage=(
            pre.must_have_coverage
        ),
        claim_integrity=integrity,
        critical_red_flags=red_flags,
    )

    return FinalApplicationScores(
        ats_keyword_score=ats,
        interview_fit_score=(
        pre.interview_fit_score
        ),
        must_have_coverage=(
        pre.must_have_coverage
        ),
        must_have_known=(
        pre.must_have_known
        ),
        claim_integrity=integrity,
        claim_approval_readiness=(
            approval_readiness
            ),
        critical_red_flags=red_flags,
        evaluation=evaluation,
        )

def calculate_claim_approval_readiness(
    pack: ApplicationPack,
) -> float:
    """
    Percentage of claims already cleared without human review.
    """

    checks = list(
        pack.manifest.claim_checks
    )

    if not checks:
        return 100.0

    approved = sum(
        1
        for check in checks
        if check.status == ClaimStatus.APPROVED
    )

    return _clamp_score(
        approved
        / len(checks)
        * 100.0
    )
