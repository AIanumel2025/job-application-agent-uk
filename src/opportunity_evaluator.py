"""Evaluate jobs across ATS, interview fit, coverage, and claim integrity."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from src.opportunity_thresholds import DEFAULT_THRESHOLDS


class OpportunityTier(StrEnum):
    BEST_OPPORTUNITY = "best_opportunity"
    HIGH_QUALITY = "high_quality"
    TAILOR_THEN_APPLY = "tailor_then_apply"
    SELECTIVE_REVIEW = "selective_review"
    REJECT = "reject"


@dataclass(slots=True)
class OpportunityEvaluation:
    ats_keyword_score: float
    interview_fit_score: float
    must_have_coverage: float
    claim_integrity: float
    critical_red_flags: int
    tier: OpportunityTier


def classify_opportunity(
    *,
    ats_keyword_score: float,
    interview_fit_score: float,
    must_have_coverage: float,
    claim_integrity: float,
    critical_red_flags: int = 0,
) -> OpportunityEvaluation:
    """Classify a job using the agent's application thresholds."""

    t = DEFAULT_THRESHOLDS

    if claim_integrity < t.required_claim_integrity:
        tier = OpportunityTier.REJECT

    elif critical_red_flags > 0:
        tier = OpportunityTier.REJECT

    elif (
        ats_keyword_score >= t.best_ats
        and interview_fit_score >= t.best_interview_fit
        and must_have_coverage >= t.best_must_have
    ):
        tier = OpportunityTier.BEST_OPPORTUNITY

    elif (
        ats_keyword_score >= t.high_quality_ats
        and interview_fit_score >= t.high_quality_interview_fit
        and must_have_coverage >= t.high_quality_must_have
    ):
        tier = OpportunityTier.HIGH_QUALITY

    elif (
        interview_fit_score >= t.high_quality_interview_fit
        and must_have_coverage >= t.high_quality_must_have
        and ats_keyword_score < t.high_quality_ats
    ):
        tier = OpportunityTier.TAILOR_THEN_APPLY

    elif (
        interview_fit_score >= 65.0
        and must_have_coverage >= 60.0
    ):
        tier = OpportunityTier.SELECTIVE_REVIEW

    else:
        tier = OpportunityTier.REJECT

    return OpportunityEvaluation(
        ats_keyword_score=round(ats_keyword_score, 2),
        interview_fit_score=round(interview_fit_score, 2),
        must_have_coverage=round(must_have_coverage, 2),
        claim_integrity=round(claim_integrity, 2),
        critical_red_flags=critical_red_flags,
        tier=tier,
    )
