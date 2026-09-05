"""Human review workflow for generated application packs."""

from __future__ import annotations
from src.application_pack_service import (
    generate_application_pack_for_job,
)
from src.postgres_job_database import (
    PostgresJobDatabase,
)
import json
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path

from src.application_models import (
    ApplicationPackManifest,
    ApplicationPackStatus,
    ClaimStatus,
)
from src.career_data_loader import find_repository_root


class ApplicationReviewDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    CHANGES_REQUESTED = "changes_requested"


def _find_manifest(
    job_id: str,
    repository_root: str | Path | None = None,
) -> Path:
    root = (
        Path(repository_root).expanduser().resolve()
        if repository_root
        else find_repository_root(Path.cwd())
    )

    applications_root = (
        root
        / "output"
        / "applications"
    )

    if not applications_root.exists():
        raise FileNotFoundError(
            "Application output directory does not exist."
        )

    matches: list[Path] = []

    for manifest_path in applications_root.glob(
        "*/application_manifest.json"
    ):
        try:
            data = json.loads(
                manifest_path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            json.JSONDecodeError,
            OSError,
        ):
            continue

        if str(
            data.get("job_id") or ""
        ) == str(job_id):
            matches.append(
                manifest_path
            )

    if not matches:
        raise FileNotFoundError(
            f"No application pack found for job: {job_id}"
        )

    # Current folder naming is deterministic, but sorting also
    # keeps this safe if multiple versions exist later.
    matches.sort(
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    return matches[0]


def review_application_pack(
    *,
    job_id: str,
    decision: ApplicationReviewDecision,
    notes: str | None = None,
    repository_root: str | Path | None = None,
) -> tuple[ApplicationPackManifest, Path]:
    """Apply an explicit human review decision to one application pack."""

    manifest_path = _find_manifest(
        job_id,
        repository_root=repository_root,
    )

    manifest = ApplicationPackManifest.model_validate_json(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    if decision == ApplicationReviewDecision.APPROVE:
        blocked_claims = [
            check
            for check in manifest.claim_checks
            if check.status == ClaimStatus.BLOCKED
        ]

        if (
            manifest.status
            == ApplicationPackStatus.BLOCKED
            or blocked_claims
        ):
            raise ValueError(
                "Blocked application packs cannot be approved."
            )

        manifest.status = (
            ApplicationPackStatus.APPROVED
        )

        manifest.human_review_required = False

    elif decision == ApplicationReviewDecision.REJECT:
        manifest.status = (
            ApplicationPackStatus.REJECTED
        )

        manifest.human_review_required = False

    elif (
        decision
        == ApplicationReviewDecision.CHANGES_REQUESTED
    ):
        manifest.status = (
            ApplicationPackStatus.CHANGES_REQUESTED
        )

        manifest.human_review_required = True

    else:
        raise ValueError(
            f"Unsupported review decision: {decision}"
        )

    if notes and notes.strip():
        manifest.review_notes.append(
            notes.strip()
        )

    manifest.reviewed_at = datetime.now(
        timezone.utc
    )

    manifest_path.write_text(
        json.dumps(
            manifest.model_dump(
                mode="json"
            ),
            indent=2,
        ),
        encoding="utf-8",
    )

    return (
        manifest,
        manifest_path.parent,
    )

def regenerate_application_pack(
    *,
    job_id: str,
    database: PostgresJobDatabase | None = None,
    repository_root: str | Path | None = None,
) -> tuple[ApplicationPackManifest, Path]:
    """
    Regenerate an application pack after human-requested changes.

    Human review notes are preserved as instructions/history.
    The regenerated pack returns to REVIEW_REQUIRED.
    """

    manifest_path = _find_manifest(
        job_id,
        repository_root=repository_root,
    )

    previous_manifest = (
        ApplicationPackManifest.model_validate_json(
            manifest_path.read_text(
                encoding="utf-8"
            )
        )
    )

    if (
        previous_manifest.status
        != ApplicationPackStatus.CHANGES_REQUESTED
    ):
        raise ValueError(
            "Application pack can only be regenerated "
            "after changes have been requested."
        )

    db = database or PostgresJobDatabase()
    db.initialise()

    job = db.get_job(
        str(previous_manifest.job_id)
    )

    if job is None:
        raise FileNotFoundError(
            f"Job not found: {previous_manifest.job_id}"
        )

    old_notes = list(
        previous_manifest.review_notes
    )

    old_regeneration_count = (
        previous_manifest.regeneration_count
    )

    pack, folder = generate_application_pack_for_job(
        job,
        repository_root=repository_root,
    )

    # Carry human review history forward.
    pack.manifest.review_notes = old_notes

    pack.manifest.regeneration_count = (
        old_regeneration_count + 1
    )

    pack.manifest.last_regenerated_at = (
        datetime.now(timezone.utc)
    )

    # A regenerated pack must always return to human review.
    pack.manifest.status = (
        ApplicationPackStatus.REVIEW_REQUIRED
    )

    pack.manifest.human_review_required = True

    regenerated_manifest_path = (
        folder
        / "application_manifest.json"
    )

    regenerated_manifest_path.write_text(
        json.dumps(
            pack.manifest.model_dump(
                mode="json"
            ),
            indent=2,
        ),
        encoding="utf-8",
    )

    return (
        pack.manifest,
        folder,
    )
