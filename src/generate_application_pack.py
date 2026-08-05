"""CLI for generating one human-review application pack."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from uuid import UUID

from rich.console import Console

from src.application_pack_builder import build_application_pack
from src.career_data_loader import find_repository_root, load_career_data
from src.career_profile_builder import build_career_matching_profile
from src.job_database import JobDatabase
from src.score_jobs import score_stored_jobs


console = Console()


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip())
    return cleaned.strip("_").lower() or "application"


def _find_match(job_id: UUID, results):
    for result in results:
        if result.job_id == job_id:
            return result
    raise KeyError(f"No scored match result found for job ID: {job_id}")


def generate_pack_for_job(
    job_id: str | UUID,
    *,
    repository_root: str | Path | None = None,
    db_path: str | Path | None = None,
    output_root: str | Path | None = None,
):
    root = (
        Path(repository_root).expanduser().resolve()
        if repository_root
        else find_repository_root(Path.cwd())
    )
    resolved_job_id = UUID(str(job_id))
    resolved_db = (
        Path(db_path).expanduser().resolve()
        if db_path
        else root / "data" / "jobs.db"
    )
    resolved_output = (
        Path(output_root).expanduser().resolve()
        if output_root
        else root / "output" / "applications"
    )

    bundle = load_career_data(root)
    profile = build_career_matching_profile(bundle)

    database = JobDatabase(resolved_db)
    database.initialise()
    job = database.get_job(resolved_job_id)
    if job is None:
        raise KeyError(f"Job not found in database: {resolved_job_id}")

    scored_results = score_stored_jobs(
        repository_root=root,
        db_path=resolved_db,
    )
    match = _find_match(resolved_job_id, scored_results)
    pack = build_application_pack(profile, match)

    folder = resolved_output / (
        f"{_slug(job.company)}_{_slug(job.title)}_{str(job.job_id)[:8]}"
    )
    folder.mkdir(parents=True, exist_ok=True)

    files = {
        "cv": folder / "tailored_cv.md",
        "cover_letter": folder / "cover_letter.md",
        "application_answers": folder / "application_answers.json",
        "interview_evidence": folder / "interview_evidence.md",
        "manifest": folder / "application_manifest.json",
    }

    files["cv"].write_text(pack.cv.markdown, encoding="utf-8")
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
        key: str(path.relative_to(root))
        if path.is_relative_to(root)
        else str(path)
        for key, path in files.items()
    }
    files["manifest"].write_text(
        json.dumps(pack.manifest.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    return pack, folder


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a human-review application pack for one job."
    )
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--root", dest="repository_root")
    parser.add_argument("--db", dest="db_path")
    parser.add_argument("--output-root")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    pack, folder = generate_pack_for_job(
        args.job_id,
        repository_root=args.repository_root,
        db_path=args.db_path,
        output_root=args.output_root,
    )

    console.print(f"Application pack created: {folder}")
    console.print(f"Status: {pack.manifest.status}")
    console.print("Human review is required before submission.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
