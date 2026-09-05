"""Policy gate for deciding application quality and priority."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from src.live_opportunity_scores import (
    FinalApplicationScores,
)


class ApplicationQualityTier(StrEnum):
    BEST_OPPORTUNITY = "best_opportunity"
    HIGH_QUALITY = "high_quality"
    TAILOR_THEN_APPLY = "tailor_then_apply"
    SELECTIVE_REVIEW = "selective_review"
    DO_NOT_PRIORITISE = "do_not_prioritise"


@dataclass(slots=True)
class ApplicationQualityDecision:
    tier: ApplicationQualityTier
    reasons: list[str]
    eligible_for_priority_application: bool


def classify_application_quality(
    scores: FinalApplicationScores,
) -> ApplicationQualityDecision:
    reasons: list[str] = []

    # Hard safety gate
    if (
        scores.critical_red_flags > 0
        or scores.claim_integrity < 100.0
    ):
        return ApplicationQualityDecision(
            tier=ApplicationQualityTier.DO_NOT_PRIORITISE,
            reasons=[
                "Application failed a critical integrity or eligibility gate."
            ],
            eligible_for_priority_application=False,
        )

    # Best opportunity
    if (
        scores.must_have_known
        and scores.ats_keyword_score >= 92.0
        and scores.interview_fit_score >= 90.0
        and scores.must_have_coverage >= 90.0
        and scores.claim_integrity == 100.0
    ):
        return ApplicationQualityDecision(
            tier=ApplicationQualityTier.BEST_OPPORTUNITY,
            reasons=[
                "Application exceeds the best-opportunity thresholds."
            ],
            eligible_for_priority_application=True,
        )

    # High quality
    if (
        scores.must_have_known
        and scores.ats_keyword_score >= 85.0
        and scores.interview_fit_score >= 85.0
        and scores.must_have_coverage >= 80.0
        and scores.claim_integrity == 100.0
    ):
        return ApplicationQualityDecision(
            tier=ApplicationQualityTier.HIGH_QUALITY,
            reasons=[
                "Application meets all high-quality thresholds."
            ],
            eligible_for_priority_application=True,
        )

    # Tailor then apply
    if (
        scores.interview_fit_score >= 85.0
        and scores.ats_keyword_score < 85.0
        and scores.claim_integrity == 100.0
    ):
        reasons.append(
            "Interview fit is strong but ATS keyword alignment needs tailoring."
        )

        if not scores.must_have_known:
            reasons.append(
                "Must-have coverage could not be confidently determined."
            )

        return ApplicationQualityDecision(
            tier=ApplicationQualityTier.TAILOR_THEN_APPLY,
            reasons=reasons,
            eligible_for_priority_application=False,
        )

    # Selective review
    if (
        scores.interview_fit_score >= 70.0
        and scores.ats_keyword_score >= 65.0
        and scores.claim_integrity == 100.0
    ):
        reasons.append(
            "Opportunity is plausible but remains below the high-quality thresholds."
        )

        if not scores.must_have_known:
            reasons.append(
                "Must-have coverage is currently unknown."
            )

        return ApplicationQualityDecision(
            tier=ApplicationQualityTier.SELECTIVE_REVIEW,
            reasons=reasons,
            eligible_for_priority_application=False,
        )

    return ApplicationQualityDecision(
        tier=ApplicationQualityTier.DO_NOT_PRIORITISE,
        reasons=[
            "Opportunity is below the current application-priority thresholds."
        ],
        eligible_for_priority_application=False,
    )
