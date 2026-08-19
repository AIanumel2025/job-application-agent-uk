"""Generate a factual, template-aware, job-specific CV draft."""

from __future__ import annotations

from collections import defaultdict

from src.application_models import (
    EvidenceDecision,
    SelectedEvidence,
    TailoredBullet,
    TailoredCV,
    TailoredExperienceSection,
    TailoredProjectSection,
)
from src.cv_content_mapper import map_reference_cv_to_evidence
from src.cv_template_loader import CVRegistry, load_cv_registry
from src.cv_template_renderer import render_tailored_cv
from src.cv_template_selector import CVSelection, select_cv_material
from src.cv_wording_selector import select_cv_wording
from src.matching_models import CareerMatchingProfile, JobMatchResult


def _selected(evidence: list[SelectedEvidence]) -> list[SelectedEvidence]:
    return [
        item
        for item in evidence
        if item.decision
        in {
            EvidenceDecision.SELECTED,
            EvidenceDecision.REVIEW_REQUIRED,
        }
    ]


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


def _summary(
    profile: CareerMatchingProfile,
    match: JobMatchResult,
    selected: list[SelectedEvidence],
) -> str:
    strengths = [
        item.title
        for item in selected
        if item.decision == EvidenceDecision.SELECTED
    ][:3]
    evidence_phrase = ", ".join(strengths) if strengths else "relevant experience"

    return (
        f"{profile.name} is targeting the {match.job_title} role at "
        f"{match.company}, bringing verified evidence in {evidence_phrase}. "
        f"The profile combines technical delivery, analytical problem-solving, "
        f"and communication experience aligned with the vacancy requirements."
    )


def _reference_wording(
    profile: CareerMatchingProfile,
    match: JobMatchResult,
    selection: CVSelection,
) -> list:
    candidates = []

    for document in selection.reference_cvs:
        candidates.extend(
            map_reference_cv_to_evidence(
                document,
                profile.evidence,
            )
        )

    return select_cv_wording(
        candidates,
        match,
        maximum_items=12,
        allow_review_required=False,
    )



def _split_experience_description(
    description: str,
) -> tuple[str | None, list[str]]:
    """Split existing evidence into organisation plus clean responsibility bullets."""
    parts = [
        part.strip().rstrip(".")
        for part in description.split(";")
        if part.strip()
    ]

    if not parts:
        return None, []

    if len(parts) == 1:
        return None, [parts[0]]

    return parts[0], parts[1:]


def _unique_text(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []

    for value in values:
        cleaned = " ".join(value.split()).strip()
        if not cleaned:
            continue

        key = cleaned.casefold()
        if key not in seen:
            output.append(cleaned)
            seen.add(key)

    return output


def tailor_cv(
    profile: CareerMatchingProfile,
    match: JobMatchResult,
    evidence: list[SelectedEvidence],
    *,
    registry: CVRegistry | None = None,
) -> TailoredCV:
    chosen = _selected(evidence)
    keywords = _keywords(match)

    registry = registry or load_cv_registry()
    selection = select_cv_material(
        registry,
        job_title=match.job_title,
    )
    wording = _reference_wording(
        profile,
        match,
        selection,
    )

    by_type: dict[str, list[SelectedEvidence]] = defaultdict(list)
    for item in chosen:
        by_type[item.evidence_type].append(item)

    wording_by_evidence: dict[str, list] = defaultdict(list)
    for item in wording:
        for evidence_id in item.matched_evidence_ids:
            wording_by_evidence[evidence_id].append(item)

    experience_sections: list[TailoredExperienceSection] = []

    for index, item in enumerate(
        by_type.get("experience", [])[:4],
        start=1,
    ):
        wording_options = wording_by_evidence.get(item.evidence_id, [])

        organisation, source_bullets = _split_experience_description(
            item.description
        )

        approved_wording = _unique_text(
            [
                option.text
                for option in wording_options
                if getattr(option, "text", "").strip()
            ]
        )

        bullet_texts = approved_wording or source_bullets
        if not bullet_texts and item.description.strip():
            bullet_texts = [item.description.strip()]

        bullets: list[TailoredBullet] = []
        for bullet_index, bullet_text in enumerate(
            bullet_texts[:5],
            start=1,
        ):
            bullets.append(
                TailoredBullet(
                    bullet_id=f"exp_{index}_{bullet_index}",
                    source_evidence_ids=[item.evidence_id],
                    text=bullet_text,
                    keywords=[
                        keyword
                        for keyword in keywords
                        if keyword.casefold() in bullet_text.casefold()
                    ],
                    relevance_score=item.relevance_score,
                    approved=item.approved_for_application,
                )
            )

        experience_sections.append(
            TailoredExperienceSection(
                source_record_id=item.source_record_id,
                role_title=item.title,
                organisation=organisation,
                bullets=bullets,
            )
        )

    projects: list[TailoredProjectSection] = []

    for item in by_type.get("project", [])[:3]:
        wording_options = wording_by_evidence.get(item.evidence_id, [])
        summary = (
            wording_options[0].text
            if wording_options
            else item.description
        )

        projects.append(
            TailoredProjectSection(
                source_record_id=item.source_record_id,
                project_name=item.title,
                summary=summary,
                technologies=[
                    keyword
                    for keyword in keywords
                    if keyword.casefold() in summary.casefold()
                ],
                source_evidence_ids=[item.evidence_id],
            )
        )

    skills = list(
        dict.fromkeys(
            [
                *[
                    skill
                    for skill in profile.skills + profile.tools
                    if any(
                        skill.casefold() in keyword.casefold()
                        or keyword.casefold() in skill.casefold()
                        for keyword in keywords
                    )
                ],
                *profile.skills,
                *profile.tools,
            ]
        )
    )[:18]

    summary = _summary(profile, match, chosen)

    provisional = TailoredCV(
        candidate_name=profile.name,
        target_role=match.job_title,
        company=match.company,
        professional_summary=summary,
        skills=skills,
        experience=experience_sections,
        projects=projects,
        education=profile.education_levels,
        certifications=profile.certifications,
        links=[],
        warnings=[
            *[
                item.reasons[0]
                for item in chosen
                if item.decision == EvidenceDecision.REVIEW_REQUIRED and item.reasons
            ],
            *selection.reasons,
        ],
        markdown="Temporary placeholder",
    )

    provisional.markdown = render_tailored_cv(
        selection.master_template,
        provisional,
    )

    return provisional
