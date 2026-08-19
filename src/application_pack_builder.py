"""Assemble a complete human-review application pack."""

from __future__ import annotations

from src.application_answer_generator import generate_standard_answers
from src.application_models import (
    ApplicationDocumentType,
    ApplicationPack,
    ApplicationPackManifest,
    ApplicationPackStatus,
)
from src.claim_guard import check_claims
from src.cover_letter_generator import generate_cover_letter
from src.cv_tailor import tailor_cv
from src.document_quality_checker import check_document_quality
from src.evidence_selector import select_evidence
from src.matching_models import CareerMatchingProfile, JobMatchResult


def _keywords(match: JobMatchResult) -> list[str]:
    values: list[str] = []
    for requirement in match.requirements.requirements:
        if requirement.normalised_value:
            values.extend(
                part.strip()
                for part in requirement.normalised_value.split(",")
                if part.strip()
            )
    return list(dict.fromkeys(values))


def build_application_pack(
    profile: CareerMatchingProfile,
    match: JobMatchResult,
) -> ApplicationPack:
    evidence = select_evidence(profile.evidence, match)

    # Phase 5.1: CV tailoring now starts from the registered structural master
    # and may reuse only wording that maps back to approved career_data evidence.
    cv = tailor_cv(profile, match, evidence)

    cover_letter = generate_cover_letter(profile, match, evidence)
    answers = generate_standard_answers(profile, match, evidence)

    claim_checks = [
        *check_claims(cv.markdown, evidence),
        *check_claims(cover_letter.markdown, evidence),
    ]

    keywords = _keywords(match)

    cv_quality = check_document_quality(
        cv.markdown,
        ApplicationDocumentType.CV,
        keywords=keywords,
        maximum_words=1200,
    )
    cover_quality = check_document_quality(
        cover_letter.markdown,
        ApplicationDocumentType.COVER_LETTER,
        keywords=keywords,
        minimum_words=150,
        maximum_words=550,
    )

    blocked = any(
        str(item.status) == "blocked"
        for item in claim_checks
    )
    quality_failed = not cv_quality.passed or not cover_quality.passed

    if blocked:
        status = ApplicationPackStatus.BLOCKED
    elif quality_failed or any(answer.requires_review for answer in answers):
        status = ApplicationPackStatus.REVIEW_REQUIRED
    else:
        status = ApplicationPackStatus.DRAFT

    selected_ids = [
        item.evidence_id
        for item in evidence
        if str(item.decision) in {"selected", "review_required"}
    ]

    interview_lines = [
        "# Interview Evidence",
        "",
        f"## {match.job_title} at {match.company}",
        "",
    ]

    for item in evidence:
        if str(item.decision) in {"selected", "review_required"}:
            interview_lines.extend(
                [
                    f"### {item.title}",
                    item.description,
                    f"- Evidence ID: `{item.evidence_id}`",
                    f"- Relevance: {item.relevance_score:.0%}",
                    "",
                ]
            )

    manifest = ApplicationPackManifest(
        job_id=match.job_id,
        company=match.company,
        role_title=match.job_title,
        application_url=match.application_url,
        status=status,
        selected_evidence_ids=selected_ids,
        claim_checks=claim_checks,
        quality_results=[cv_quality, cover_quality],
        warnings=[
            *cv.warnings,
            *cover_letter.warnings,
            *[
                warning
                for answer in answers
                for warning in answer.warnings
            ],
        ],
        human_review_required=True,
    )

    return ApplicationPack(
        manifest=manifest,
        cv=cv,
        cover_letter=cover_letter,
        application_answers=answers,
        interview_evidence_markdown="\n".join(interview_lines).strip() + "\n",
        metadata={
            "match_id": str(match.match_id),
            "final_score": match.final_score,
            "recommendation": str(match.recommendation),
            "cv_template_integration": "phase_5_1",
        },
    )
