"""Compare extracted job skills against the career matching profile."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Iterable

from src.matching_models import (
    CareerEvidence,
    CareerMatchingProfile,
    ExtractedJobRequirements,
    MatchStrength,
    RequirementCategory,
    RequirementPriority,
    SkillMatch,
    SkillMatchResult,
)


SKILL_ALIASES: dict[str, set[str]] = {
    "sql": {"postgresql", "mysql", "sqlite", "sql server", "relational database"},
    "postgresql": {"sql", "relational database"},
    "aws": {"amazon web services", "s3", "athena", "lambda", "ec2"},
    "power bi": {"business intelligence", "dax", "power query"},
    "python": {"pandas", "numpy", "scikit-learn", "python programming"},
    "machine learning": {
        "supervised learning",
        "classification",
        "regression",
        "scikit-learn",
        "ml",
    },
    "data engineering": {
        "etl",
        "data pipeline",
        "data pipelines",
        "data ingestion",
        "data warehouse",
    },
    "mlops": {
        "model deployment",
        "model monitoring",
        "ci/cd",
        "github actions",
        "docker",
    },
    "github actions": {"ci/cd", "continuous integration", "automation"},
    "docker": {"containerisation", "containerization", "containers"},
    "nlp": {"natural language processing", "text analytics"},
    "llm": {"large language model", "large language models", "generative ai"},
    "rag": {"retrieval augmented generation", "retrieval-augmented generation"},
}


def _normalise(value: str) -> str:
    return " ".join(
        value.casefold()
        .replace("/", " ")
        .replace("_", " ")
        .replace("-", " ")
        .split()
    )


def _candidate_terms(profile: CareerMatchingProfile) -> list[str]:
    return list(dict.fromkeys(profile.skills + profile.tools))


def _skill_evidence(
    required_skill: str,
    profile: CareerMatchingProfile,
) -> list[CareerEvidence]:
    required = _normalise(required_skill)
    output: list[CareerEvidence] = []

    for evidence in profile.evidence:
        haystack = _normalise(f"{evidence.title} {evidence.description}")
        if required in haystack:
            output.append(evidence)

    return output[:5]


def _related(required: str, candidate: str) -> bool:
    required_n = _normalise(required)
    candidate_n = _normalise(candidate)

    aliases = {_normalise(item) for item in SKILL_ALIASES.get(required_n, set())}
    reverse_aliases = {
        _normalise(item)
        for item in SKILL_ALIASES.get(candidate_n, set())
    }

    direct_alias_match = (
        candidate_n in aliases
        or required_n in reverse_aliases
    )

    phrase_alias_match = any(
        alias == candidate_n
        or alias in candidate_n
        or candidate_n in alias
        for alias in aliases
    )

    reverse_phrase_match = any(
        alias == required_n
        or alias in required_n
        or required_n in alias
        for alias in reverse_aliases
    )

    return direct_alias_match or phrase_alias_match or reverse_phrase_match


def _best_match(
    required_skill: str,
    candidate_skills: Iterable[str],
) -> tuple[MatchStrength, str | None, float]:
    required_n = _normalise(required_skill)
    best_candidate: str | None = None
    best_score = 0.0
    best_strength = MatchStrength.MISSING

    for candidate in candidate_skills:
        candidate_n = _normalise(candidate)

        if required_n == candidate_n:
            return MatchStrength.EXACT, candidate, 1.0

        if _related(required_skill, candidate):
            score = 0.9
            if score > best_score:
                best_strength = MatchStrength.STRONG_RELATED
                best_candidate = candidate
                best_score = score
            continue

        ratio = SequenceMatcher(None, required_n, candidate_n).ratio()

        if ratio >= 0.82 and ratio > best_score:
            best_strength = MatchStrength.STRONG_RELATED
            best_candidate = candidate
            best_score = ratio
        elif ratio >= 0.62 and ratio > best_score:
            best_strength = MatchStrength.TRANSFERABLE
            best_candidate = candidate
            best_score = ratio

    return best_strength, best_candidate, round(best_score, 4)


def _extract_skills_from_requirement(value: str | None, fallback: str) -> list[str]:
    if value:
        return [
            item.strip()
            for item in value.split(",")
            if item.strip()
        ]
    return [fallback]


def match_skills(
    requirements: ExtractedJobRequirements,
    profile: CareerMatchingProfile,
) -> SkillMatchResult:
    """Compare skill requirements with candidate skills and evidence."""

    matches: list[SkillMatch] = []
    candidate_skills = _candidate_terms(profile)

    for requirement in requirements.requirements:
        if requirement.category != RequirementCategory.SKILL:
            continue

        required_skills = _extract_skills_from_requirement(
            requirement.normalised_value,
            requirement.text,
        )

        for required_skill in required_skills:
            strength, matched_skill, similarity = _best_match(
                required_skill,
                candidate_skills,
            )
            evidence = _skill_evidence(
                matched_skill or required_skill,
                profile,
            )

            if strength == MatchStrength.EXACT:
                explanation = f"Exact match found for {required_skill}."
            elif strength == MatchStrength.STRONG_RELATED:
                explanation = (
                    f"{required_skill} is strongly related to "
                    f"{matched_skill} in the career profile."
                )
            elif strength == MatchStrength.TRANSFERABLE:
                explanation = (
                    f"{matched_skill} offers transferable evidence for "
                    f"{required_skill}, but the match is not direct."
                )
            else:
                explanation = (
                    f"No sufficient evidence was found for {required_skill}."
                )

            matches.append(
                SkillMatch(
                    requirement_id=requirement.requirement_id,
                    required_skill=required_skill,
                    priority=requirement.priority,
                    match_strength=strength,
                    matched_skill=matched_skill,
                    similarity_score=similarity,
                    evidence=evidence,
                    explanation=explanation,
                )
            )

    if not matches:
        return SkillMatchResult(matches=[], score=0.0)

    weights = {
        MatchStrength.EXACT: 1.0,
        MatchStrength.STRONG_RELATED: 0.85,
        MatchStrength.TRANSFERABLE: 0.6,
        MatchStrength.WEAK: 0.3,
        MatchStrength.MISSING: 0.0,
        MatchStrength.NOT_APPLICABLE: 0.0,
    }

    total_weight = 0.0
    earned = 0.0

    for item in matches:
        priority_weight = (
            1.5
            if item.priority == RequirementPriority.REQUIRED
            else 1.0
        )
        total_weight += priority_weight
        earned += weights[item.match_strength] * priority_weight

    result = SkillMatchResult(
        matches=matches,
        score=round((earned / total_weight) * 100, 2)
        if total_weight
        else 0.0,
    )
    result.recalculate_counts()
    return result
