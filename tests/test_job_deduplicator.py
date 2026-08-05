from __future__ import annotations

from src.job_deduplicator import compare_jobs, find_duplicate


def test_exact_url_is_duplicate(sample_job) -> None:
    incoming = sample_job.model_copy(deep=True)
    match = compare_jobs(incoming, sample_job)
    assert match is not None
    assert match.confidence == 1.0
    assert "canonical_url" in match.matching_fields


def test_description_hash_is_duplicate(sample_job) -> None:
    incoming = sample_job.model_copy(
        update={
            "job_id": "7f95e83e-39dd-4f36-bf03-f6580835b6a9",
            "canonical_url": "https://mirror.example.com/ai-123",
            "source_job_id": None,
        }
    )
    match = compare_jobs(incoming, sample_job)
    assert match is not None
    assert "description_hash" in match.matching_fields


def test_different_jobs_are_not_duplicates(sample_job) -> None:
    incoming = sample_job.model_copy(
        update={
            "job_id": "ce93c627-d02d-4a61-af29-669c8f682a78",
            "canonical_url": "https://other.example.com/accountant",
            "title": "Financial Accountant",
            "title_normalised": "financial accountant",
            "company": "Other PLC",
            "company_normalised": "other",
            "description": "Prepare statutory accounts.",
            "description_hash": "different",
            "source_job_id": "ACC-9",
        }
    )
    result = find_duplicate(incoming, [sample_job])
    assert result.is_duplicate is False
    assert result.best_match is None
