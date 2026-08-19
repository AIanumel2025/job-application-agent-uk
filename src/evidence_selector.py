"""Select safe, relevant evidence for one job application."""

from __future__ import annotations

from difflib import SequenceMatcher
import re

from src.application_models import EvidenceDecision, SelectedEvidence
from src.matching_models import CareerEvidence, JobMatchResult


_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
    "you",
    "your",
    "we",
    "our",
}

_TOKEN_RE = re.compile(r"[a-z0-9+#.]+", re.IGNORECASE)


def _normalise(value: str) -> str:
    return " ".join(
        value.casefold()
        .replace("-", " ")
        .replace("_", " ")
        .replace("/", " ")
        .split()
    )


def _tokens(value: str) -> set[str]:
    return {
        token.casefold()
        for token in _TOKEN_RE.findall(_normalise(value))
        if token.casefold() not in _STOP_WORDS
        and len(token) > 1
    }


def _token_similarity(left: str, right: str) -> float:
    """Return a balanced token-overlap score for two short text fragments."""

    left_tokens = _tokens(left)
    right_tokens = _tokens(right)

    if not left_tokens or not right_tokens:
        return 0.0

    intersection = len(left_tokens & right_tokens)

    # Coverage of the smaller phrase is more useful here than dividing by the
    # entire job description. For example, "AI Engineer Intern" should match
    # strongly to "AI Engineering Intern".
    smaller_coverage = intersection / min(
        len(left_tokens),
        len(right_tokens),
    )

    jaccard = intersection / len(
        left_tokens | right_tokens
    )

    return max(smaller_coverage, jaccard)


def _phrase_similarity(left: str, right: str) -> float:
    left_n = _normalise(left)
    right_n = _normalise(right)

    if not left_n or not right_n:
        return 0.0

    if left_n == right_n:
        return 1.0

    if left_n in right_n or right_n in left_n:
        return 0.95

    sequence = SequenceMatcher(
        None,
        left_n,
        right_n,
    ).ratio()

    token_score = _token_similarity(
        left_n,
        right_n,
    )

    return max(sequence, token_score)


def _requirement_texts(
    match: JobMatchResult,
) -> list[str]:
    values: list[str] = []

    for requirement in match.requirements.requirements:
        if requirement.text:
            values.append(requirement.text)

        if requirement.normalised_value:
            values.extend(
                part.strip()
                for part in str(
                    requirement.normalised_value
                ).split(",")
                if part.strip()
            )

    return values


def _relevance(
    evidence: CareerEvidence,
    match: JobMatchResult,
) -> float:
    """Score one evidence item against the target job.

    The score combines:
    - direct evidence-title vs job-title similarity;
    - evidence vs individual job requirements;
    - evidence vs the combined job text.

    Requirement-level comparison prevents strong evidence from being diluted by
    a long vacancy description.
    """

    evidence_title = evidence.title or ""
    evidence_text = (
        f"{evidence.title} {evidence.description}"
    ).strip()

    title_score = _phrase_similarity(
        evidence_title,
        match.job_title,
    )

    requirement_scores = [
        _phrase_similarity(
            evidence_text,
            requirement_text,
        )
        for requirement_text in _requirement_texts(
            match
        )
    ]

    best_requirement_score = (
        max(requirement_scores)
        if requirement_scores
        else 0.0
    )

    combined_job_text = " ".join(
        [
            match.job_title,
            *[
                requirement.text
                for requirement
                in match.requirements.requirements
                if requirement.text
            ],
            *[
                str(requirement.normalised_value)
                for requirement
                in match.requirements.requirements
                if requirement.normalised_value
            ],
        ]
    )

    combined_token_score = _token_similarity(
        evidence_text,
        combined_job_text,
    )

    # A strong title match should count heavily for experience evidence, while
    # projects and skills can qualify through requirement-level relevance.
    score = max(
        title_score * 0.90,
        best_requirement_score * 0.85,
        combined_token_score * 0.75,
    )

    return round(
        min(max(score, 0.0), 1.0),
        4,
    )


def select_evidence(
    profile_evidence: list[CareerEvidence],
    match: JobMatchResult,
    *,
    maximum_items: int = 12,
    minimum_relevance: float = 0.20,
) -> list[SelectedEvidence]:
    """Select approved, relevant evidence for an application.

    Verified evidence is selected automatically.
    Relevant but unverified evidence is retained for human review.
    """

    selected: list[SelectedEvidence] = []

    for evidence in profile_evidence:
        reasons: list[str] = []
        relevance = _relevance(
            evidence,
            match,
        )

        if not evidence.approved_for_application:
            decision = EvidenceDecision.REJECTED
            reasons.append(
                "Evidence is not approved for application use."
            )

        elif relevance < minimum_relevance:
            decision = EvidenceDecision.REJECTED
            reasons.append(
                "Evidence relevance is below the configured threshold."
            )

        elif not evidence.verified:
            decision = EvidenceDecision.REVIEW_REQUIRED
            reasons.append(
                "Evidence is relevant but not fully verified."
            )

        else:
            decision = EvidenceDecision.SELECTED
            reasons.append(
                "Evidence is relevant, verified, and approved."
            )

        selected.append(
            SelectedEvidence(
                evidence_id=evidence.evidence_id,
                source_record_id=evidence.source_record_id,
                title=evidence.title,
                description=evidence.description,
                evidence_type=str(
                    evidence.evidence_type
                ),
                relevance_score=relevance,
                verified=evidence.verified,
                approved_for_application=(
                    evidence.approved_for_application
                ),
                decision=decision,
                reasons=reasons,
            )
        )

        type_priority = {
        "experience": 6,
        "project": 5,
        "skill": 4,
        "achievement": 3,
        "certification": 2,
        "education": 1,
    }

    selected.sort(
        key=lambda item: (
            item.decision == EvidenceDecision.SELECTED,
            item.decision == EvidenceDecision.REVIEW_REQUIRED,
            type_priority.get(
                str(item.evidence_type).split(".")[-1].casefold(),
                0,
            ),
            item.relevance_score,
        ),
        reverse=True,
    )

    return selected[:maximum_items]
