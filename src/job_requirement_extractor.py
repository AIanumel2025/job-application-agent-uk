"""Extract structured requirements from normalised job vacancies."""

from __future__ import annotations

import re
from typing import Iterable
from uuid import uuid5, NAMESPACE_URL

from src.job_models import NormalisedJob
from src.matching_models import (
    ExtractedJobRequirements,
    JobRequirement,
    RequirementCategory,
    RequirementPriority,
)


_SECTION_SPLIT_RE = re.compile(r"[\r\n]+")
_BULLET_RE = re.compile(r"^[\s•*·\-\u2022]+")
_YEARS_RE = re.compile(
    r"\b(?P<years>\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\b",
    re.I,
)
_DEGREE_RE = re.compile(
    r"\b(?:bachelor'?s?|master'?s?|msc|bsc|phd|doctorate|degree)\b",
    re.I,
)


REQUIRED_MARKERS = (
    "required",
    "must have",
    "must be",
    "essential",
    "you will need",
    "minimum",
    "mandatory",
)

PREFERRED_MARKERS = (
    "preferred",
    "desirable",
    "nice to have",
    "advantageous",
    "bonus",
    "ideally",
)

SKILL_TERMS = (
    "python",
    "sql",
    "postgresql",
    "power bi",
    "tableau",
    "aws",
    "azure",
    "gcp",
    "docker",
    "kubernetes",
    "git",
    "github actions",
    "databricks",
    "spark",
    "pandas",
    "numpy",
    "machine learning",
    "deep learning",
    "nlp",
    "natural language processing",
    "llm",
    "large language model",
    "rag",
    "retrieval augmented generation",
    "data engineering",
    "data modelling",
    "data visualization",
    "data visualisation",
    "ci/cd",
    "mlops",
    "api",
    "rest",
    "linux",
)

CERTIFICATION_TERMS = (
    "certification",
    "certified",
    "aws certified",
    "azure certification",
    "pl-300",
    "security clearance",
)

SECURITY_TERMS = (
    "security clearance",
    "sc clearance",
    "dv clearance",
    "developed vetting",
    "uk national only",
    "british citizen only",
    "sole uk national",
)

SPONSORSHIP_TERMS = (
    "visa sponsorship",
    "sponsorship",
    "right to work",
    "without sponsorship",
    "skilled worker",
)


def _clean_line(value: str) -> str:
    value = _BULLET_RE.sub("", value)
    return " ".join(value.split()).strip(" :;")


def _priority_for_text(text: str) -> RequirementPriority:
    lowered = text.casefold()

    if any(marker in lowered for marker in REQUIRED_MARKERS):
        return RequirementPriority.REQUIRED

    if any(marker in lowered for marker in PREFERRED_MARKERS):
        return RequirementPriority.PREFERRED

    return RequirementPriority.UNCLEAR


def _category_for_text(text: str) -> RequirementCategory:
    lowered = text.casefold()

    if any(term in lowered for term in SECURITY_TERMS):
        return RequirementCategory.SECURITY

    if any(term in lowered for term in SPONSORSHIP_TERMS):
        return RequirementCategory.ELIGIBILITY

    if _YEARS_RE.search(text):
        return RequirementCategory.EXPERIENCE

    if _DEGREE_RE.search(text):
        return RequirementCategory.EDUCATION

    if any(term in lowered for term in CERTIFICATION_TERMS):
        return RequirementCategory.CERTIFICATION

    if any(term in lowered for term in SKILL_TERMS):
        return RequirementCategory.SKILL

    return RequirementCategory.OTHER


def _normalised_value(text: str, category: RequirementCategory) -> str | None:
    lowered = text.casefold()

    if category == RequirementCategory.SKILL:
        matches = [term for term in SKILL_TERMS if term in lowered]
        return ", ".join(matches) if matches else None

    if category == RequirementCategory.EXPERIENCE:
        match = _YEARS_RE.search(text)
        return match.group("years") if match else None

    if category == RequirementCategory.EDUCATION:
        match = _DEGREE_RE.search(text)
        return match.group(0).lower() if match else None

    return None


def _iter_candidate_lines(job: NormalisedJob) -> Iterable[tuple[str, str]]:
    for section_name, values in (
        ("requirements", job.requirements),
        ("preferred_skills", job.preferred_skills),
        ("responsibilities", job.responsibilities),
    ):
        for value in values:
            for line in _SECTION_SPLIT_RE.split(value):
                cleaned = _clean_line(line)
                if cleaned:
                    yield section_name, cleaned

    for line in _SECTION_SPLIT_RE.split(job.description):
        cleaned = _clean_line(line)
        if cleaned:
            yield "description", cleaned


def extract_job_requirements(
    job: NormalisedJob,
) -> ExtractedJobRequirements:
    """Extract explicit requirements from a normalised vacancy."""

    requirements: list[JobRequirement] = []
    seen: set[str] = set()
    minimum_years: float | None = None
    required_degree_level: str | None = None
    required_certifications: list[str] = []
    required_tools: list[str] = []
    sponsorship_statement: str | None = None
    security_statement: str | None = None

    for source_section, text in _iter_candidate_lines(job):
        dedupe_key = text.casefold()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        priority = (
            RequirementPriority.PREFERRED
            if source_section == "preferred_skills"
            else _priority_for_text(text)
        )
        category = _category_for_text(text)
        normalised = _normalised_value(text, category)

        requirement_id = str(
            uuid5(
                NAMESPACE_URL,
                f"{job.job_id}|{source_section}|{dedupe_key}",
            )
        )

        requirements.append(
            JobRequirement(
                requirement_id=requirement_id,
                category=category,
                priority=priority,
                text=text,
                normalised_value=normalised,
                source_section=source_section,
                confidence=0.95 if source_section != "description" else 0.75,
                evidence_text=text,
            )
        )

        if category == RequirementCategory.EXPERIENCE:
            match = _YEARS_RE.search(text)
            if match:
                years = float(match.group("years"))
                minimum_years = max(minimum_years or 0.0, years)

        if category == RequirementCategory.EDUCATION and priority == RequirementPriority.REQUIRED:
            required_degree_level = normalised or text

        if category == RequirementCategory.CERTIFICATION and priority == RequirementPriority.REQUIRED:
            required_certifications.append(text)

        if category == RequirementCategory.SKILL and normalised:
            required_tools.extend(
                item.strip()
                for item in normalised.split(",")
                if item.strip()
            )

        if category == RequirementCategory.ELIGIBILITY and sponsorship_statement is None:
            sponsorship_statement = text

        if category == RequirementCategory.SECURITY and security_statement is None:
            security_statement = text

    return ExtractedJobRequirements(
        job_id=job.job_id,
        requirements=requirements,
        minimum_years_experience=minimum_years,
        required_degree_level=required_degree_level,
        required_certifications=list(dict.fromkeys(required_certifications)),
        required_tools=list(dict.fromkeys(required_tools)),
        required_industries=[],
        sponsorship_statement=sponsorship_statement,
        security_statement=security_statement,
        extraction_notes=[],
    )
