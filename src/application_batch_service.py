"""Batch application-pack generation for top-ranked opportunities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.application_pack_service import (
    generate_application_pack_for_job,
)
from src.application_quality_gate import (
    classify_application_quality,
)
from src.configured_job_search_service import (
    search_configured_jobs,
)
from src.job_scoring_service import (
    load_matching_profile,
    score_job,
)
from src.live_opportunity_scores import (
    calculate_final_application_scores,
)
from src.postgres_job_database import (
    PostgresJobDatabase,
)


@dataclass(slots=True)
class BatchApplicationResult:
    rank: int
    job_id: str
    company: str
    title: str

    # Existing ranking output.
    ranking_score: float
    recommendation: str

    # Final live application scores.
    ats_keyword_score: float
    interview_fit_score: float
    must_have_coverage: float
    must_have_known: bool
    claim_integrity: float
    claim_approval_readiness: float
    critical_red_flags: int

    # Application quality gate.
    opportunity_tier: str
    eligible_for_priority_application: bool
    quality_reasons: list[str]

    # Application pack state.
    pack_status: str
    human_review_required: bool
    output_folder: str
    selected_evidence_ids: list[str]


@dataclass(slots=True)
class BatchApplicationRun:
    selected_count: int
    generated_count: int
    skipped_count: int
    applications: list[BatchApplicationResult]


def generate_top_application_packs(
    *,
    top_n: int = 5,
    discovery_limit: int = 50,
    database: PostgresJobDatabase | None = None,
    repository_root: str | Path | None = None,
    output_root: str | Path | None = None,
) -> BatchApplicationRun:
    """
    Search configured sources, select the strongest ranked jobs,
    generate human-review application packs, calculate final
    application scores, and apply the application quality gate.

    No application is submitted automatically.
    """

    if top_n < 1:
        raise ValueError(
            "top_n must be at least 1"
        )

    db = database or PostgresJobDatabase()
    db.initialise()

    profile = load_matching_profile()

    ranked_jobs = search_configured_jobs(
        discovery_limit=discovery_limit,
        shortlist_limit=top_n,
        database=db,
    )

    applications: list[BatchApplicationResult] = []
    skipped_count = 0

    for ranked in ranked_jobs[:top_n]:
        stored_job = db.get_job(
            str(ranked.job_id)
        )

        if stored_job is None:
            skipped_count += 1
            continue

        # -----------------------------------------------------
        # 1. Score the stored vacancy against the career profile.
        # -----------------------------------------------------

        match = score_job(
            stored_job,
            profile,
        )

        # -----------------------------------------------------
        # 2. Generate the actual application pack.
        # -----------------------------------------------------

        pack, folder = generate_application_pack_for_job(
            stored_job,
            repository_root=repository_root,
            output_root=output_root,
        )

        # -----------------------------------------------------
        # 3. Calculate the live four-score evaluation.
        # -----------------------------------------------------

        scores = calculate_final_application_scores(
            match=match,
            pack=pack,
        )

        # -----------------------------------------------------
        # 4. Apply the quality / opportunity gate.
        # -----------------------------------------------------

        quality_decision = classify_application_quality(
            scores
        )

        # -----------------------------------------------------
        # 5. Return the complete application result.
        # -----------------------------------------------------

        applications.append(
            BatchApplicationResult(
                rank=ranked.rank,
                job_id=str(ranked.job_id),
                company=ranked.company,
                title=ranked.title,

                ranking_score=ranked.final_score,
                recommendation=str(
                    ranked.recommendation
                ),

                ats_keyword_score=(
                    scores.ats_keyword_score
                ),
                interview_fit_score=(
                    scores.interview_fit_score
                ),
                must_have_coverage=(
                    scores.must_have_coverage
                ),
                must_have_known=(
                    scores.must_have_known
                ),
                claim_integrity=(
                    scores.claim_integrity
                ),
                claim_approval_readiness=(
                    scores.claim_approval_readiness
                ),
                critical_red_flags=(
                    scores.critical_red_flags
                ),

                opportunity_tier=str(
                    quality_decision.tier
                ),
                eligible_for_priority_application=(
                    quality_decision
                    .eligible_for_priority_application
                ),
                quality_reasons=list(
                    quality_decision.reasons
                ),

                pack_status=str(
                    pack.manifest.status
                ),
                human_review_required=(
                    pack.manifest.human_review_required
                ),
                output_folder=str(folder),
                selected_evidence_ids=list(
                    pack.manifest.selected_evidence_ids
                ),
            )
        )

    return BatchApplicationRun(
        selected_count=min(
            top_n,
            len(ranked_jobs),
        ),
        generated_count=len(
            applications
        ),
        skipped_count=skipped_count,
        applications=applications,
    )
