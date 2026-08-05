from src.application_models import (
    ApplicationDocumentType,
    QualitySeverity,
)
from src.document_quality_checker import check_document_quality


def test_placeholder_causes_failure():
    result = check_document_quality(
        "Dear [COMPANY], I am applying for the role.",
        ApplicationDocumentType.COVER_LETTER,
    )
    assert result.passed is False
    assert any(
        item.code == "placeholder_found"
        for item in result.findings
    )


def test_keyword_coverage_is_calculated():
    result = check_document_quality(
        "Python and AWS data engineering work.",
        ApplicationDocumentType.CV,
        keywords=["python", "aws", "sql"],
    )
    assert result.keyword_coverage == 2 / 3


def test_clean_document_passes():
    result = check_document_quality(
        "Python SQL AWS Docker experience supporting reliable data pipelines.",
        ApplicationDocumentType.CV,
        keywords=["python", "sql", "aws"],
    )
    assert result.passed is True
