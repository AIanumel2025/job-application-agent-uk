"""Service for controlled application lifecycle transitions."""

from __future__ import annotations

from datetime import datetime, timezone

from src.application_lifecycle_models import (
    ApplicationLifecycleEvent,
    ApplicationLifecycleRecord,
    ApplicationLifecycleStatus,
)
from src.postgres_job_database import (
    PostgresJobDatabase,
)


_ALLOWED_TRANSITIONS: dict[
    ApplicationLifecycleStatus,
    set[ApplicationLifecycleStatus],
] = {
    ApplicationLifecycleStatus.REVIEW_REQUIRED: {
        ApplicationLifecycleStatus.CHANGES_REQUESTED,
        ApplicationLifecycleStatus.APPROVED,
        ApplicationLifecycleStatus.REJECTED,
        ApplicationLifecycleStatus.WITHDRAWN,
    },

    ApplicationLifecycleStatus.CHANGES_REQUESTED: {
        ApplicationLifecycleStatus.REVIEW_REQUIRED,
        ApplicationLifecycleStatus.REJECTED,
        ApplicationLifecycleStatus.WITHDRAWN,
    },

    ApplicationLifecycleStatus.APPROVED: {
        ApplicationLifecycleStatus.READY_TO_SUBMIT,
        ApplicationLifecycleStatus.REJECTED,
        ApplicationLifecycleStatus.WITHDRAWN,
    },

    ApplicationLifecycleStatus.READY_TO_SUBMIT: {
        ApplicationLifecycleStatus.SUBMITTED,
        ApplicationLifecycleStatus.WITHDRAWN,
    },

    ApplicationLifecycleStatus.SUBMITTED: {
        ApplicationLifecycleStatus.SCREENING,
        ApplicationLifecycleStatus.INTERVIEW,
        ApplicationLifecycleStatus.REJECTED,
        ApplicationLifecycleStatus.WITHDRAWN,
    },

    ApplicationLifecycleStatus.SCREENING: {
        ApplicationLifecycleStatus.INTERVIEW,
        ApplicationLifecycleStatus.REJECTED,
        ApplicationLifecycleStatus.WITHDRAWN,
    },

    ApplicationLifecycleStatus.INTERVIEW: {
        ApplicationLifecycleStatus.OFFER,
        ApplicationLifecycleStatus.REJECTED,
        ApplicationLifecycleStatus.WITHDRAWN,
    },

    ApplicationLifecycleStatus.OFFER: {
        ApplicationLifecycleStatus.WITHDRAWN,
    },

    ApplicationLifecycleStatus.REJECTED: set(),

    ApplicationLifecycleStatus.WITHDRAWN: set(),
}


def create_application_lifecycle(
    *,
    job_id: str,
    database: PostgresJobDatabase | None = None,
    application_url: str | None = None,
    note: str | None = None,
) -> ApplicationLifecycleRecord:
    """
    Create an application lifecycle record.

    New records start at REVIEW_REQUIRED.
    """

    db = database or PostgresJobDatabase()
    db.initialise()

    existing = db.get_application_lifecycle(
        job_id
    )

    if existing is not None:
        return existing

    now = datetime.now(
        timezone.utc
    )

    event = ApplicationLifecycleEvent(
        from_status=None,
        to_status=(
            ApplicationLifecycleStatus.REVIEW_REQUIRED
        ),
        occurred_at=now,
        note=note,
    )

    record = ApplicationLifecycleRecord(
        job_id=job_id,
        current_status=(
            ApplicationLifecycleStatus.REVIEW_REQUIRED
        ),
        application_url=application_url,
        created_at=now,
        updated_at=now,
        notes=(
            [note]
            if note
            else []
        ),
        history=[
            event
        ],
    )

    db.save_application_lifecycle(
        record
    )

    return record


def transition_application_lifecycle(
    *,
    job_id: str,
    to_status: ApplicationLifecycleStatus,
    database: PostgresJobDatabase | None = None,
    note: str | None = None,
) -> ApplicationLifecycleRecord:
    """
    Move an application to a new lifecycle status.

    Invalid transitions are rejected.
    """

    db = database or PostgresJobDatabase()
    db.initialise()

    record = db.get_application_lifecycle(
        job_id
    )

    if record is None:
        raise KeyError(
            f"application lifecycle does not exist for job: {job_id}"
        )

    current_status = (
        ApplicationLifecycleStatus(
            record.current_status
        )
    )

    target_status = (
        ApplicationLifecycleStatus(
            to_status
        )
    )

    if target_status == current_status:
        return record

    allowed = _ALLOWED_TRANSITIONS.get(
        current_status,
        set(),
    )

    if target_status not in allowed:
        raise ValueError(
            "invalid application lifecycle transition: "
            f"{current_status} -> {target_status}"
        )

    now = datetime.now(
        timezone.utc
    )

    event = ApplicationLifecycleEvent(
        from_status=current_status,
        to_status=target_status,
        occurred_at=now,
        note=note,
    )

    record.current_status = (
        target_status
    )

    record.updated_at = now

    if (
        target_status
        == ApplicationLifecycleStatus.SUBMITTED
        and record.submitted_at is None
    ):
        record.submitted_at = now

    if note:
        record.notes.append(
            note
        )

    record.history.append(
        event
    )

    db.save_application_lifecycle(
        record
    )

    return record


def get_application_lifecycle(
    *,
    job_id: str,
    database: PostgresJobDatabase | None = None,
) -> ApplicationLifecycleRecord | None:
    db = database or PostgresJobDatabase()
    db.initialise()

    return db.get_application_lifecycle(
        job_id
    )


def list_application_lifecycles(
    *,
    status: ApplicationLifecycleStatus | None = None,
    database: PostgresJobDatabase | None = None,
) -> list[ApplicationLifecycleRecord]:
    db = database or PostgresJobDatabase()
    db.initialise()

    return db.list_application_lifecycles(
        status=(
            str(status)
            if status is not None
            else None
        )
    )
