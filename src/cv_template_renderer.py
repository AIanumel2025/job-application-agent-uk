"""Render tailored CV content using the registered master-template structure."""

from __future__ import annotations

from dataclasses import dataclass
import re

from src.application_models import TailoredCV
from src.cv_template_loader import LoadedCVDocument


_PLACEHOLDER_RE = re.compile(r"\[[^\]]+\]")
_SWAP_MARKER = "SWAP THIS BLOCK FOR EVERY APPLICATION"
_STABLE_MARKER = "KEEP STABLE BELOW THIS LINE"


@dataclass(slots=True)
class MasterTemplateStructure:
    header_lines: list[str]
    dynamic_section_lines: list[str]
    stable_section_lines: list[str]
    detected_swap_marker: bool
    detected_stable_marker: bool


def parse_master_template(
    master: LoadedCVDocument,
) -> MasterTemplateStructure:
    """Split the master into header, dynamic, and stable sections."""

    header: list[str] = []
    dynamic: list[str] = []
    stable: list[str] = []

    mode = "header"
    swap_found = False
    stable_found = False

    for raw in master.paragraphs:
        line = raw.strip()
        if not line:
            continue

        if _SWAP_MARKER.casefold() in line.casefold():
            swap_found = True
            mode = "dynamic"
            continue

        if _STABLE_MARKER.casefold() in line.casefold():
            stable_found = True
            mode = "stable"
            continue

        if mode == "header":
            header.append(line)
        elif mode == "dynamic":
            dynamic.append(line)
        else:
            stable.append(line)

    return MasterTemplateStructure(
        header_lines=header,
        dynamic_section_lines=dynamic,
        stable_section_lines=stable,
        detected_swap_marker=swap_found,
        detected_stable_marker=stable_found,
    )


def _safe_stable_lines(
    structure: MasterTemplateStructure,
) -> list[str]:
    """Keep structural headings while dropping placeholders/instructional claims."""

    output: list[str] = []

    for line in structure.stable_section_lines:
        if _PLACEHOLDER_RE.search(line):
            continue

        lowered = line.casefold()
        if lowered.startswith("note:"):
            continue

        # Keep headings and factual content only when it is later represented by
        # the structured TailoredCV. This prevents unsupported master claims from
        # leaking into the rendered result.
        if line.isupper() or len(line.split()) <= 5:
            output.append(line)

    return output



def _split_skill_sections(
    skills: list[str],
) -> tuple[list[str], list[str]]:
    """Split one ordered skill list into non-duplicative CV sections."""
    cleaned = list(
        dict.fromkeys(
            item.strip()
            for item in skills
            if item.strip()
        )
    )

    if len(cleaned) <= 8:
        return cleaned, []

    return cleaned[:8], cleaned[8:]


def render_tailored_cv(
    master: LoadedCVDocument,
    tailored: TailoredCV,
) -> str:
    """Render TailoredCV content with the master template's section philosophy.

    The master contributes structure only. TailoredCV remains the factual content.
    """

    structure = parse_master_template(master)

    core_competencies, technical_skills = _split_skill_sections(
        tailored.skills
    )

    lines = [
        f"# {tailored.candidate_name}",
        "",
        f"## {tailored.target_role}",
        "",
        "## PROFESSIONAL SNAPSHOT",
        tailored.professional_summary,
        "",
    ]

    if core_competencies:
        lines.extend(
            [
                "## CORE COMPETENCIES",
                " • ".join(core_competencies),
                "",
            ]
        )

    if technical_skills:
        lines.extend(
            [
                "## ADDITIONAL TECHNICAL SKILLS",
                " • ".join(technical_skills),
                "",
            ]
        )

    lines.append("## PROFESSIONAL EXPERIENCE")

    for section in tailored.experience:
        heading = section.role_title
        if section.organisation:
            heading += f" | {section.organisation}"
        lines.append(f"### {heading}")

        if section.dates:
            lines.append(section.dates)

        for bullet in section.bullets:
            lines.append(f"- {bullet.text}")

        lines.append("")

    if tailored.projects:
        lines.append("## KEY PROJECTS")
        for project in tailored.projects:
            lines.extend(
                [
                    f"### {project.project_name}",
                    project.summary,
                    "",
                ]
            )

    if tailored.education:
        lines.extend(
            [
                "## EDUCATION",
                *[f"- {item}" for item in tailored.education],
                "",
            ]
        )

    if tailored.certifications:
        lines.extend(
            [
                "## CERTIFICATIONS",
                *[f"- {item}" for item in tailored.certifications],
                "",
            ]
        )

    if tailored.links:
        lines.extend(
            [
                "## LINKS",
                *[f"- {item}" for item in tailored.links],
                "",
            ]
        )

    return "\n".join(lines).strip() + "\n"
