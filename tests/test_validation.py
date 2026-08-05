"""Tests for file-level and general business validation rules."""

from __future__ import annotations

from datetime import date

from src.validation_rules import (
    Severity,
    ValidationResult,
    run_all_validation_rules,
    validate_application_answers,
    validate_claim_safety,
    validate_dates_and_expiry,
    validate_salary_consistency,
    validate_unique_ids,
)


def test_current_bundle_has_no_validation_errors(valid_bundle) -> None:
    result = run_all_validation_rules(
        valid_bundle,
        as_of=date(2026, 8, 3),
    )

    assert result.errors == []
    assert result.status in {"passed", "passed_with_warnings"}


def test_duplicate_project_id_is_an_error(mutable_bundle) -> None:
    duplicate = mutable_bundle.projects.projects[0].model_copy(deep=True)
    mutable_bundle.projects.projects.append(duplicate)

    result = ValidationResult()
    validate_unique_ids(mutable_bundle, result)

    assert any(
        issue.code == "duplicate_id"
        and issue.severity == Severity.ERROR
        and issue.record_id == duplicate.project_id
        for issue in result.issues
    )


def test_blocked_claim_is_reported_but_not_fatal_when_unapproved(
    mutable_bundle,
) -> None:
    claim = next(
        item
        for item in mutable_bundle.achievements.claims
        if item.claim_id == "claim_fintech_risk_accuracy_80"
    )
    assert claim.approved_for_application is False

    result = ValidationResult()
    validate_claim_safety(mutable_bundle, result)

    assert any(
        issue.code == "blocked_claim"
        and issue.record_id == claim.claim_id
        and issue.severity == Severity.WARNING
        for issue in result.issues
    )


def test_missing_required_application_answer_is_an_error(
    mutable_bundle,
) -> None:
    del mutable_bundle.application_answers.answers["notice_period"]

    result = ValidationResult()
    validate_application_answers(mutable_bundle, result)

    assert any(
        issue.code == "missing_application_answer"
        and issue.record_id == "notice_period"
        and issue.severity == Severity.ERROR
        for issue in result.issues
    )


def test_sensitive_answer_must_require_review(mutable_bundle) -> None:
    answer = mutable_bundle.application_answers.answers[
        "right_to_work_in_uk"
    ]
    answer.review_before_submission = False

    result = ValidationResult()
    validate_application_answers(mutable_bundle, result)

    assert any(
        issue.code == "sensitive_answer_not_reviewed"
        and issue.record_id == "right_to_work_in_uk"
        for issue in result.errors
    )


def test_salary_mismatch_is_an_error(mutable_bundle) -> None:
    mutable_bundle.target_roles.minimum_salary_gbp = 60000

    result = ValidationResult()
    validate_salary_consistency(mutable_bundle, result)

    assert any(
        issue.code == "salary_mismatch"
        and issue.severity == Severity.ERROR
        for issue in result.issues
    )


def test_expired_certification_generates_warning(mutable_bundle) -> None:
    certification = mutable_bundle.certifications.certifications[0]
    certification.expiry_date = date(2026, 1, 1)

    result = ValidationResult()
    validate_dates_and_expiry(
        mutable_bundle,
        result,
        as_of=date(2026, 8, 3),
    )

    assert any(
        issue.code == "expired_certification"
        and issue.record_id == certification.certification_id
        and issue.severity == Severity.WARNING
        for issue in result.issues
    )


def test_validation_result_statuses() -> None:
    result = ValidationResult()
    assert result.status == "passed"

    result.add(
        "example_warning",
        Severity.WARNING,
        "Example warning",
    )
    assert result.status == "passed_with_warnings"

    result.add(
        "example_error",
        Severity.ERROR,
        "Example error",
    )
    assert result.status == "failed"
