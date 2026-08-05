"""Tests for src.privacy_scanner."""

from __future__ import annotations

from pathlib import Path

from src.privacy_scanner import (
    PrivacySeverity,
    scan_required_yaml_files,
    scan_text,
)


def test_current_yaml_files_have_no_critical_privacy_findings(
    repository_root: Path,
) -> None:
    result = scan_required_yaml_files(repository_root)

    assert result.critical == []
    assert result.status in {"passed", "passed_with_warnings"}


def test_github_token_is_critical() -> None:
    result = scan_text(
        "github_token: ghp_abcdefghijklmnopqrstuvwxyz1234567890",
        file_path="example.yaml",
    )

    assert any(
        finding.code == "github_token"
        and finding.severity == PrivacySeverity.CRITICAL
        for finding in result.findings
    )


def test_aws_access_key_is_critical() -> None:
    result = scan_text(
        "access_key: AKIAABCDEFGHIJKLMNOP",
        file_path="example.yaml",
    )

    assert any(
        finding.code == "aws_access_key"
        and finding.severity == PrivacySeverity.CRITICAL
        for finding in result.findings
    )


def test_private_key_is_critical() -> None:
    result = scan_text(
        "-----BEGIN PRIVATE KEY-----",
        file_path="example.yaml",
    )

    assert any(
        finding.code == "private_key"
        and finding.severity == PrivacySeverity.CRITICAL
        for finding in result.findings
    )


def test_national_insurance_number_is_critical() -> None:
    result = scan_text(
        "national_insurance_number: AB 12 34 56 C",
        file_path="example.yaml",
    )

    assert any(
        finding.code == "uk_national_insurance_number"
        and finding.severity == PrivacySeverity.CRITICAL
        for finding in result.findings
    )


def test_email_and_phone_are_informational() -> None:
    result = scan_text(
        "email: person@example.com\nphone: 07957 731 050\n",
        file_path="profile.yaml",
    )

    assert result.critical == []
    assert any(
        finding.code == "email_address"
        and finding.severity == PrivacySeverity.INFO
        for finding in result.findings
    )
    assert any(
        finding.code == "uk_phone_number"
        and finding.severity == PrivacySeverity.INFO
        for finding in result.findings
    )


def test_valid_payment_card_pattern_is_detected() -> None:
    result = scan_text(
        "card_number: 4111 1111 1111 1111",
        file_path="example.yaml",
    )

    assert any(
        finding.code == "payment_card_number"
        and finding.severity == PrivacySeverity.CRITICAL
        for finding in result.findings
    )


def test_non_luhn_numeric_value_is_not_treated_as_card() -> None:
    result = scan_text(
        "some_metric: 1234 5678 9012 3456",
        file_path="example.yaml",
    )

    assert not any(
        finding.code == "payment_card_number"
        for finding in result.findings
    )


def test_database_connection_string_with_password_is_critical() -> None:
    result = scan_text(
        "database_url: postgresql://user:supersecret@localhost:5432/app",
        file_path="example.yaml",
    )

    assert any(
        finding.code == "database_connection_string"
        and finding.severity == PrivacySeverity.CRITICAL
        for finding in result.findings
    )
