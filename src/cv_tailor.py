"""Generate a factual, job-specific CV draft."""

from __future__ import annotations

from collections import defaultdict

from src.application_models import (
    SelectedEvidence,
    TailoredBullet,
    TailoredCV,
    TailoredExperienceSection,
    TailoredProjectSection,
)
from src.matching_models import CareerMatchingProfile, JobMatchResult


def _selected(evidence: list[SelectedEvidence]) -> list[SelectedEvidence]:
    return [
        item
        for item in evidence
        if str(item.decision) in {"selected", "review_required"}
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
        for item in selected[:3]
    ]

    evidence_phrase = ", ".join(strengths) if strengths else "relevant experience"

    return (
        f"{profile.name} is targeting the {match.job_title} role at "
        f"{match.company}, bringing evidence in {evidence_phrase}. "
        f"The profile combines technical delivery, analytical problem-solving, "
        f"and communication experience aligned with the vacancy requirements."
    )


def tailor_cv(
    profile: CareerMatchingProfile,
    match: JobMatchResult,
    evidence: list[SelectedEvidence],
) -> TailoredCV:
    chosen = _selected(evidence)
    keywords = _keywords(match)

    by_type: dict[str, list[SelectedEvidence]] = defaultdict(list)
    for item in chosen:
        by_type[item.evidence_type].append(item)

    experience_sections: list[TailoredExperienceSection] = []
    for index, item in enumerate(by_type.get("experience", [])[:4], start=1):
        bullet = TailoredBullet(
            bullet_id=f"exp_{index}_1",
            source_evidence_ids=[item.evidence_id],
            text=item.description,
            keywords=[
                keyword
                for keyword in keywords
                if keyword.casefold() in item.description.casefold()
            ],
            relevance_score=item.relevance_score,
            approved=item.approved_for_application,
        )
        experience_sections.append(
            TailoredExperienceSection(
                source_record_id=item.source_record_id,
                role_title=item.title,
                bullets=[bullet],
            )
        )

    projects: list[TailoredProjectSection] = []
    for item in by_type.get("project", [])[:3]:
        projects.append(
            TailoredProjectSection(
                source_record_id=item.source_record_id,
                project_name=item.title,
                summary=item.description,
                technologies=[
                    keyword
                    for keyword in keywords
                    if keyword.casefold() in item.description.casefold()
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

    markdown_lines = [
        f"# {profile.name}",
        "",
        f"## Target Role: {match.job_title}",
        "",
        "## Professional Summary",
        summary,
        "",
        "## Core Skills",
        ", ".join(skills),
        "",
        "## Experience",
    ]

    for section in experience_sections:
        markdown_lines.extend(
            [
                f"### {section.role_title}",
                *[f"- {bullet.text}" for bullet in section.bullets],
                "",
            ]
        )

    if projects:
        markdown_lines.append("## Selected Projects")
        for project in projects:
            markdown_lines.extend(
                [
                    f"### {project.project_name}",
                    project.summary,
                    "",
                ]
            )

    if profile.education_levels:
        markdown_lines.extend(
            [
                "## Education",
                *[f"- {item}" for item in profile.education_levels],
                "",
            ]
        )

    if profile.certifications:
        markdown_lines.extend(
            [
                "## Certifications",
                *[f"- {item}" for item in profile.certifications],
                "",
            ]
        )

    warnings = [
        item.reasons[0]
        for item in chosen
        if str(item.decision) == "review_required" and item.reasons
    ]

    return TailoredCV(
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
        warnings=warnings,
        markdown="\n".join(markdown_lines).strip() + "\n",
    )
