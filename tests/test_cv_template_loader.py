"""Tests for Phase 5.1 CV template loading."""

from pathlib import Path

import yaml
from docx import Document

from src.cv_template_loader import (
    CVTemplateLoaderError,
    load_active_reference_cvs,
    load_cv_registry,
    load_default_master_template,
)


def _write_docx(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    for line in lines:
        document.add_paragraph(line)
    document.save(path)


def _write_registry(root: Path) -> Path:
    cv_dir = root / "source_documents" / "cv"
    cv_dir.mkdir(parents=True, exist_ok=True)

    _write_docx(
        cv_dir / "master.docx",
        ["MASTER", "PROFESSIONAL SUMMARY", "Stable content"],
    )
    _write_docx(
        cv_dir / "ai.docx",
        ["AI ENGINEER", "Built Python systems."],
    )

    payload = {
        "version": 1,
        "factual_source_of_truth": "career_data/",
        "policy": {
            "cv_documents_are_factual_authority": False,
        },
        "documents": {
            "master": {
                "file": "master.docx",
                "document_type": "master_template",
                "status": "active",
                "role_families": ["ai_engineering"],
                "uses": ["document_structure"],
                "wording_source": False,
                "factual_authority": False,
            },
            "ai_reference": {
                "file": "ai.docx",
                "document_type": "reference_cv",
                "status": "active",
                "priority": 1,
                "role_families": ["ai_engineering"],
                "uses": ["approved_wording_reference"],
                "wording_source": True,
                "factual_authority": False,
            },
        },
        "selection_rules": {
            "default_master_template": "master",
            "maximum_reference_cvs_per_application": 2,
        },
        "excluded_files": [".DS_Store"],
    }

    index = cv_dir / "cv_index.yaml"
    index.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
    return index


def test_loads_registered_master_and_reference(tmp_path) -> None:
    index = _write_registry(tmp_path)
    registry = load_cv_registry(index)

    master = load_default_master_template(registry)
    references = load_active_reference_cvs(registry)

    assert master.path.name == "master.docx"
    assert master.document_type == "master_template"
    assert len(references) == 1
    assert references[0].path.name == "ai.docx"
    assert references[0].wording_source is True


def test_registry_preserves_factual_source_policy(tmp_path) -> None:
    index = _write_registry(tmp_path)
    registry = load_cv_registry(index)

    assert registry.factual_source_of_truth == "career_data/"
    assert (
        registry.policy["cv_documents_are_factual_authority"]
        is False
    )


def test_missing_registered_docx_is_rejected(tmp_path) -> None:
    index = _write_registry(tmp_path)
    data = yaml.safe_load(index.read_text(encoding="utf-8"))
    data["documents"]["ai_reference"]["file"] = "missing.docx"
    index.write_text(
        yaml.safe_dump(data, sort_keys=False),
        encoding="utf-8",
    )

    try:
        load_cv_registry(index)
    except CVTemplateLoaderError as exc:
        assert "does not exist" in str(exc).casefold()
    else:
        raise AssertionError("Expected missing registered CV to fail.")
