"""Generate a concise, evidence-backed cover letter draft."""

from __future__ import annotations

from src.application_models import CoverLetter, SelectedEvidence
from src.matching_models import CareerMatchingProfile, JobMatchResult


def generate_cover_letter(
    profile: CareerMatchingProfile,
    match: JobMatchResult,
    evidence: list[SelectedEvidence],
) -> CoverLetter:
    chosen = [
        item
        for item in evidence
        if str(item.decision) in {"selected", "review_required"}
    ][:4]

    opening = (
        f"I am applying for the {match.job_title} position at {match.company}. "
        f"The role aligns with my background in data, artificial intelligence, "
        f"automation, and evidence-led problem-solving."
    )

    if chosen:
        evidence_sentences = " ".join(
            f"My experience includes {item.description.rstrip('.')}."
            for item in chosen[:2]
        )
    else:
        evidence_sentences = (
            "My background includes technical projects, analytical work, "
            "and experience explaining complex ideas clearly."
        )

    alignment = (
        f"The vacancy's requirements are particularly relevant to my experience. "
        f"{evidence_sentences} These examples demonstrate both technical ability "
        f"and the judgement required to deliver reliable work."
    )

    motivation = (
        f"I would welcome the opportunity to contribute to {match.company}, "
        f"while continuing to develop within the {match.job_title} role. "
        f"I am especially interested in work where sound engineering, clear "
        f"communication, and measurable outcomes are valued."
    )

    closing_paragraph = (
        "Thank you for considering my application. I would welcome the "
        "opportunity to discuss how my experience can support the team."
    )

    paragraphs = [
        opening,
        alignment,
        motivation,
        closing_paragraph,
    ]

    markdown = "\n\n".join(
        [
            "Dear Hiring Manager,",
            *paragraphs,
            "Yours sincerely,",
            profile.name,
        ]
    )

    warnings = [
        item.reasons[0]
        for item in chosen
        if str(item.decision) == "review_required" and item.reasons
    ]

    return CoverLetter(
        candidate_name=profile.name,
        company=match.company,
        role_title=match.job_title,
        paragraphs=paragraphs,
        source_evidence_ids=[item.evidence_id for item in chosen],
        warnings=warnings,
        markdown=markdown.strip() + "\n",
    )
