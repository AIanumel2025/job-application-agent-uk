"""Choose the safest and most relevant wording from reference CVs."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from src.cv_content_mapper import CVWordingCandidate
from src.matching_models import JobMatchResult


@dataclass(slots=True)
class SelectedCVWording:
    text: str
    source_cv_key: str
    source_file: str
    source_type: str
    matched_evidence_ids: list[str]
    job_relevance_score: float
    evidence_relevance_score: float
    combined_score: float
    review_required: bool
    reasons: list[str]


def _normalise(value: str) -> str:
    return " ".join(
        value.casefold()
        .replace("-", " ")
        .replace("_", " ")
        .replace("/", " ")
        .split()
    )


def _job_text(match: JobMatchResult) -> str:
    return " ".join(
        [
            match.job_title,
            match.company,
            *[
                requirement.text
                for requirement in match.requirements.requirements
            ],
        ]
    )


def _job_relevance(text: str, match: JobMatchResult) -> float:
    text_n = _normalise(text)
    job_n = _normalise(_job_text(match))

    text_tokens = set(text_n.split())
    job_tokens = set(job_n.split())

    overlap = len(text_tokens & job_tokens) / max(len(text_tokens), 1)
    sequence = SequenceMatcher(None, text_n, job_n).ratio()

    return round(max(overlap, sequence), 4)


def select_cv_wording(
    candidates: list[CVWordingCandidate],
    match: JobMatchResult,
    *,
    maximum_items: int = 12,
    allow_review_required: bool = False,
) -> list[SelectedCVWording]:
    """Select reusable reference wording for one vacancy."""

    selected: list[SelectedCVWording] = []

    for candidate in candidates:
        if not candidate.approved_for_reuse:
            continue

        if candidate.review_required and not allow_review_required:
            continue

        job_score = _job_relevance(candidate.text, match)
        combined = round(
            candidate.relevance_score * 0.60
            + job_score * 0.40,
            4,
        )

        selected.append(
            SelectedCVWording(
                text=candidate.text,
                source_cv_key=candidate.source_cv_key,
                source_file=candidate.source_file,
                source_type=candidate.source_type,
                matched_evidence_ids=list(candidate.matched_evidence_ids),
                job_relevance_score=job_score,
                evidence_relevance_score=candidate.relevance_score,
                combined_score=combined,
                review_required=candidate.review_required,
                reasons=list(candidate.reasons),
            )
        )

    selected.sort(
        key=lambda item: (
            item.combined_score,
            item.evidence_relevance_score,
            item.job_relevance_score,
        ),
        reverse=True,
    )

    deduped: list[SelectedCVWording] = []
    seen: set[str] = set()

    for item in selected:
        key = _normalise(item.text)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= maximum_items:
            break

    return deduped
