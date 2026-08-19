"""Tests for Phase 5.1 CV template selection."""

from pathlib import Path

import yaml
from docx import Document

from src.cv_template_loader import load_cv_registry
from src.cv_template_selector import (
    explain_selection,
    infer_role_family,
    select_cv_material,
)


def _docx(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    doc.add_paragraph(text)
    doc.save(path)


def _registry(tmp_path: Path):
    cv_dir = tmp_path / "source_documents" / "cv"
    _docx(cv_dir / "master.docx", "Master template")
    _docx(cv_dir / "ai.docx", "AI wording")
    _docx(cv_dir / "data.docx", "Data wording")
    _docx(cv_dir / "teach.docx", "Teaching wording")

    payload = {
        "version": 1,
        "factual_source_of_truth": "career_data/",
        "policy": {},
        "documents": {
            "master": {
                "file": "master.docx",
                "document_type": "master_template",
                "status": "active",
                "role_families": [
                    "ai_engineering",
                    "data_engineering",
                ],
                "uses": ["document_structure"],
                "wording_source": False,
                "factual_authority": False,
            },
            "ai": {
                "file": "ai.docx",
                "document_type": "reference_cv",
                "status": "active",
                "priority": 1,
                "role_families": [
                    "ai_engineering",
                    "machine_learning_engineering",
                ],
                "uses": ["approved_wording_reference"],
                "wording_source": True,
                "factual_authority": False,
            },
            "data": {
                "file": "data.docx",
                "document_type": "reference_cv",
                "status": "active",
                "priority": 1,
                "role_families": [
                    "data_engineering",
                    "data_analytics",
                    "data_quality",
                ],
                "uses": ["approved_wording_reference"],
                "wording_source": True,
                "factual_authority": False,
            },
            "teach": {
                "file": "teach.docx",
                "document_type": "reference_cv",
                "status": "active",
                "priority": 1,
                "role_families": ["teaching", "education"],
                "uses": ["approved_wording_reference"],
                "wording_source": True,
                "factual_authority": False,
            },
        },
        "selection_rules": {
            "default_master_template": "master",
            "maximum_reference_cvs_per_application": 2,
        },
        "excluded_files": [],
    }

    index = cv_dir / "cv_index.yaml"
    index.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
    return load_cv_registry(index)


def test_infers_common_role_families() -> None:
    assert infer_role_family("AI Engineering Intern") == "ai_engineering"
    assert infer_role_family("Data Engineer") == "data_engineering"
    assert infer_role_family("Power BI Analyst") == "business_intelligence"


def test_selects_data_reference_for_data_engineer(tmp_path) -> None:
    registry = _registry(tmp_path)

    selection = select_cv_material(
        registry,
        job_title="Data Engineer",
    )

    assert selection.master_template.path.name == "master.docx"
    assert selection.reference_cvs
    assert selection.reference_cvs[0].path.name == "data.docx"
    assert selection.fallback_used is False


def test_unknown_role_uses_master_only(tmp_path) -> None:
    registry = _registry(tmp_path)

    selection = select_cv_material(
        registry,
        job_title="Chief Happiness Officer",
    )

    assert selection.master_template.path.name == "master.docx"
    assert selection.reference_cvs == []
    assert selection.fallback_used is True
    assert "Fallback used: True" in explain_selection(selection)
