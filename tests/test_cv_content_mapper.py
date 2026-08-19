"""Tests for Phase 5.1 CV-to-evidence content mapping."""

from pathlib import Path

from src.cv_content_mapper import map_reference_cv_to_evidence
from src.cv_template_loader import LoadedCVDocument
from src.matching_models import CareerEvidence


def _document(lines: list[str]) -> LoadedCVDocument:
    return LoadedCVDocument(
        registry_key="ai_reference",
        path=Path("source_documents/cv/ai.docx"),
        document_type="reference_cv",
        status="active",
        role_families=["ai_engineering"],
        uses=["approved_wording_reference"],
        wording_source=True,
        factual_authority=False,
        priority=1,
        paragraphs=lines,
        table_rows=[],
        full_text="\n".join(lines),
        notes=None,
    )


def _evidence(
    description: str,
    *,
    evidence_id: str = "project_1",
    verified: bool = True,
) -> CareerEvidence:
    return CareerEvidence(
        evidence_id=evidence_id,
        evidence_type="project",
        source_record_id="project_pipeline",
        title="Document Intelligence Pipeline",
        description=description,
        verified=verified,
        approved_for_application=True,
    )


def test_maps_relevant_reference_wording_to_evidence() -> None:
    document = _document(
        ["Built a Python and AWS document-processing pipeline using Docker."]
    )
    evidence = [
        _evidence(
            "Built a Python and AWS document-processing pipeline "
            "using Docker and GitHub Actions."
        )
    ]

    candidates = map_reference_cv_to_evidence(document, evidence)

    assert len(candidates) == 1
    assert candidates[0].matched_evidence_ids == ["project_1"]
    assert candidates[0].approved_for_reuse is True


def test_unsupported_numeric_claim_is_not_reusable() -> None:
    document = _document(
        ["Improved document processing accuracy by 75% using Python and AWS."]
    )
    evidence = [
        _evidence(
            "Built a Python and AWS document-processing pipeline "
            "using Docker."
        )
    ]

    candidates = map_reference_cv_to_evidence(
        document,
        evidence,
        minimum_similarity=0.10,
    )

    assert len(candidates) == 1
    assert candidates[0].contains_numeric_claim is True
    assert candidates[0].numeric_claim_supported is False
    assert candidates[0].approved_for_reuse is False
    assert candidates[0].review_required is True


def test_supported_numeric_claim_can_be_reused() -> None:
    document = _document(
        ["Improved document processing accuracy by 50% using Python."]
    )
    evidence = [
        _evidence(
            "Improved document processing accuracy by 50% using Python."
        )
    ]

    candidates = map_reference_cv_to_evidence(document, evidence)

    assert candidates[0].numeric_claim_supported is True
    assert candidates[0].approved_for_reuse is True
