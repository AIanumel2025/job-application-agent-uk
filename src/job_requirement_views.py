"""Derived scoring views for extracted job requirements."""

from __future__ import annotations

from dataclasses import dataclass

from src.matching_models import (
    ExtractedJobRequirements,
    RequirementCategory,
    RequirementPriority,
)


@dataclass(slots=True)
class JobRequirementView:
    keywords: list[str]
    required_skills: list[str]
    must_haves: list[str]
    nice_to_haves: list[str]
    domain_terms: list[str]
    required_years_experience: float | None


DOMAIN_TERMS = (
    "ai",
    "artificial intelligence",
    "machine learning",
    "data engineering",
    "data science",
    "analytics engineering",
    "document ai",
    "document intelligence",
    "llm",
    "rag",
    "ai agents",
    "agentic ai",
    "automation",
    "workflow orchestration",
    "data pipelines",
    "cloud",
    "mlops",
)


def _deduplicate(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []

    for value in values:
        cleaned = str(value).strip()

        if not cleaned:
            continue

        key = cleaned.casefold()

        if key in seen:
            continue

        seen.add(key)
        output.append(cleaned)

    return output


def build_job_requirement_view(
    extracted: ExtractedJobRequirements,
) -> JobRequirementView:
    """Convert structured extracted requirements into scoring-friendly views."""

    required_skills: list[str] = []
    must_haves: list[str] = []
    nice_to_haves: list[str] = []
    domain_terms: list[str] = []

    for requirement in extracted.requirements:
        text = requirement.text or ""
        lowered = text.casefold()

        if requirement.priority == RequirementPriority.REQUIRED:
            must_haves.append(text)

        elif requirement.priority == RequirementPriority.PREFERRED:
            nice_to_haves.append(text)

        if requirement.category == RequirementCategory.SKILL:
            if requirement.normalised_value:
                required_skills.extend(
                    item.strip()
                    for item in requirement.normalised_value.split(",")
                    if item.strip()
                )

        for term in DOMAIN_TERMS:
            if term in lowered:
                domain_terms.append(term)

    keywords = _deduplicate(
        list(extracted.required_tools)
        + required_skills
        + domain_terms
    )

    return JobRequirementView(
        keywords=_deduplicate(keywords),
        required_skills=_deduplicate(required_skills),
        must_haves=_deduplicate(must_haves),
        nice_to_haves=_deduplicate(nice_to_haves),
        domain_terms=_deduplicate(domain_terms),
        required_years_experience=extracted.minimum_years_experience,
    )
