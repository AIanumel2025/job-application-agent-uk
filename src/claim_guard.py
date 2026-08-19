"""Check generated claims against selected, approved career evidence."""

from __future__ import annotations

import re
from uuid import uuid4

from src.application_models import (
    ClaimCheck,
    ClaimStatus,
    EvidenceDecision,
    SelectedEvidence,
)


_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?%?\b")
_MARKDOWN_HEADING_RE = re.compile(r"^#{1,6}\s+")
_MARKDOWN_BULLET_RE = re.compile(r"^(?:[-*+]\s+|\d+[.)]\s+)")
_TOKEN_RE = re.compile(r"[a-z0-9+#.]+", re.IGNORECASE)

_STRUCTURAL_LABELS = {
    "professional snapshot",
    "core competencies",
    "additional technical skills",
    "technical skills",
    "professional experience",
    "key projects",
    "education",
    "certifications",
    "links",
}


def _normalise(value: str) -> str:
    return " ".join(value.casefold().split())


def _tokens(value: str) -> set[str]:
    return {
        token.casefold()
        for token in _TOKEN_RE.findall(_normalise(value))
        if len(token) > 1
    }


def _is_structural_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True

    if _MARKDOWN_HEADING_RE.match(stripped):
        return True

    if stripped.casefold().rstrip(":") in _STRUCTURAL_LABELS:
        return True

    return False


def _extract_claims(text: str) -> list[str]:
    """Extract substantive prose/bullets while ignoring Markdown structure."""

    claims: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if _is_structural_line(line):
            continue

        line = _MARKDOWN_BULLET_RE.sub("", line).strip()
        if not line:
            continue

        for sentence in _SENTENCE_RE.split(line):
            claim = sentence.strip()

            # Ignore tiny fragments that are not meaningful factual claims.
            if len(_tokens(claim)) < 3:
                continue

            claims.append(claim)

    return claims


def _supporting_evidence(
    claim: str,
    evidence: list[SelectedEvidence],
) -> list[SelectedEvidence]:
    claim_tokens = _tokens(claim)
    if not claim_tokens:
        return []

    matches: list[SelectedEvidence] = []

    for item in evidence:
        if not item.approved_for_application:
            continue

        if item.decision == EvidenceDecision.REJECTED:
            continue

        evidence_tokens = _tokens(
            f"{item.title} {item.description}"
        )
        if not evidence_tokens:
            continue

        overlap = len(
            claim_tokens & evidence_tokens
        ) / max(len(claim_tokens), 1)

        if overlap >= 0.25:
            matches.append(item)

    return matches


def _numbers(value: str) -> set[str]:
    return set(_NUMBER_RE.findall(value))


def _numbers_supported(
    claim: str,
    support: list[SelectedEvidence],
) -> bool:
    claim_numbers = _numbers(claim)

    if not claim_numbers:
        return True

    supported_numbers: set[str] = set()

    for item in support:
        supported_numbers.update(
            _numbers(
                f"{item.title} {item.description}"
            )
        )

    return claim_numbers.issubset(
        supported_numbers
    )


def check_claims(
    text: str,
    evidence: list[SelectedEvidence],
) -> list[ClaimCheck]:
    """Check substantive generated claims against selected career evidence."""

    results: list[ClaimCheck] = []

    for claim in _extract_claims(text):
        support = _supporting_evidence(
            claim,
            evidence,
        )
        reasons: list[str] = []

        if not _numbers_supported(
            claim,
            support,
        ):
            status = ClaimStatus.BLOCKED
            reasons.append(
                "The claim contains a number not supported by the selected evidence."
            )

        elif not support:
            status = ClaimStatus.REVIEW_REQUIRED
            reasons.append(
                "No sufficiently related approved evidence was found."
            )

        elif any(
            item.decision
            == EvidenceDecision.REVIEW_REQUIRED
            for item in support
        ):
            status = ClaimStatus.REVIEW_REQUIRED
            reasons.append(
                "Supporting evidence requires review."
            )

        else:
            status = ClaimStatus.APPROVED
            reasons.append(
                "The claim is supported by approved evidence."
            )

        results.append(
            ClaimCheck(
                claim_id=str(uuid4()),
                text=claim,
                status=status,
                source_evidence_ids=[
                    item.evidence_id
                    for item in support
                ],
                reasons=reasons,
            )
        )

    return results
