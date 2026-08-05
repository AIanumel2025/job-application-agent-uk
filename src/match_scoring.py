"""Calculate transparent weighted job-match scores."""

from __future__ import annotations

from src.matching_models import (
    EligibilityResult,
    ExperienceMatchResult,
    MatchRecommendation,
    MatchScoreBreakdown,
    PreferenceFitResult,
    ScoreBand,
    ScoreComponent,
    SkillMatchResult,
)


DEFAULT_WEIGHTS = {
    "skills": 0.30,
    "experience": 0.25,
    "eligibility": 0.20,
    "preferences": 0.15,
    "evidence_quality": 0.10,
}


def score_band_for(score: float) -> ScoreBand:
    if score >= 85:
        return ScoreBand.STRONG
    if score >= 70:
        return ScoreBand.GOOD
    if score >= 55:
        return ScoreBand.POSSIBLE
    if score >= 40:
        return ScoreBand.WEAK
    return ScoreBand.POOR


def recommendation_for(
    score: float,
    eligibility: EligibilityResult,
) -> MatchRecommendation:
    if eligibility.hard_stop_triggered:
        return MatchRecommendation.NOT_ELIGIBLE

    if str(eligibility.overall_status) == "review_required":
        return MatchRecommendation.MANUAL_REVIEW

    if score >= 85:
        return MatchRecommendation.STRONG_MATCH
    if score >= 70:
        return MatchRecommendation.GOOD_MATCH
    if score >= 55:
        return MatchRecommendation.POSSIBLE_MATCH
    if score >= 40:
        return MatchRecommendation.WEAK_MATCH
    return MatchRecommendation.DO_NOT_APPLY


def calculate_match_score(
    *,
    skill_result: SkillMatchResult,
    experience_result: ExperienceMatchResult,
    eligibility_result: EligibilityResult,
    preference_result: PreferenceFitResult,
    evidence_quality_score: float = 70.0,
    weights: dict[str, float] | None = None,
) -> MatchScoreBreakdown:
    weights = dict(weights or DEFAULT_WEIGHTS)

    required = set(DEFAULT_WEIGHTS)
    missing = required - set(weights)
    if missing:
        raise ValueError(
            "matching weights are missing: " + ", ".join(sorted(missing))
        )

    total_weight = sum(weights.values())
    if abs(total_weight - 1.0) > 0.0001:
        raise ValueError("matching weights must sum to 1.0")

    values = {
        "skills": skill_result.score,
        "experience": experience_result.score,
        "eligibility": eligibility_result.score,
        "preferences": preference_result.overall_score,
        "evidence_quality": evidence_quality_score,
    }

    components = [
        ScoreComponent(
            name=name,
            raw_score=values[name],
            weight=weights[name],
            weighted_score=round(values[name] * weights[name], 4),
            explanation=f"{name.replace('_', ' ').title()} contribution.",
        )
        for name in DEFAULT_WEIGHTS
    ]

    total_score = round(
        sum(component.weighted_score for component in components),
        2,
    )

    if eligibility_result.hard_stop_triggered:
        total_score = min(total_score, 39.0)

    return MatchScoreBreakdown(
        components=components,
        total_score=total_score,
        score_band=score_band_for(total_score),
    )
