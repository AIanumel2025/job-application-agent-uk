"""Map wording from registered CV documents to verified career evidence."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re

from src.cv_template_loader import LoadedCVDocument
from src.matching_models import CareerEvidence


_BULLET_RE = re.compile(r"^[\s•*·\-\u2022]+")
_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?%?\b")


@dataclass(slots=True)
class CVWordingCandidate:
    source_cv_key: str
    source_file: str
    text: str
    source_type: str
    matched_evidence_ids: list[str]
    relevance_score: float
    contains_numeric_claim: bool
    numeric_claim_supported: bool
    approved_for_reuse: bool
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


def _clean_line(value: str) -> str:
    return " ".join(_BULLET_RE.sub("", value).split()).strip()


def _looks_like_heading(value: str) -> bool:
    cleaned = value.strip()
    if not cleaned:
        return False
    letters = [char for char in cleaned if char.isalpha()]
    if not letters:
        return False
    uppercase_ratio = sum(char.isupper() for char in letters) / len(letters)
    return uppercase_ratio >= 0.80 and len(cleaned.split()) <= 8


def _candidate_lines(document: LoadedCVDocument) -> list[tuple[str, str]]:
    output: list[tuple[str, str]] = []
    current_section = "general"

    for paragraph in document.paragraphs:
        cleaned = _clean_line(paragraph)
        if not cleaned:
            continue

        if _looks_like_heading(cleaned):
            current_section = _normalise(cleaned).replace(" ", "_")
            continue

        if cleaned.startswith("[") and cleaned.endswith("]"):
            continue

        output.append((current_section, cleaned))

    for row in document.table_rows:
        cleaned = " | ".join(cell.strip() for cell in row if cell.strip())
        if cleaned:
            output.append(("table", cleaned))

    return output


def _evidence_similarity(
    text: str,
    evidence: CareerEvidence,
) -> float:
    text_n = _normalise(text)
    evidence_n = _normalise(f"{evidence.title} {evidence.description}")

    if text_n in evidence_n or evidence_n in text_n:
        return 1.0

    text_tokens = set(text_n.split())
    evidence_tokens = set(evidence_n.split())

    overlap = len(text_tokens & evidence_tokens) / max(len(text_tokens), 1)
    sequence = SequenceMatcher(None, text_n, evidence_n).ratio()

    return round(max(overlap, sequence), 4)


def _numeric_claim_supported(
    text: str,
    matched_evidence: list[CareerEvidence],
) -> bool:
    numbers = set(_NUMBER_RE.findall(text))
    if not numbers:
        return True

    evidence_numbers: set[str] = set()
    for item in matched_evidence:
        evidence_numbers.update(_NUMBER_RE.findall(item.description))
        evidence_numbers.update(_NUMBER_RE.findall(item.title))

    return numbers.issubset(evidence_numbers)


def map_reference_cv_to_evidence(
    document: LoadedCVDocument,
    evidence: list[CareerEvidence],
    *,
    minimum_similarity: float = 0.22,
) -> list[CVWordingCandidate]:
    """Map reference-CV wording to approved career evidence.

    Wording is reusable only when related evidence exists and any numeric claim
    is supported by that evidence.
    """

    candidates: list[CVWordingCandidate] = []

    approved_evidence = [
        item
        for item in evidence
        if item.approved_for_application
    ]

    for source_type, text in _candidate_lines(document):
        ranked = sorted(
            (
                (_evidence_similarity(text, item), item)
                for item in approved_evidence
            ),
            key=lambda pair: pair[0],
            reverse=True,
        )

        matched = [
            item
            for score, item in ranked[:4]
            if score >= minimum_similarity
        ]
        best_score = ranked[0][0] if ranked else 0.0

        contains_numeric = bool(_NUMBER_RE.search(text))
        numeric_supported = _numeric_claim_supported(text, matched)

        reasons: list[str] = []
        approved = True
        review_required = False

        if not document.wording_source:
            approved = False
            reasons.append("Document is not registered as a wording source.")

        if not matched:
            approved = False
            review_required = True
            reasons.append(
                "No sufficiently related approved career evidence was found."
            )

        if contains_numeric and not numeric_supported:
            approved = False
            review_required = True
            reasons.append(
                "Numeric wording is not supported by the matched career evidence."
            )

        if matched and any(not item.verified for item in matched):
            review_required = True
            reasons.append("At least one matched evidence item is unverified.")

        if approved and not reasons:
            reasons.append(
                "Wording is mapped to approved career evidence and may be reused."
            )

        candidates.append(
            CVWordingCandidate(
                source_cv_key=document.registry_key,
                source_file=document.path.name,
                text=text,
                source_type=source_type,
                matched_evidence_ids=[item.evidence_id for item in matched],
                relevance_score=best_score,
                contains_numeric_claim=contains_numeric,
                numeric_claim_supported=numeric_supported,
                approved_for_reuse=approved,
                review_required=review_required,
                reasons=reasons,
            )
        )

    return candidates
