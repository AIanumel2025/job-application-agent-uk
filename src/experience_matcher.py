"""Match experience requirements against career evidence."""

from __future__ import annotations

from difflib import SequenceMatcher

from src.matching_models import (
    CareerEvidence,
    CareerMatchingProfile,
    EvidenceType,
    ExperienceEvidenceLevel,
    ExperienceMatch,
    ExperienceMatchResult,
    ExtractedJobRequirements,
    RequirementCategory,
    RequirementPriority,
)


def _normalise(value: str) -> str:
    return " ".join(
        value.casefold()
        .replace("/", " ")
        .replace("_", " ")
        .replace("-", " ")
        .split()
    )


def _relevance(
    requirement_text: str,
    evidence: CareerEvidence,
) -> float:
    requirement = _normalise(requirement_text)
    candidate = _normalise(f"{evidence.title} {evidence.description}")

    if requirement in candidate or candidate in requirement:
        return 1.0

    requirement_tokens = set(requirement.split())
    candidate_tokens = set(candidate.split())

    overlap = (
        len(requirement_tokens & candidate_tokens)
        / max(len(requirement_tokens), 1)
    )
    sequence = SequenceMatcher(None, requirement, candidate).ratio()

    return round(max(overlap, sequence), 4)


def _classify_evidence(evidence: CareerEvidence) -> ExperienceEvidenceLevel:
    if evidence.evidence_type == EvidenceType.EXPERIENCE:
        return ExperienceEvidenceLevel.DIRECT
    if evidence.evidence_type == EvidenceType.PROJECT:
        return ExperienceEvidenceLevel.PROJECT_BASED
    if evidence.evidence_type == EvidenceType.EDUCATION:
        return ExperienceEvidenceLevel.ACADEMIC
    return ExperienceEvidenceLevel.TRANSFERABLE


def match_experience(
    requirements: ExtractedJobRequirements,
    profile: CareerMatchingProfile,
) -> ExperienceMatchResult:
    """Match experience requirements to the strongest available evidence."""

    experience_requirements = [
        item
        for item in requirements.requirements
        if item.category in {
            RequirementCategory.EXPERIENCE,
            RequirementCategory.INDUSTRY,
            RequirementCategory.OTHER,
        }
        and (
            item.category != RequirementCategory.OTHER
            or "experience" in item.text.casefold()
        )
    ]

    matches: list[ExperienceMatch] = []

    for requirement in experience_requirements:
        ranked = sorted(
            (
                (_relevance(requirement.text, evidence), evidence)
                for evidence in profile.evidence
                if evidence.approved_for_application
            ),
            key=lambda item: item[0],
            reverse=True,
        )

        best_score, best_evidence = ranked[0] if ranked else (0.0, None)

        if best_evidence is None or best_score < 0.25:
            level = ExperienceEvidenceLevel.INSUFFICIENT
            evidence_list: list[CareerEvidence] = []
            score = 0.0
            explanation = "No sufficiently relevant experience evidence was found."
        else:
            level = _classify_evidence(best_evidence)
            evidence_list = [
                evidence
                for relevance, evidence in ranked[:3]
                if relevance >= max(best_score - 0.15, 0.25)
            ]

            level_multiplier = {
                ExperienceEvidenceLevel.DIRECT: 1.0,
                ExperienceEvidenceLevel.PROJECT_BASED: 0.8,
                ExperienceEvidenceLevel.TRANSFERABLE: 0.7,
                ExperienceEvidenceLevel.ACADEMIC: 0.55,
                ExperienceEvidenceLevel.INSUFFICIENT: 0.0,
            }[level]
            score = round(best_score * level_multiplier * 100, 2)
            explanation = (
                f"Best evidence is {level.value.replace('_', ' ')}: "
                f"{best_evidence.title}."
            )

        matches.append(
            ExperienceMatch(
                requirement_id=requirement.requirement_id,
                requirement_text=requirement.text,
                priority=requirement.priority,
                evidence_level=level,
                years_required=(
                    float(requirement.normalised_value)
                    if requirement.normalised_value
                    and requirement.normalised_value.replace(".", "", 1).isdigit()
                    else None
                ),
                years_evidenced=profile.years_of_experience,
                evidence=evidence_list,
                score=score,
                explanation=explanation,
            )
        )

    if not matches:
        return ExperienceMatchResult(matches=[], score=0.0)

    total_weight = 0.0
    earned = 0.0

    for item in matches:
        priority_weight = (
            1.5
            if item.priority == RequirementPriority.REQUIRED
            else 1.0
        )
        total_weight += priority_weight
        earned += item.score * priority_weight

    return ExperienceMatchResult(
        matches=matches,
        score=round(earned / total_weight, 2) if total_weight else 0.0,
        direct_matches=sum(
            item.evidence_level == ExperienceEvidenceLevel.DIRECT
            for item in matches
        ),
        transferable_matches=sum(
            item.evidence_level == ExperienceEvidenceLevel.TRANSFERABLE
            for item in matches
        ),
        project_based_matches=sum(
            item.evidence_level == ExperienceEvidenceLevel.PROJECT_BASED
            for item in matches
        ),
        insufficient_matches=sum(
            item.evidence_level == ExperienceEvidenceLevel.INSUFFICIENT
            for item in matches
        ),
    )
