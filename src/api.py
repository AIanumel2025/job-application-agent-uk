"""FastAPI entry point for the Job Application Agent."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl

from src.application_batch_service import (
    generate_top_application_packs,
)
from src.application_lifecycle_models import (
    ApplicationLifecycleStatus,
)
from src.application_lifecycle_service import (
    create_application_lifecycle,
    get_application_lifecycle,
    list_application_lifecycles,
    transition_application_lifecycle,
)
from src.application_pack_service import (
    generate_application_pack_for_job,
)
from src.application_review_service import (
    ApplicationReviewDecision,
    regenerate_application_pack,
    review_application_pack,
)
from src.configured_job_search_service import (
    search_configured_jobs,
)
from src.job_discovery_ingestion_service import (
    discover_and_ingest_greenhouse_jobs,
)
from src.job_discovery_scoring_service import (
    discover_ingest_score_greenhouse_jobs,
)
from src.job_discovery_service import (
    discover_greenhouse_jobs,
)
from src.job_ingestion_service import (
    ingest_job_url,
)
from src.job_models import (
    IngestionRun,
    JobSource,
    NormalisedJob,
)
from src.job_scoring_service import (
    load_matching_profile,
    score_job,
)
from src.matching_models import (
    JobMatchResult,
)
from src.postgres_job_database import (
    PostgresJobDatabase,
)


class ApplicationReviewRequest(BaseModel):
    decision: ApplicationReviewDecision
    notes: str | None = Field(
        default=None,
        max_length=2000,
    )


class BatchApplicationRequest(BaseModel):
    top_n: int = Field(
        default=5,
        ge=1,
        le=20,
    )
    discovery_limit: int = Field(
        default=50,
        ge=1,
        le=100,
    )


class ConfiguredJobSearchRequest(BaseModel):
    role_terms: list[str] = Field(
        default_factory=list
    )
    location_terms: list[str] = Field(
        default_factory=list
    )
    discovery_limit: int = Field(
        default=50,
        ge=1,
        le=100,
    )
    shortlist_limit: int = Field(
        default=10,
        ge=1,
        le=50,
    )


class ApplicationLifecycleCreateRequest(BaseModel):
    application_url: str | None = None
    note: str | None = Field(
        default=None,
        max_length=2000,
    )


class ApplicationLifecycleTransitionRequest(BaseModel):
    to_status: ApplicationLifecycleStatus
    note: str | None = Field(
        default=None,
        max_length=2000,
    )


class JobDiscoveryRequest(BaseModel):
    board_tokens: list[str]
    role_terms: list[str] = Field(
        default_factory=list
    )
    location_terms: list[str] = Field(
        default_factory=list
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
    )


class JobIngestionRequest(BaseModel):
    url: HttpUrl
    source: JobSource = JobSource.MANUAL
    notes: str | None = None


def _serialize_lifecycle(
    record,
) -> dict:
    return {
        "lifecycle_id": str(
            record.lifecycle_id
        ),
        "job_id": str(
            record.job_id
        ),
        "current_status": str(
            record.current_status
        ),
        "application_url": (
            str(record.application_url)
            if record.application_url
            else None
        ),
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "submitted_at": record.submitted_at,
        "notes": list(
            record.notes
        ),
        "history": [
            {
                "event_id": str(
                    event.event_id
                ),
                "from_status": (
                    str(event.from_status)
                    if event.from_status
                    else None
                ),
                "to_status": str(
                    event.to_status
                ),
                "occurred_at": (
                    event.occurred_at
                ),
                "note": event.note,
            }
            for event in record.history
        ],
    }


app = FastAPI(
    title="Job Application Agent API",
    description=(
        "API layer for job ingestion, scoring, "
        "application generation, human review, "
        "and application lifecycle tracking."
    ),
    version="0.3.0",
)


db = PostgresJobDatabase()


@app.get("/health")
def health_check() -> dict[str, str]:
    """Confirm that the API service is running."""

    return {
        "status": "ok",
        "service": "job-application-agent",
        "database": "postgresql",
    }


@app.get(
    "/jobs",
    response_model=list[NormalisedJob],
)
def list_jobs(
    limit: int | None = Query(
        default=None,
        ge=1,
        le=500,
    ),
) -> list[NormalisedJob]:
    """Return jobs stored in PostgreSQL."""

    return db.list_jobs(
        limit=limit
    )


@app.get(
    "/jobs/{job_id}",
    response_model=NormalisedJob,
)
def get_job(
    job_id: str,
) -> NormalisedJob:
    """Return one stored job by ID."""

    job = db.get_job(
        job_id
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}",
        )

    return job


@app.post(
    "/jobs/{job_id}/score",
    response_model=JobMatchResult,
)
def score_job_endpoint(
    job_id: str,
) -> JobMatchResult:
    """Score one PostgreSQL job against the career profile."""

    job = db.get_job(
        job_id
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}",
        )

    profile = load_matching_profile()

    return score_job(
        job,
        profile,
    )


@app.post(
    "/jobs/{job_id}/application-pack",
)
def generate_application_pack_endpoint(
    job_id: str,
) -> dict:
    """Generate a human-review application pack for one PostgreSQL job."""

    job = db.get_job(
        job_id
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}",
        )

    pack, folder = generate_application_pack_for_job(
        job,
    )

    return {
        "job_id": str(
            job.job_id
        ),
        "company": job.company,
        "role_title": job.title,
        "status": str(
            pack.manifest.status
        ),
        "human_review_required": (
            pack.manifest.human_review_required
        ),
        "final_score": (
            pack.metadata.get(
                "final_score"
            )
        ),
        "recommendation": (
            pack.metadata.get(
                "recommendation"
            )
        ),
        "selected_evidence_ids": (
            pack.manifest.selected_evidence_ids
        ),
        "files": (
            pack.manifest.files
        ),
        "output_folder": str(
            folder
        ),
    }


@app.post(
    "/jobs/ingest",
    response_model=IngestionRun,
)
def ingest_job_endpoint(
    request: JobIngestionRequest,
) -> IngestionRun:
    """Fetch, parse, normalise and store one vacancy in PostgreSQL."""

    return ingest_job_url(
        url=str(
            request.url
        ),
        source=request.source,
        notes=request.notes,
        database=db,
    )


@app.post(
    "/jobs/discover",
)
def discover_jobs_endpoint(
    request: JobDiscoveryRequest,
) -> list[dict]:
    """Discover public Greenhouse vacancies."""

    jobs = discover_greenhouse_jobs(
        board_tokens=request.board_tokens,
        role_terms=request.role_terms,
        location_terms=request.location_terms,
        limit=request.limit,
    )

    return [
        {
            "source": job.source,
            "company_token": (
                job.company_token
            ),
            "source_job_id": (
                job.source_job_id
            ),
            "title": job.title,
            "location": job.location,
            "url": job.url,
            "updated_at": (
                job.updated_at
            ),
        }
        for job in jobs
    ]


@app.post(
    "/jobs/discover-and-ingest",
)
def discover_and_ingest_jobs_endpoint(
    request: JobDiscoveryRequest,
) -> list[dict]:
    """Discover matching Greenhouse vacancies and ingest them."""

    results = discover_and_ingest_greenhouse_jobs(
        board_tokens=request.board_tokens,
        role_terms=request.role_terms,
        location_terms=request.location_terms,
        limit=request.limit,
        database=db,
    )

    return [
        {
            "source": item.discovered.source,
            "company_token": (
                item.discovered.company_token
            ),
            "source_job_id": (
                item.discovered.source_job_id
            ),
            "title": (
                item.discovered.title
            ),
            "location": (
                item.discovered.location
            ),
            "url": (
                item.discovered.url
            ),
            "updated_at": (
                item.discovered.updated_at
            ),
            "action": (
                item.action
            ),
            "job_id": (
                item.job_id
            ),
            "duplicate_of": (
                item.duplicate_of
            ),
            "message": (
                item.message
            ),
        }
        for item in results
    ]


@app.post(
    "/jobs/discover-score-rank",
)
def discover_score_rank_jobs(
    request: JobDiscoveryRequest,
) -> list[dict]:
    """Discover, ingest, score, and rank matching vacancies."""

    ranked_jobs = (
        discover_ingest_score_greenhouse_jobs(
            board_tokens=request.board_tokens,
            role_terms=request.role_terms,
            location_terms=request.location_terms,
            limit=request.limit,
            shortlist_limit=request.limit,
            database=db,
        )
    )

    return [
        {
            "rank": (
                item.rank
            ),
            "job_id": (
                item.job_id
            ),
            "company": (
                item.company
            ),
            "title": (
                item.title
            ),
            "location": (
                item.location
            ),
            "url": (
                item.url
            ),
            "ingestion_action": (
                item.ingestion_action
            ),
            "final_score": (
                item.final_score
            ),
            "recommendation": (
                item.recommendation
            ),
            "score_details": (
                item.score_details
            ),
        }
        for item in ranked_jobs
    ]


@app.post(
    "/jobs/search-ranked",
)
def search_ranked_jobs(
    request: ConfiguredJobSearchRequest,
) -> list[dict]:
    """Search configured employers and return ranked opportunities."""

    ranked_jobs = search_configured_jobs(
        role_terms=request.role_terms,
        location_terms=request.location_terms,
        discovery_limit=(
            request.discovery_limit
        ),
        shortlist_limit=(
            request.shortlist_limit
        ),
        database=db,
    )

    return [
        {
            "rank": (
                item.rank
            ),
            "job_id": (
                item.job_id
            ),
            "company": (
                item.company
            ),
            "title": (
                item.title
            ),
            "location": (
                item.location
            ),
            "url": (
                item.url
            ),
            "ingestion_action": (
                item.ingestion_action
            ),
            "final_score": (
                item.final_score
            ),
            "recommendation": (
                item.recommendation
            ),
            "interview_fit_score": (
                item.interview_fit_score
            ),
            "must_have_coverage": (
                item.must_have_coverage
            ),
            "must_have_known": (
                item.must_have_known
            ),
            "score_details": (
                item.score_details
            ),
        }
        for item in ranked_jobs
    ]


@app.post(
    "/jobs/search-and-build-applications",
)
def search_and_build_applications(
    request: BatchApplicationRequest,
) -> dict:
    """
    Search configured job sources, select the strongest ranked jobs,
    and generate human-review application packs.
    """

    result = generate_top_application_packs(
        top_n=request.top_n,
        discovery_limit=(
            request.discovery_limit
        ),
        database=db,
    )

    return {
        "selected_count": (
            result.selected_count
        ),
        "generated_count": (
            result.generated_count
        ),
        "skipped_count": (
            result.skipped_count
        ),
        "applications": [
            {
                "rank": (
                    item.rank
                ),
                "job_id": (
                    item.job_id
                ),
                "company": (
                    item.company
                ),
                "title": (
                    item.title
                ),
                "ranking_score": (
                    item.ranking_score
                ),
                "recommendation": (
                    item.recommendation
                ),
                "ats_keyword_score": (
                    item.ats_keyword_score
                ),
                "interview_fit_score": (
                    item.interview_fit_score
                ),
                "must_have_coverage": (
                    item.must_have_coverage
                ),
                "must_have_known": (
                    item.must_have_known
                ),
                "claim_integrity": (
                    item.claim_integrity
                ),
                "claim_approval_readiness": (
                    item.claim_approval_readiness
                ),
                "critical_red_flags": (
                    item.critical_red_flags
                ),
                "opportunity_tier": (
                    item.opportunity_tier
                ),
                "eligible_for_priority_application": (
                    item.eligible_for_priority_application
                ),
                "quality_reasons": (
                    item.quality_reasons
                ),
                "pack_status": (
                    item.pack_status
                ),
                "human_review_required": (
                    item.human_review_required
                ),
                "output_folder": (
                    item.output_folder
                ),
                "selected_evidence_ids": (
                    item.selected_evidence_ids
                ),
            }
            for item in result.applications
        ],
    }


@app.post(
    "/jobs/{job_id}/application-review",
)
def review_application_endpoint(
    job_id: str,
    request: ApplicationReviewRequest,
) -> dict:
    """Record an explicit human decision for one generated application pack."""

    try:
        manifest, folder = (
            review_application_pack(
                job_id=job_id,
                decision=(
                    request.decision
                ),
                notes=(
                    request.notes
                ),
            )
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(
                exc
            ),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(
                exc
            ),
        ) from exc

    return {
        "job_id": str(
            manifest.job_id
        ),
        "company": (
            manifest.company
        ),
        "role_title": (
            manifest.role_title
        ),
        "status": str(
            manifest.status
        ),
        "human_review_required": (
            manifest.human_review_required
        ),
        "review_notes": (
            manifest.review_notes
        ),
        "reviewed_at": (
            manifest.reviewed_at
        ),
        "output_folder": str(
            folder
        ),
    }


@app.post(
    "/jobs/{job_id}/application-regenerate",
)
def regenerate_application_endpoint(
    job_id: str,
) -> dict:
    """Regenerate a pack after human-requested changes."""

    try:
        manifest, folder = (
            regenerate_application_pack(
                job_id=job_id,
                database=db,
            )
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(
                exc
            ),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(
                exc
            ),
        ) from exc

    return {
        "job_id": str(
            manifest.job_id
        ),
        "company": (
            manifest.company
        ),
        "role_title": (
            manifest.role_title
        ),
        "status": str(
            manifest.status
        ),
        "human_review_required": (
            manifest.human_review_required
        ),
        "review_notes": (
            manifest.review_notes
        ),
        "regeneration_count": (
            manifest.regeneration_count
        ),
        "last_regenerated_at": (
            manifest.last_regenerated_at
        ),
        "output_folder": str(
            folder
        ),
    }


@app.post(
    "/jobs/{job_id}/application-lifecycle",
)
def create_application_lifecycle_endpoint(
    job_id: str,
    request: ApplicationLifecycleCreateRequest,
) -> dict:
    """
    Create lifecycle tracking for an application.

    New lifecycle records begin at review_required.
    """

    job = db.get_job(
        job_id
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    record = (
        create_application_lifecycle(
            job_id=job_id,
            database=db,
            application_url=(
                request.application_url
                or str(
                    job.application_url
                )
            ),
            note=request.note,
        )
    )

    return _serialize_lifecycle(
        record
    )


@app.post(
    "/jobs/{job_id}/application-lifecycle/transition",
)
def transition_application_lifecycle_endpoint(
    job_id: str,
    request: ApplicationLifecycleTransitionRequest,
) -> dict:
    """
    Move an application through a validated lifecycle transition.
    """

    try:
        record = (
            transition_application_lifecycle(
                job_id=job_id,
                to_status=(
                    request.to_status
                ),
                database=db,
                note=(
                    request.note
                ),
            )
        )

    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(
                exc
            ),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(
                exc
            ),
        ) from exc

    return _serialize_lifecycle(
        record
    )


@app.get(
    "/jobs/{job_id}/application-lifecycle",
)
def get_application_lifecycle_endpoint(
    job_id: str,
) -> dict:
    """Return lifecycle state and history for one application."""

    record = (
        get_application_lifecycle(
            job_id=job_id,
            database=db,
        )
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Application lifecycle not found."
            ),
        )

    return _serialize_lifecycle(
        record
    )


@app.get(
    "/application-lifecycles",
)
def list_application_lifecycles_endpoint(
    status: ApplicationLifecycleStatus | None = None,
) -> list[dict]:
    """
    List tracked applications, optionally filtered by lifecycle status.
    """

    records = (
        list_application_lifecycles(
            status=status,
            database=db,
        )
    )

    return [
        _serialize_lifecycle(
            record
        )
        for record in records
    ]
