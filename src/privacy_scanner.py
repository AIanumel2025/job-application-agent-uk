"""Privacy and secret scanner for the UK Job Application Agent.

This module scans YAML source text for high-risk secrets and sensitive personal
data. It does not replace proper secret-management practices, but it provides a
useful safety gate before files are committed or used by later automation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
import re
from typing import Iterable

from src.career_data_loader import REQUIRED_FILES, CareerDataLoadError, find_repository_root


class PrivacySeverity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class PrivacyFinding:
    code: str
    severity: PrivacySeverity
    message: str
    file_path: str
    line_number: int | None = None
    matched_preview: str | None = None


@dataclass
class PrivacyScanResult:
    findings: list[PrivacyFinding] = field(default_factory=list)

    def add(
        self,
        *,
        code: str,
        severity: PrivacySeverity,
        message: str,
        file_path: str,
        line_number: int | None = None,
        matched_preview: str | None = None,
    ) -> None:
        self.findings.append(
            PrivacyFinding(
                code=code,
                severity=severity,
                message=message,
                file_path=file_path,
                line_number=line_number,
                matched_preview=matched_preview,
            )
        )

    @property
    def critical(self) -> list[PrivacyFinding]:
        return [
            finding
            for finding in self.findings
            if finding.severity == PrivacySeverity.CRITICAL
        ]

    @property
    def warnings(self) -> list[PrivacyFinding]:
        return [
            finding
            for finding in self.findings
            if finding.severity == PrivacySeverity.WARNING
        ]

    @property
    def infos(self) -> list[PrivacyFinding]:
        return [
            finding
            for finding in self.findings
            if finding.severity == PrivacySeverity.INFO
        ]

    @property
    def passed(self) -> bool:
        return not self.critical

    @property
    def status(self) -> str:
        if self.critical:
            return "failed"
        if self.warnings:
            return "passed_with_warnings"
        return "passed"

    def summary(self) -> dict[str, int | str]:
        return {
            "status": self.status,
            "critical": len(self.critical),
            "warnings": len(self.warnings),
            "infos": len(self.infos),
            "total_findings": len(self.findings),
        }


@dataclass(frozen=True)
class PatternRule:
    code: str
    pattern: re.Pattern[str]
    severity: PrivacySeverity
    message: str


def _compile(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


SECRET_RULES: tuple[PatternRule, ...] = (
    PatternRule(
        code="aws_access_key",
        pattern=re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
        severity=PrivacySeverity.CRITICAL,
        message="Possible AWS access key detected.",
    ),
    PatternRule(
        code="github_token",
        pattern=re.compile(
            r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,255}\b"
        ),
        severity=PrivacySeverity.CRITICAL,
        message="Possible GitHub token detected.",
    ),
    PatternRule(
        code="openai_api_key",
        pattern=re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
        severity=PrivacySeverity.CRITICAL,
        message="Possible API key detected.",
    ),
    PatternRule(
        code="generic_bearer_token",
        pattern=_compile(r"\bbearer\s+[A-Za-z0-9._~+/=-]{20,}\b"),
        severity=PrivacySeverity.CRITICAL,
        message="Possible bearer token detected.",
    ),
    PatternRule(
        code="private_key",
        pattern=re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
        ),
        severity=PrivacySeverity.CRITICAL,
        message="Private cryptographic key detected.",
    ),
    PatternRule(
        code="password_assignment",
        pattern=_compile(
            r"\b(?:password|passwd|pwd|secret)\b\s*[:=]\s*"
            r"['\"]?[^'\"\s]{8,}"
        ),
        severity=PrivacySeverity.CRITICAL,
        message="Possible password or secret value detected.",
    ),
    PatternRule(
        code="database_connection_string",
        pattern=_compile(
            r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?)://"
            r"[^:\s/]+:[^@\s]+@"
        ),
        severity=PrivacySeverity.CRITICAL,
        message="Database connection string with embedded credentials detected.",
    ),
)


PERSONAL_DATA_RULES: tuple[PatternRule, ...] = (
    PatternRule(
        code="uk_national_insurance_number",
        pattern=re.compile(
            r"\b(?!BG|GB|KN|NK|NT|TN|ZZ)"
            r"[A-CEGHJ-PR-TW-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D]\b",
            re.IGNORECASE,
        ),
        severity=PrivacySeverity.CRITICAL,
        message="Possible UK National Insurance number detected.",
    ),
    PatternRule(
        code="payment_card_number",
        pattern=re.compile(
            r"(?<!\d)(?:\d[ -]*?){13,19}(?!\d)"
        ),
        severity=PrivacySeverity.CRITICAL,
        message="Possible payment-card number detected.",
    ),
    PatternRule(
        code="iban",
        pattern=re.compile(
            r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b",
            re.IGNORECASE,
        ),
        severity=PrivacySeverity.CRITICAL,
        message="Possible IBAN detected.",
    ),
    PatternRule(
        code="passport_labelled_value",
        pattern=_compile(
            r"\bpassport(?:\s+(?:number|no\.?))?\s*[:=]\s*[A-Z0-9]{6,12}\b"
        ),
        severity=PrivacySeverity.CRITICAL,
        message="Possible passport number detected.",
    ),
    PatternRule(
        code="visa_document_number",
        pattern=_compile(
            r"\b(?:visa|brp|biometric residence permit)"
            r"(?:\s+(?:number|no\.?))?\s*[:=]\s*[A-Z0-9]{6,15}\b"
        ),
        severity=PrivacySeverity.CRITICAL,
        message="Possible visa or residence-permit document number detected.",
    ),
    PatternRule(
        code="full_street_address",
        pattern=_compile(
            r"\b\d{1,5}\s+[A-Za-z0-9.' -]{2,50}\s+"
            r"(?:street|st|road|rd|avenue|ave|lane|ln|drive|dr|close|"
            r"court|ct|way|gardens|place|pl)\b"
        ),
        severity=PrivacySeverity.WARNING,
        message="Possible full street address detected.",
    ),
)


EXPECTED_CONTACT_RULES: tuple[PatternRule, ...] = (
    PatternRule(
        code="email_address",
        pattern=re.compile(
            r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
            re.IGNORECASE,
        ),
        severity=PrivacySeverity.INFO,
        message="Email address present. Keep the repository private.",
    ),
    PatternRule(
        code="uk_phone_number",
        pattern=re.compile(
            r"(?<!\d)(?:\+44\s?7\d{3}|07\d{3})[\s-]?\d{3}[\s-]?\d{3}(?!\d)"
        ),
        severity=PrivacySeverity.INFO,
        message="UK phone number present. Keep the repository private.",
    ),
)


SAFE_LABELS = {
    "credential_id",
    "certification_number",
    "course_hours",
    "minimum_salary_gbp",
    "earned_date",
    "expiry_date",
    "generated_on",
    "confirmed_on",
    "earliest_start_date",
}


def _mask_match(value: str) -> str:
    """Return a non-sensitive preview of a matched value."""

    compact = value.strip()

    if len(compact) <= 8:
        return "***"

    return f"{compact[:3]}…{compact[-3:]}"


def _line_has_safe_label(line: str) -> bool:
    stripped = line.strip().lower()
    return any(stripped.startswith(f"{label}:") for label in SAFE_LABELS)


def _luhn_valid(number: str) -> bool:
    """Return True when a numeric string passes the Luhn checksum."""

    digits = [int(character) for character in number if character.isdigit()]

    if not 13 <= len(digits) <= 19:
        return False

    checksum = 0
    parity = len(digits) % 2

    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit

    return checksum % 10 == 0


def scan_text(
    text: str,
    *,
    file_path: str,
) -> PrivacyScanResult:
    """Scan one text document and return all findings."""

    result = PrivacyScanResult()

    for line_number, line in enumerate(text.splitlines(), start=1):
        if _line_has_safe_label(line):
            safe_labelled_line = True
        else:
            safe_labelled_line = False

        for rule in SECRET_RULES:
            for match in rule.pattern.finditer(line):
                result.add(
                    code=rule.code,
                    severity=rule.severity,
                    message=rule.message,
                    file_path=file_path,
                    line_number=line_number,
                    matched_preview=_mask_match(match.group(0)),
                )

        for rule in PERSONAL_DATA_RULES:
            for match in rule.pattern.finditer(line):
                if rule.code == "payment_card_number":
                    digits = re.sub(r"\D", "", match.group(0))

                    if safe_labelled_line or not _luhn_valid(digits):
                        continue

                result.add(
                    code=rule.code,
                    severity=rule.severity,
                    message=rule.message,
                    file_path=file_path,
                    line_number=line_number,
                    matched_preview=_mask_match(match.group(0)),
                )

        for rule in EXPECTED_CONTACT_RULES:
            for match in rule.pattern.finditer(line):
                result.add(
                    code=rule.code,
                    severity=rule.severity,
                    message=rule.message,
                    file_path=file_path,
                    line_number=line_number,
                    matched_preview=_mask_match(match.group(0)),
                )

    return result


def merge_results(
    destination: PrivacyScanResult,
    source: PrivacyScanResult,
) -> None:
    destination.findings.extend(source.findings)


def scan_file(path: Path, *, repository_root: Path) -> PrivacyScanResult:
    """Scan one UTF-8 text file."""

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        result = PrivacyScanResult()
        result.add(
            code="file_read_error",
            severity=PrivacySeverity.CRITICAL,
            message=f"Could not read file: {exc}",
            file_path=str(path.relative_to(repository_root)),
        )
        return result

    return scan_text(
        text,
        file_path=str(path.relative_to(repository_root)),
    )


def scan_required_yaml_files(
    repository_root: Path | str | None = None,
) -> PrivacyScanResult:
    """Scan the 13 YAML files required by the career-data loader."""

    if repository_root is None:
        root = find_repository_root()
    else:
        root = Path(repository_root).expanduser().resolve()

    if not root.is_dir():
        raise CareerDataLoadError(
            f"Repository root does not exist or is not a directory: {root}"
        )

    result = PrivacyScanResult()

    for definition in REQUIRED_FILES.values():
        path = root / definition.relative_path

        if not path.is_file():
            result.add(
                code="missing_file",
                severity=PrivacySeverity.CRITICAL,
                message="Required YAML file is missing.",
                file_path=str(definition.relative_path),
            )
            continue

        merge_results(
            result,
            scan_file(path, repository_root=root),
        )

    return result


def scan_additional_text_files(
    paths: Iterable[Path],
    *,
    repository_root: Path,
) -> PrivacyScanResult:
    """Scan extra text files selected by the caller."""

    result = PrivacyScanResult()

    for path in paths:
        resolved = path.expanduser().resolve()

        if not resolved.is_file():
            result.add(
                code="missing_file",
                severity=PrivacySeverity.WARNING,
                message="Optional file selected for scanning does not exist.",
                file_path=str(path),
            )
            continue

        merge_results(
            result,
            scan_file(resolved, repository_root=repository_root),
        )

    return result
