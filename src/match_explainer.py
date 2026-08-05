"""Generate readable, evidence-backed job-match explanations."""

from __future__ import annotations

from src.matching_models import (
    EligibilityResult,
    ExperienceEvidenceLevel,
    ExperienceMatchResult,
    MatchExplanation,
    MatchScoreBreakdown,
    MatchStrength,
    PreferenceFitResult,
    SkillMatchResult,
)


def build_match_explanation(
    *,
    skill_result: SkillMatchResult,
    experience_result: ExperienceMatchResult,
    eligibility_result: EligibilityResult,
    preference_result: PreferenceFitResult,
    score_breakdown: MatchScoreBreakdown,
) -> MatchExplanation:
    strengths: list[str] = []
    gaps: list[str] = []
    risks: list[str] = []
    eligibility_notes: list[str] = []
    actions: list[str] = []
    evidence_ids: list[str] = []

    for item in skill_result.matches:
        if item.match_strength in {
            MatchStrength.EXACT,
            MatchStrength.STRONG_RELATED,
        }:
            strengths.append(item.explanation)
        elif item.match_strength == MatchStrength.TRANSFERABLE:
            strengths.append(item.explanation)
        elif item.match_strength == MatchStrength.MISSING:
            gaps.append(item.explanation)

        evidence_ids.extend(
            evidence.evidence_id for evidence in item.evidence
        )

    for item in experience_result.matches:
        if item.evidence_level in {
            ExperienceEvidenceLevel.DIRECT,
            ExperienceEvidenceLevel.PROJECT_BASED,
            ExperienceEvidenceLevel.TRANSFERABLE,
        }:
            strengths.append(item.explanation)
        else:
            gaps.append(item.explanation)

        evidence_ids.extend(
            evidence.evidence_id for evidence in item.evidence
        )

    for check in eligibility_result.checks:
        eligibility_notes.append(check.explanation)
        if check.is_hard_stop and str(check.status) == "failed":
            risks.append(check.explanation)
        elif str(check.status) in {"review_required", "unclear"}:
            risks.append(check.explanation)

    if str(preference_result.salary.status) == "below_requirement":
        gaps.append(preference_result.salary.explanation)
    else:
        strengths.append(preference_result.salary.explanation)

    if str(preference_result.location.status) == "mismatch":
        gaps.append(preference_result.location.explanation)
    else:
        strengths.append(preference_result.location.explanation)

    if skill_result.missing_required:
        actions.append(
            "Review the missing required skills before deciding to apply."
        )

    if eligibility_result.hard_stop_triggered:
        actions.append(
            "Do not proceed unless the eligibility conflict is resolved."
        )
    elif any(
        str(check.status) in {"review_required", "unclear"}
        for check in eligibility_result.checks
    ):
        actions.append(
            "Confirm unclear sponsorship, security, or work-authorisation details."
        )

    if not actions:
        actions.append("Proceed to application-material tailoring.")

    summary = (
        f"Overall match score: {score_breakdown.total_score:.0f}%. "
        f"Band: {str(score_breakdown.score_band).replace('_', ' ')}."
    )

    return MatchExplanation(
        summary=summary,
        strengths=list(dict.fromkeys(strengths)),
        gaps=list(dict.fromkeys(gaps)),
        risks=list(dict.fromkeys(risks)),
        eligibility_notes=list(dict.fromkeys(eligibility_notes)),
        recommended_actions=list(dict.fromkeys(actions)),
        evidence_ids=list(dict.fromkeys(evidence_ids)),
    )
