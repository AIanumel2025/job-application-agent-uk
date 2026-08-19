"""Reusable application-pack generation service."""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.application_models import ApplicationPack
from src.application_pack_builder import build_application_pack
from src.career_data_loader import find_repository_root
from src.job_models import NormalisedJob
from src.job_scoring_service import (
    load_matching_profile,
    score_job,
)


def _slug(value: str) -> str:
    cleaned = re.sub(
        r"[^a-zA-Z0-9]+",
        "_",
        value.strip(),
    )
    return cleaned.strip("_").lower() or "application"


def generate_application_pack_for_job(
    job: NormalisedJob,
    *,
    repository_root: str | Path | None = None,
    output_root: str | Path | None = None,
) -> tuple[ApplicationPack, Path]:
    """Build and persist one human-review application pack."""

    root = (
        Path(repository_root).expanduser().resolve()
        if repository_root
        else find_repository_root(Path.cwd())
    )

    resolved_output = (
        Path(output_root).expanduser().resolve()
        if output_root
        else root / "output" / "applications"
    )

    profile = load_matching_profile(root)

    match = score_job(
        job,
        profile,
    )

    pack = build_application_pack(
        profile,
        match,
    )

    folder = resolved_output / (
        f"{_slug(job.company)}_"
        f"{_slug(job.title)}_"
        f"{str(job.job_id)[:8]}"
    )

    folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    files = {
        "cv": folder / "tailored_cv.md",
        "cover_letter": folder / "cover_letter.md",
        "application_answers": folder
        / "application_answers.json",
        "interview_evidence": folder
        / "interview_evidence.md",
        "manifest": folder
        / "application_manifest.json",
    }

    files["cv"].write_text(
        pack.cv.markdown,
        encoding="utf-8",
    )

    files["cover_letter"].write_text(
        pack.cover_letter.markdown,
        encoding="utf-8",
    )

    files["application_answers"].write_text(
        json.dumps(
            [
                item.model_dump(mode="json")
                for item in pack.application_answers
            ],
            indent=2,
        ),
        encoding="utf-8",
    )

    files["interview_evidence"].write_text(
        pack.interview_evidence_markdown,
        encoding="utf-8",
    )

    pack.manifest.files = {
        key: (
            str(path.relative_to(root))
            if path.is_relative_to(root)
            else str(path)
        )
        for key, path in files.items()
    }

    files["manifest"].write_text(
        json.dumps(
            pack.manifest.model_dump(mode="json"),
            indent=2,
        ),
        encoding="utf-8",
    )

    return pack, folder
