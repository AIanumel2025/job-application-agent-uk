"""Models for tracking an application's hiring-process lifecycle."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class LifecycleModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )


class ApplicationLifecycleStatus(StrEnum):
    REVIEW_REQUIRED = "review_required"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    READY_TO_SUBMIT = "ready_to_submit"
    SUBMITTED = "submitted"
    SCREENING = "screening"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ApplicationLifecycleEvent(LifecycleModel):
    event_id: UUID = Field(
        default_factory=uuid4
    )

    from_status: ApplicationLifecycleStatus | None = None

    to_status: ApplicationLifecycleStatus

    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )

    note: str | None = None


class ApplicationLifecycleRecord(LifecycleModel):
    lifecycle_id: UUID = Field(
        default_factory=uuid4
    )

    job_id: UUID

    current_status: ApplicationLifecycleStatus

    application_url: HttpUrl | None = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )

    submitted_at: datetime | None = None

    notes: list[str] = Field(
        default_factory=list
    )

    history: list[ApplicationLifecycleEvent] = Field(
        default_factory=list
    )
