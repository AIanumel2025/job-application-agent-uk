"""Run ranked job discovery across configured job sources."""

from __future__ import annotations
from src.job_search_preferences import load_job_search_preferences
from src.job_discovery_service import (
    discover_ashby_jobs,
    discover_lever_jobs,
    discover_smartrecruiters_jobs,
    discover_workable_jobs,
)
from src.live_opportunity_scores import (
    calculate_pre_application_scores,
)
from src.job_discovery_scoring_service import (
    RankedDiscoveredJob,
    discover_ingest_score_greenhouse_jobs,
)
from src.job_ingestion_service import (
    ingest_job_url,
)
from src.job_models import (
    JobSource,
)
from src.job_scoring_service import (
    load_matching_profile,
    score_job,
)
from src.job_source_registry import (
    load_ashby_board_tokens,
    load_greenhouse_board_tokens,
    load_lever_site_tokens,
    load_smartrecruiters_company_identifiers,
    load_workable_site_urls,
)
from src.postgres_job_database import (
    PostgresJobDatabase,
)


def _score_stored_job(
    *,
    job_id: str,
    database: PostgresJobDatabase,
    profile,
    ingestion_action: str,
) -> RankedDiscoveredJob | None:
    """Load one stored job, score it, and convert it to ranked output."""

    job = database.get_job(job_id)

    if job is None:
        return None

    match = score_job(
        job,
        profile,
    )

    pre_scores = calculate_pre_application_scores(
        match
    )

    score_details = (
        match.model_dump(mode="json")
        if hasattr(match, "model_dump")
        else {}
    )

    recommendation_value = getattr(
        match,
        "recommendation",
        "",
    )

    recommendation = (
        recommendation_value.value
        if hasattr(recommendation_value, "value")
        else str(recommendation_value)
    )

    location_value = None

    if job.location:
        location_parts = [
            str(part).strip()
            for part in (
                getattr(job.location, "city", None),
                getattr(job.location, "region", None),
                getattr(job.location, "country", None),
            )
            if part
        ]

        if location_parts:
            location_value = ", ".join(location_parts)

    return RankedDiscoveredJob(
        rank=0,
        job_id=str(job.job_id),
        company=job.company,
        title=job.title,
        location=location_value,
        url=str(job.application_url),
        ingestion_action=ingestion_action,
        final_score=float(
            getattr(match, "final_score", 0.0)
            or 0.0
        ),
        recommendation=recommendation,
        score_details=score_details,
        interview_fit_score=(
            pre_scores.interview_fit_score
        ),
        must_have_coverage=(
            pre_scores.must_have_coverage
        ),
        must_have_known=(
            pre_scores.must_have_known
        ),
        )

def search_configured_jobs(
    *,
    role_terms: list[str] | None = None,
    location_terms: list[str] | None = None,
    discovery_limit: int = 50,
    shortlist_limit: int = 10,
    database: PostgresJobDatabase | None = None,
) -> list[RankedDiscoveredJob]:
    """Search configured ATS sources and return ranked opportunities."""

    db = database or PostgresJobDatabase()
    db.initialise()

    profile = load_matching_profile()

    ranked_jobs: list[RankedDiscoveredJob] = []

    preferences = load_job_search_preferences()

    effective_role_terms = (
        role_terms
        if role_terms
        else preferences.role_terms
    )

    effective_location_terms = (
        location_terms
        if location_terms
        else preferences.location_terms
    )

    # ------------------------------------------------------------
    # Greenhouse
    # ------------------------------------------------------------

    greenhouse_tokens = load_greenhouse_board_tokens()

    if greenhouse_tokens:
        greenhouse_results = discover_ingest_score_greenhouse_jobs(
            board_tokens=greenhouse_tokens,
            role_terms=effective_role_terms,
            location_terms=effective_location_terms,
            limit=discovery_limit,
            shortlist_limit=discovery_limit,
            database=db,
        )

        ranked_jobs.extend(greenhouse_results)

    # ------------------------------------------------------------
    # Lever
    # ------------------------------------------------------------

    lever_sites = load_lever_site_tokens()

    if lever_sites:
        lever_jobs = discover_lever_jobs(
            sites=lever_sites,
            role_terms=effective_role_terms,
            location_terms=effective_location_terms,
            limit=discovery_limit,
        )

        for discovered in lever_jobs:
            run = ingest_job_url(
                url=discovered.url,
                source=JobSource.COMPANY_SITE,
                notes=(
                    "Automatically discovered from "
                    f"Lever site: {discovered.company_token}"
                ),
                company_hint=(
                    discovered.company_token
                    .replace("_", " ")
                    .replace("-", " ")
                    .title()
                ),
                source_job_id_hint=discovered.source_job_id,
                database=db,
            )

            if not run.results:
                continue

            ingestion_result = run.results[0]

            action_value = ingestion_result.action

            action = (
                action_value.value
                if hasattr(action_value, "value")
                else str(action_value)
            )

            stored_job_id = None

            if action == "inserted":
                stored_job_id = ingestion_result.job_id

            elif action == "duplicate":
                stored_job_id = (
                    ingestion_result.duplicate_of
                    or ingestion_result.job_id
                )

            if not stored_job_id:
                continue

            ranked = _score_stored_job(
                job_id=str(stored_job_id),
                database=db,
                profile=profile,
                ingestion_action=action,
            )

            if ranked is not None:
                ranked_jobs.append(ranked)

                
    # ------------------------------------------------------------
    # Ashby
    # ------------------------------------------------------------

    ashby_boards = load_ashby_board_tokens()

    if ashby_boards:
        ashby_jobs = discover_ashby_jobs(
            board_names=ashby_boards,
            role_terms=effective_role_terms,
            location_terms=effective_location_terms,
            limit=discovery_limit,
        )

        for discovered in ashby_jobs:
            run = ingest_job_url(
                url=discovered.url,
                source=JobSource.COMPANY_SITE,
                notes=(
                    "Automatically discovered from "
                    f"Ashby board: {discovered.company_token}"
                ),
                company_hint=(
                    discovered.company_token
                    .replace("_", " ")
                    .replace("-", " ")
                    .title()
                ),
                source_job_id_hint=discovered.source_job_id,
                database=db,
            )

            if not run.results:
                continue

            ingestion_result = run.results[0]

            action_value = ingestion_result.action

            action = (
                action_value.value
                if hasattr(action_value, "value")
                else str(action_value)
            )

            stored_job_id = None

            if action == "inserted":
                stored_job_id = ingestion_result.job_id

            elif action == "duplicate":
                stored_job_id = (
                    ingestion_result.duplicate_of
                    or ingestion_result.job_id
                )

            if not stored_job_id:
                continue

            ranked = _score_stored_job(
                job_id=str(stored_job_id),
                database=db,
                profile=profile,
                ingestion_action=action,
            )

            if ranked is not None:
                ranked_jobs.append(ranked)
    # ------------------------------------------------------------
    # Workable
    # ------------------------------------------------------------

    workable_sites = load_workable_site_urls()

    if workable_sites:
        workable_jobs = discover_workable_jobs(
            site_urls=workable_sites,
            role_terms=effective_role_terms,
            location_terms=effective_location_terms,
            limit=discovery_limit,
        )

        for discovered in workable_jobs:
            run = ingest_job_url(
                url=discovered.url,
                source=JobSource.COMPANY_SITE,
                notes=(
                    "Automatically discovered from "
                    f"Workable site: {discovered.company_token}"
                ),
                company_hint=None,
                source_job_id_hint=discovered.source_job_id,
                database=db,
            )

            if not run.results:
                continue

            ingestion_result = run.results[0]

            action_value = ingestion_result.action

            action = (
                action_value.value
                if hasattr(action_value, "value")
                else str(action_value)
            )

            stored_job_id = None

            if action == "inserted":
                stored_job_id = ingestion_result.job_id

            elif action == "duplicate":
                stored_job_id = (
                    ingestion_result.duplicate_of
                    or ingestion_result.job_id
                )

            if not stored_job_id:
                continue

            ranked = _score_stored_job(
                job_id=str(stored_job_id),
                database=db,
                profile=profile,
                ingestion_action=action,
            )

            if ranked is not None:
                ranked_jobs.append(ranked)
    # ------------------------------------------------------------
    # SmartRecruiters
    # ------------------------------------------------------------

    smartrecruiters_companies = (
        load_smartrecruiters_company_identifiers()
    )

    if smartrecruiters_companies:
        smartrecruiters_jobs = discover_smartrecruiters_jobs(
            company_identifiers=smartrecruiters_companies,
            role_terms=effective_role_terms,
            location_terms=effective_location_terms,
            limit=discovery_limit,
        )

        for discovered in smartrecruiters_jobs:
            run = ingest_job_url(
                url=discovered.url,
                source=JobSource.COMPANY_SITE,
                notes=(
                    "Automatically discovered from "
                    "SmartRecruiters company: "
                    f"{discovered.company_token}"
                ),
                company_hint=(
                    discovered.company_token
                    .replace("_", " ")
                    .replace("-", " ")
                    .title()
                ),
                source_job_id_hint=discovered.source_job_id,
                database=db,
            )

            if not run.results:
                continue

            ingestion_result = run.results[0]

            action_value = ingestion_result.action

            action = (
                action_value.value
                if hasattr(action_value, "value")
                else str(action_value)
            )

            stored_job_id = None

            if action == "inserted":
                stored_job_id = ingestion_result.job_id

            elif action == "duplicate":
                stored_job_id = (
                    ingestion_result.duplicate_of
                    or ingestion_result.job_id
                )

            if not stored_job_id:
                continue

            ranked = _score_stored_job(
                job_id=str(stored_job_id),
                database=db,
                profile=profile,
                ingestion_action=action,
            )

            if ranked is not None:
                ranked_jobs.append(ranked)

    # ------------------------------------------------------------
    # Enrich every discovered job with live pre-application scores.
    # This also covers Greenhouse results that were scored through
    # their own discovery service.
    # ------------------------------------------------------------

    for ranked in ranked_jobs:
        stored_job = db.get_job(
            str(ranked.job_id)
        )

        if stored_job is None:
            continue

        match = score_job(
            stored_job,
            profile,
        )

        pre_scores = calculate_pre_application_scores(
            match
        )

        ranked.interview_fit_score = (
            pre_scores.interview_fit_score
        )

        ranked.must_have_coverage = (
            pre_scores.must_have_coverage
        )

        ranked.must_have_known = (
            pre_scores.must_have_known
        )

    # ------------------------------------------------------------
    # Final cross-source ranking
    # ------------------------------------------------------------

    ranked_jobs.sort(
        key=lambda item: item.final_score,
        reverse=True,
    )

    shortlisted = ranked_jobs[:shortlist_limit]

    for index, item in enumerate(
        shortlisted,
        start=1,
    ):
        item.rank = index

    return shortlisted
   
