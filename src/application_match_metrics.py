"""Explainable metrics for evaluating job/application compatibility."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(slots=True)
class KeywordMatchResult:
    score: float
    matched: list[str]
    missing: list[str]


@dataclass(slots=True)
class MustHaveCoverageResult:
    score: float
    covered: list[str]
    missing: list[str]


def _normalise(text: str) -> str:
    """Normalise text for deterministic matching."""

    text = text.lower()

    text = re.sub(
        r"[^a-z0-9+#./\-\s]",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def _contains_term(
    text: str,
    term: str,
) -> bool:
    """Check whether a term occurs in normalised text."""

    normalised_text = _normalise(text)
    normalised_term = _normalise(term)

    if not normalised_term:
        return False

    return normalised_term in normalised_text


def score_keyword_match(
    *,
    job_keywords: list[str],
    candidate_text: str,
) -> KeywordMatchResult:
    """
    Measure how many job keywords are genuinely supported
    somewhere in the candidate's factual career evidence.
    """

    cleaned_keywords = []

    seen = set()

    for keyword in job_keywords:
        keyword = str(keyword).strip()

        if not keyword:
            continue

        key = _normalise(keyword)

        if key in seen:
            continue

        seen.add(key)
        cleaned_keywords.append(keyword)

    if not cleaned_keywords:
        return KeywordMatchResult(
            score=0.0,
            matched=[],
            missing=[],
        )

    matched = []
    missing = []

    for keyword in cleaned_keywords:
        if _contains_term(
            candidate_text,
            keyword,
        ):
            matched.append(keyword)
        else:
            missing.append(keyword)

    score = (
        len(matched)
        / len(cleaned_keywords)
        * 100
    )

    return KeywordMatchResult(
        score=round(score, 2),
        matched=matched,
        missing=missing,
    )


def score_must_have_coverage(
    *,
    must_haves: list[str],
    candidate_text: str,
) -> MustHaveCoverageResult:
    """
    Measure coverage of explicitly identified must-have
    requirements.
    """

    cleaned_requirements = []

    seen = set()

    for requirement in must_haves:
        requirement = str(
            requirement
        ).strip()

        if not requirement:
            continue

        key = _normalise(
            requirement
        )

        if key in seen:
            continue

        seen.add(key)

        cleaned_requirements.append(
            requirement
        )

    if not cleaned_requirements:
        return MustHaveCoverageResult(
            score=100.0,
            covered=[],
            missing=[],
        )

    covered = []
    missing = []

    for requirement in cleaned_requirements:
        if _contains_term(
            candidate_text,
            requirement,
        ):
            covered.append(
                requirement
            )
        else:
            missing.append(
                requirement
            )

    score = (
        len(covered)
        / len(cleaned_requirements)
        * 100
    )

    return MustHaveCoverageResult(
        score=round(score, 2),
        covered=covered,
        missing=missing,
    )


def score_claim_integrity(
    *,
    proposed_claims: list[str],
    verified_claims: list[str],
) -> float:
    """
    Calculate what percentage of proposed application claims
    can be supported by verified career evidence.

    A production application should always return 100%.
    """

    proposed = {
        _normalise(item)
        for item in proposed_claims
        if str(item).strip()
    }

    verified = {
        _normalise(item)
        for item in verified_claims
        if str(item).strip()
    }

    if not proposed:
        return 100.0

    supported = sum(
        1
        for claim in proposed
        if claim in verified
    )

    return round(
        supported / len(proposed) * 100,
        2,
    )
