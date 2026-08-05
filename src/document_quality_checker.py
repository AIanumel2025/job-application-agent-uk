"""Run deterministic quality checks on generated application documents."""

from __future__ import annotations

import re
from collections import Counter

from src.application_models import (
    ApplicationDocumentType,
    DocumentQualityResult,
    QualityFinding,
    QualitySeverity,
)


def _tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9+#.-]+", text.casefold())


def _keyword_coverage(text: str, keywords: list[str]) -> float:
    if not keywords:
        return 1.0

    lowered = text.casefold()
    matched = sum(
        keyword.casefold() in lowered
        for keyword in keywords
    )
    return matched / len(keywords)


def _repetition_ratio(text: str) -> float:
    tokens = [
        token
        for token in _tokens(text)
        if len(token) >= 4
    ]
    if not tokens:
        return 0.0

    counts = Counter(tokens)
    repeated = sum(count - 1 for count in counts.values() if count > 1)
    return repeated / len(tokens)


def check_document_quality(
    text: str,
    document_type: ApplicationDocumentType,
    *,
    keywords: list[str] | None = None,
    minimum_words: int | None = None,
    maximum_words: int | None = None,
) -> DocumentQualityResult:
    keywords = keywords or []
    findings: list[QualityFinding] = []
    word_count = len(text.split())

    placeholders = ("[COMPANY]", "[ROLE]", "[NAME]", "TODO", "TBC")
    for placeholder in placeholders:
        if placeholder.casefold() in text.casefold():
            findings.append(
                QualityFinding(
                    code="placeholder_found",
                    severity=QualitySeverity.ERROR,
                    document_type=document_type,
                    message=f"Unresolved placeholder found: {placeholder}",
                )
            )

    if minimum_words is not None and word_count < minimum_words:
        findings.append(
            QualityFinding(
                code="too_short",
                severity=QualitySeverity.WARNING,
                document_type=document_type,
                message=(
                    f"Document has {word_count} words; minimum is {minimum_words}."
                ),
            )
        )

    if maximum_words is not None and word_count > maximum_words:
        findings.append(
            QualityFinding(
                code="too_long",
                severity=QualitySeverity.WARNING,
                document_type=document_type,
                message=(
                    f"Document has {word_count} words; maximum is {maximum_words}."
                ),
            )
        )

    generic_phrases = (
        "i am a perfect fit",
        "results-driven professional",
        "dynamic individual",
        "hard-working team player",
    )
    for phrase in generic_phrases:
        if phrase in text.casefold():
            findings.append(
                QualityFinding(
                    code="generic_phrase",
                    severity=QualitySeverity.WARNING,
                    document_type=document_type,
                    message=f"Generic wording detected: {phrase}",
                )
            )

    coverage = _keyword_coverage(text, keywords)
    repetition = _repetition_ratio(text)

    if coverage < 0.50:
        findings.append(
            QualityFinding(
                code="low_keyword_coverage",
                severity=QualitySeverity.WARNING,
                document_type=document_type,
                message="Less than half of the target keywords appear.",
            )
        )

    if repetition > 0.20:
        findings.append(
            QualityFinding(
                code="high_repetition",
                severity=QualitySeverity.WARNING,
                document_type=document_type,
                message="The document repeats too many significant words.",
            )
        )

    deductions = {
        QualitySeverity.INFO: 0,
        QualitySeverity.WARNING: 8,
        QualitySeverity.ERROR: 20,
        QualitySeverity.CRITICAL: 40,
    }
    score = max(
        0.0,
        100.0 - sum(deductions[item.severity] for item in findings),
    )
    passed = not any(
        item.severity in {
            QualitySeverity.ERROR,
            QualitySeverity.CRITICAL,
        }
        for item in findings
    )

    return DocumentQualityResult(
        document_type=document_type,
        passed=passed,
        score=score,
        findings=findings,
        keyword_coverage=coverage,
        repetition_ratio=repetition,
    )
