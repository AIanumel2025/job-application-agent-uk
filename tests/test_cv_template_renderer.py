"""Tests for Phase 5.1 CV template rendering."""

from pathlib import Path

from src.application_models import (
    TailoredBullet,
    TailoredCV,
    TailoredExperienceSection,
    TailoredProjectSection,
)
from src.cv_template_loader import LoadedCVDocument
from src.cv_template_renderer import (
    parse_master_template,
    render_tailored_cv,
)


def _master() -> LoadedCVDocument:
    paragraphs = [
        "ANTHONY L. ANUMEL",
        "London, England",
        ">>> SWAP THIS BLOCK FOR EVERY APPLICATION — TAILOR IN UNDER 2 MINUTES <<<",
        "[TITLE EXACTLY AS WRITTEN IN THE JOB POSTING]",
        "PROFESSIONAL SNAPSHOT",
        "[Line 1: Mirror the job description]",
        "CORE COMPETENCIES",
        ">>> KEEP STABLE BELOW THIS LINE — DO NOT EDIT FOR EACH APPLICATION <<<",
        "TECHNICAL SKILLS",
        "PROFESSIONAL EXPERIENCE",
        "[Your Title] | [Company]",
        "NOTE: unsupported example claim",
    ]

    return LoadedCVDocument(
        registry_key="plain_master_template",
        path=Path("source_documents/cv/plain_master_template.docx"),
        document_type="master_template",
        status="active",
        role_families=["ai_engineering", "data_engineering"],
        uses=["document_structure"],
        wording_source=False,
        factual_authority=False,
        priority=None,
        paragraphs=paragraphs,
        table_rows=[],
        full_text="\n".join(paragraphs),
        notes=None,
    )


def _tailored() -> TailoredCV:
    cv = TailoredCV(
        candidate_name="Anthony L. Anumel",
        target_role="Data Engineer",
        company="Example AI Ltd",
        professional_summary=(
            "Data Engineer with verified Python and AWS evidence."
        ),
        skills=["Python", "AWS", "SQL"],
        experience=[
            TailoredExperienceSection(
                source_record_id="experience_teacher",
                role_title="Algebra Teacher",
                bullets=[
                    TailoredBullet(
                        bullet_id="exp_1_1",
                        source_evidence_ids=["exp_1"],
                        text=(
                            "Used Excel and Power BI dashboards to "
                            "communicate insights."
                        ),
                        keywords=["Power BI"],
                        relevance_score=0.8,
                        approved=True,
                    )
                ],
            )
        ],
        projects=[
            TailoredProjectSection(
                source_record_id="project_pipeline",
                project_name="Document Intelligence Pipeline",
                summary=(
                    "Built a Python and AWS document-processing "
                    "pipeline using Docker."
                ),
                technologies=["Python", "AWS", "Docker"],
                source_evidence_ids=["project_1"],
            )
        ],
        education=["MSc Artificial Intelligence"],
        certifications=["PL-300 Power BI"],
        links=[],
        warnings=[],
        markdown="Temporary placeholder",
    )
    return cv


def test_parses_dynamic_and_stable_master_sections() -> None:
    structure = parse_master_template(_master())

    assert structure.detected_swap_marker is True
    assert structure.detected_stable_marker is True
    assert structure.dynamic_section_lines
    assert structure.stable_section_lines


def test_rendered_cv_uses_tailored_verified_content() -> None:
    rendered = render_tailored_cv(
        _master(),
        _tailored(),
    )

    assert "# Anthony L. Anumel" in rendered
    assert "## Data Engineer" in rendered
    assert "Python" in rendered
    assert "Document Intelligence Pipeline" in rendered


def test_renderer_does_not_leak_master_placeholders() -> None:
    rendered = render_tailored_cv(
        _master(),
        _tailored(),
    )

    assert "[TITLE EXACTLY AS WRITTEN" not in rendered
    assert "[Your Title]" not in rendered
    assert "unsupported example claim" not in rendered
