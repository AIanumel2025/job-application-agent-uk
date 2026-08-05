"""Check generated claims against selected, approved career evidence."""

from __future__ import annotations

import re
from uuid import uuid4

from src.application_models import ClaimCheck, ClaimStatus, SelectedEvidence


_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?%?\b")


def _normalise(value: str) -> str:
    return " ".join(value.casefold().split())


def _supporting_evidence(
    claim: str,
    evidence: list[SelectedEvidence],
) -> list[SelectedEvidence]:
    claim_tokens = set(_normalise(claim).split())
    matches: list[SelectedEvidence] = []

    for item in evidence:
        if not item.approved_for_application:
            continue
        evidence_tokens = set(
            _normalise(f"{item.title} {item.description}").split()
        )
        overlap = len(claim_tokens & evidence_tokens) / max(len(claim_tokens), 1)
        if overlap >= 0.25:
            matches.append(item)

    return matches


def check_claims(
    text: str,
    evidence: list[SelectedEvidence],
) -> list[ClaimCheck]:
    results: list[ClaimCheck] = []

    for sentence in _SENTENCE_RE.split(text.strip()):
        claim = sentence.strip()
        if not claim:
            continue

        support = _supporting_evidence(claim, evidence)
        reasons: list[str] = []

        if _NUMBER_RE.search(claim) and not any(
            _NUMBER_RE.search(item.description)
            for item in support
        ):
            status = ClaimStatus.BLOCKED
            reasons.append(
                "The claim contains a number not supported by the selected evidence."
            )
        elif not support:
            status = ClaimStatus.REVIEW_REQUIRED
            reasons.append("No sufficiently related approved evidence was found.")
        elif any(
            str(item.decision) == "review_required"
            for item in support
        ):
            status = ClaimStatus.REVIEW_REQUIRED
            reasons.append("Supporting evidence requires review.")
        else:
            status = ClaimStatus.APPROVED
            reasons.append("The claim is supported by approved evidence.")

        results.append(
            ClaimCheck(
                claim_id=str(uuid4()),
                text=claim,
                status=status,
                source_evidence_ids=[
                    item.evidence_id for item in support
                ],
                reasons=reasons,
            )
        )

    return results
