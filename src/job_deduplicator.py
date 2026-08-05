"""Detect duplicate or near-duplicate job vacancies."""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Iterable

from src.job_models import DuplicateMatch, NormalisedJob


@dataclass(slots=True)
class DeduplicationResult:
    """Result of comparing one incoming vacancy against existing jobs."""

    is_duplicate: bool
    best_match: DuplicateMatch | None = None
    all_matches: list[DuplicateMatch] = field(default_factory=list)


def _similarity(left: str | None, right: str | None) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left.lower(), right.lower()).ratio()


def compare_jobs(
    incoming: NormalisedJob,
    existing: NormalisedJob,
) -> DuplicateMatch | None:
    """Compare two vacancies and return a match when evidence is strong."""

    matching_fields: list[str] = []
    scores: list[float] = []

    if incoming.canonical_url == existing.canonical_url:
        matching_fields.append("canonical_url")
        scores.append(1.0)

    if (
        incoming.source_job_id
        and existing.source_job_id
        and incoming.source_job_id == existing.source_job_id
        and incoming.source == existing.source
    ):
        matching_fields.append("source_job_id")
        scores.append(1.0)

    if (
        incoming.description_hash
        and existing.description_hash
        and incoming.description_hash == existing.description_hash
    ):
        matching_fields.append("description_hash")
        scores.append(1.0)

    company_score = _similarity(
        incoming.company_normalised,
        existing.company_normalised,
    )
    title_score = _similarity(
        incoming.title_normalised,
        existing.title_normalised,
    )

    if company_score >= 0.92:
        matching_fields.append("company")
        scores.append(company_score)

    if title_score >= 0.88:
        matching_fields.append("title")
        scores.append(title_score)

    incoming_city = incoming.location.city if incoming.location else None
    existing_city = existing.location.city if existing.location else None
    city_score = _similarity(incoming_city, existing_city)

    if city_score >= 0.90:
        matching_fields.append("location")
        scores.append(city_score)

    exact_signal = any(
        field in matching_fields
        for field in ("canonical_url", "source_job_id", "description_hash")
    )

    strong_composite = (
        company_score >= 0.92
        and title_score >= 0.88
        and (
            city_score >= 0.90
            or incoming_city is None
            or existing_city is None
        )
    )

    if not exact_signal and not strong_composite:
        return None

    if exact_signal:
        confidence = 1.0
    else:
        confidence = round(
            (company_score * 0.4)
            + (title_score * 0.45)
            + (city_score * 0.15),
            4,
        )

    reason = (
        "exact duplicate signal"
        if exact_signal
        else "strong company, title, and location similarity"
    )

    return DuplicateMatch(
        incoming_job_id=incoming.job_id,
        existing_job_id=existing.job_id,
        reason=reason,
        confidence=confidence,
        matching_fields=matching_fields,
    )


def find_duplicate(
    incoming: NormalisedJob,
    existing_jobs: Iterable[NormalisedJob],
) -> DeduplicationResult:
    """Find the strongest duplicate match for one incoming job."""

    matches: list[DuplicateMatch] = []

    for existing in existing_jobs:
        match = compare_jobs(incoming, existing)
        if match is not None:
            matches.append(match)

    matches.sort(key=lambda item: item.confidence, reverse=True)

    return DeduplicationResult(
        is_duplicate=bool(matches),
        best_match=matches[0] if matches else None,
        all_matches=matches,
    )
