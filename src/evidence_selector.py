"""Select safe, relevant evidence for one job application."""

from __future__ import annotations

from difflib import SequenceMatcher

from src.application_models import EvidenceDecision, SelectedEvidence
from src.matching_models import CareerEvidence, JobMatchResult


def _normalise(value: str) -> str:
    return " ".join(
        value.casefold()
        .replace("-", " ")
        .replace("_", " ")
        .replace("/", " ")
        .split()
    )


def _relevance(evidence: CareerEvidence, match: JobMatchResult) -> float:
    evidence_text = _normalise(f"{evidence.title} {evidence.description}")
    job_text = _normalise(
        " ".join(
            [
                match.job_title,
                match.company,
                *[
                    requirement.text
                    for requirement in match.requirements.requirements
                ],
            ]
        )
    )

    evidence_tokens = set(evidence_text.split())
    job_tokens = set(job_text.split())

    overlap = len(evidence_tokens & job_tokens) / max(len(job_tokens), 1)
    sequence = SequenceMatcher(None, evidence_text, job_text).ratio()

    return round(max(overlap, sequence), 4)


def select_evidence(
    profile_evidence: list[CareerEvidence],
    match: JobMatchResult,
    *,
    maximum_items: int = 12,
    minimum_relevance: float = 0.20,
) -> list[SelectedEvidence]:
    """Select approved, non-confidential evidence for an application."""

    selected: list[SelectedEvidence] = []

    for evidence in profile_evidence:
        reasons: list[str] = []
        relevance = _relevance(evidence, match)

        if not evidence.approved_for_application:
            decision = EvidenceDecision.REJECTED
            reasons.append("Evidence is not approved for application use.")
        elif relevance < minimum_relevance:
            decision = EvidenceDecision.REJECTED
            reasons.append("Evidence relevance is below the configured threshold.")
        elif not evidence.verified:
            decision = EvidenceDecision.REVIEW_REQUIRED
            reasons.append("Evidence is relevant but not fully verified.")
        else:
            decision = EvidenceDecision.SELECTED
            reasons.append("Evidence is relevant, verified, and approved.")

        selected.append(
            SelectedEvidence(
                evidence_id=evidence.evidence_id,
                source_record_id=evidence.source_record_id,
                title=evidence.title,
                description=evidence.description,
                evidence_type=str(evidence.evidence_type),
                relevance_score=relevance,
                verified=evidence.verified,
                approved_for_application=evidence.approved_for_application,
                decision=decision,
                reasons=reasons,
            )
        )

    selected.sort(
        key=lambda item: (
            item.decision == EvidenceDecision.SELECTED,
            item.decision == EvidenceDecision.REVIEW_REQUIRED,
            item.relevance_score,
        ),
        reverse=True,
    )

    return selected[:maximum_items]
