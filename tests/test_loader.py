"""Tests for src.career_data_loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.career_data_loader import (
    CareerDataLoadError,
    REQUIRED_FILES,
    check_required_files,
    find_repository_root,
    get_loaded_file_summary,
    load_career_data,
    read_yaml_file,
)


def test_find_repository_root_from_nested_directory(
    temporary_repository: Path,
) -> None:
    nested = temporary_repository / "src" / "nested"
    nested.mkdir(parents=True)

    assert find_repository_root(nested) == temporary_repository


def test_loader_reads_all_required_yaml_files(
    temporary_repository: Path,
) -> None:
    bundle = load_career_data(temporary_repository)
    summary = get_loaded_file_summary(bundle)

    assert summary["yaml_files"] == len(REQUIRED_FILES)
    assert summary["projects"] > 0
    assert summary["achievement_claims"] > 0
    assert summary["certifications"] > 0


def test_missing_required_file_produces_clear_error(
    temporary_repository: Path,
) -> None:
    missing_path = temporary_repository / "career_data" / "profile.yaml"
    missing_path.unlink()

    with pytest.raises(CareerDataLoadError) as error:
        check_required_files(temporary_repository)

    message = str(error.value)
    assert "Required career-data files are missing" in message
    assert "career_data/profile.yaml" in message


def test_malformed_yaml_reports_line_and_column(
    temporary_repository: Path,
) -> None:
    path = temporary_repository / "career_data" / "achievements.yaml"
    path.write_text(
        "schema_version: '1.0'\nclaims:\n  - claim_id: good\n- broken: true\n",
        encoding="utf-8",
    )

    with pytest.raises(CareerDataLoadError) as error:
        read_yaml_file(path)

    message = str(error.value)
    assert "Malformed YAML" in message
    assert "line" in message
    assert "column" in message


def test_empty_yaml_file_is_rejected(
    temporary_repository: Path,
) -> None:
    path = temporary_repository / "career_data" / "profile.yaml"
    path.write_text("", encoding="utf-8")

    with pytest.raises(CareerDataLoadError, match="is empty"):
        read_yaml_file(path)


def test_non_mapping_yaml_is_rejected(
    temporary_repository: Path,
) -> None:
    path = temporary_repository / "career_data" / "profile.yaml"
    path.write_text("- one\n- two\n", encoding="utf-8")

    with pytest.raises(CareerDataLoadError, match="top-level mapping"):
        read_yaml_file(path)


def test_invalid_model_field_is_reported(
    temporary_repository: Path,
) -> None:
    profile_path = temporary_repository / "career_data" / "profile.yaml"
    text = profile_path.read_text(encoding="utf-8")
    text = text.replace("minimum_salary_gbp: 50000", "minimum_salary_gbp: invalid")
    profile_path.write_text(text, encoding="utf-8")

    with pytest.raises(CareerDataLoadError) as error:
        load_career_data(temporary_repository)

    message = str(error.value)
    assert "Validation failed" in message
    assert "minimum_salary_gbp" in message
