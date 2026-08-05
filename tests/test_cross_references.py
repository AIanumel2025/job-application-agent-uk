"""Tests for cross-file reference and consistency rules."""

from __future__ import annotations

from src.validation_rules import (
    Severity,
    ValidationResult,
    validate_certification_consistency,
    validate_claim_references,
    validate_confidential_projects,
    validate_project_link_consistency,
    validate_project_references,
)


def test_missing_claim_reference_is_an_error(mutable_bundle) -> None:
    project = mutable_bundle.projects.projects[0]
    project.outcomes[0].claim_id = "claim_that_does_not_exist"

    result = ValidationResult()
    validate_claim_references(mutable_bundle, result)

    assert any(
        issue.code == "missing_claim_reference"
        and issue.record_id == project.project_id
        and issue.severity == Severity.ERROR
        for issue in result.issues
    )


def test_unknown_article_project_reference_is_an_error(
    mutable_bundle,
) -> None:
    article = mutable_bundle.article_links.articles[0]
    article.related_project_ids.append("unknown_project")

    result = ValidationResult()
    validate_project_references(mutable_bundle, result)

    assert any(
        issue.code == "missing_project_reference"
        and issue.record_id == article.article_id
        and issue.severity == Severity.ERROR
        for issue in result.issues
    )


def test_repository_url_mismatch_is_an_error(mutable_bundle) -> None:
    public_project = next(
        project
        for project in mutable_bundle.projects.projects
        if project.repository_url is not None
    )
    link = next(
        record
        for record in mutable_bundle.project_links.projects
        if record.project_id == public_project.project_id
    )
    link.repository_url = "https://github.com/example/different-repository"

    result = ValidationResult()
    validate_project_link_consistency(mutable_bundle, result)

    assert any(
        issue.code == "repository_url_mismatch"
        and issue.record_id == public_project.project_id
        for issue in result.errors
    )


def test_orphan_project_link_is_an_error(mutable_bundle) -> None:
    orphan = mutable_bundle.project_links.projects[0].model_copy(deep=True)
    orphan.project_id = "orphan_project"
    mutable_bundle.project_links.projects.append(orphan)

    result = ValidationResult()
    validate_project_link_consistency(mutable_bundle, result)

    assert any(
        issue.code == "orphan_project_link_entry"
        and issue.record_id == "orphan_project"
        for issue in result.errors
    )


def test_certification_mismatch_is_an_error(mutable_bundle) -> None:
    indexed = mutable_bundle.certification_index.certifications[0]
    indexed.provider = "Different Provider"

    result = ValidationResult()
    validate_certification_consistency(mutable_bundle, result)

    assert any(
        issue.code == "certification_mismatch"
        and issue.record_id == indexed.certification_id
        and issue.field_path == "provider"
        for issue in result.errors
    )


def test_confidential_project_must_not_expose_repository(
    mutable_bundle,
) -> None:
    confidential = next(
        project
        for project in mutable_bundle.projects.projects
        if project.project_id == "document_intelligence_etl_pipeline"
    )
    confidential.repository_url = "https://github.com/example/private-work"

    result = ValidationResult()
    validate_confidential_projects(mutable_bundle, result)

    assert any(
        issue.code == "confidential_repository_exposed"
        and issue.record_id == confidential.project_id
        for issue in result.errors
    )


def test_current_cross_file_references_have_no_errors(valid_bundle) -> None:
    result = ValidationResult()

    validate_claim_references(valid_bundle, result)
    validate_project_references(valid_bundle, result)
    validate_project_link_consistency(valid_bundle, result)
    validate_certification_consistency(valid_bundle, result)
    validate_confidential_projects(valid_bundle, result)

    assert result.errors == []
