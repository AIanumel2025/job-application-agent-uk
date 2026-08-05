"""Rank scored vacancies by fit, eligibility, urgency, and value."""

from __future__ import annotations

from datetime import date, datetime

from src.matching_models import (
    EligibilityStatus,
    JobMatchResult,
    JobRankingReport,
    RankedJob,
)


def urgency_score_for(closing_date: str | None) -> float:
    if not closing_date:
        return 40.0

    try:
        parsed = datetime.fromisoformat(
            closing_date.replace("Z", "+00:00")
        ).date()
    except ValueError:
        try:
            parsed = date.fromisoformat(closing_date)
        except ValueError:
            return 40.0

    days_remaining = (parsed - date.today()).days

    if days_remaining < 0:
        return 0.0
    if days_remaining <= 2:
        return 100.0
    if days_remaining <= 7:
        return 90.0
    if days_remaining <= 14:
        return 75.0
    if days_remaining <= 30:
        return 55.0
    return 35.0


def strategic_value_for(result: JobMatchResult) -> float:
    recommendation = str(result.recommendation)

    values = {
        "strong_match": 100.0,
        "good_match": 85.0,
        "possible_match": 65.0,
        "manual_review": 50.0,
        "weak_match": 35.0,
        "do_not_apply": 10.0,
        "not_eligible": 0.0,
    }
    return values.get(recommendation, 40.0)


def rank_jobs(
    results: list[JobMatchResult],
    closing_dates: dict[str, str | None] | None = None,
) -> JobRankingReport:
    closing_dates = closing_dates or {}
    ranked: list[RankedJob] = []

    for result in results:
        closing_date = closing_dates.get(str(result.job_id))
        urgency = urgency_score_for(closing_date)
        strategic = strategic_value_for(result)

        eligibility_penalty = (
            0.0
            if result.eligibility_result.hard_stop_triggered
            else 1.0
        )

        ranking_score = round(
            (
                result.final_score * 0.70
                + urgency * 0.15
                + strategic * 0.15
            )
            * eligibility_penalty,
            2,
        )

        ranked.append(
            RankedJob(
                rank=1,
                job_id=result.job_id,
                match_id=result.match_id,
                job_title=result.job_title,
                company=result.company,
                final_score=result.final_score,
                recommendation=result.recommendation,
                eligibility_status=result.eligibility_result.overall_status,
                closing_date=closing_date,
                urgency_score=urgency,
                strategic_value_score=strategic,
                ranking_score=ranking_score,
            )
        )

    ranked.sort(
        key=lambda item: (
            item.ranking_score,
            item.final_score,
        ),
        reverse=True,
    )

    for index, item in enumerate(ranked, start=1):
        item.rank = index

    blocked = sum(
        item.eligibility_status == EligibilityStatus.FAILED
        for item in ranked
    )

    return JobRankingReport(
        total_jobs=len(ranked),
        eligible_jobs=len(ranked) - blocked,
        blocked_jobs=blocked,
        ranked_jobs=ranked,
        metadata={
            "ranking_formula": (
                "70% match score + 15% urgency + 15% strategic value; "
                "hard-stop jobs receive a zero ranking score"
            )
        },
    )
