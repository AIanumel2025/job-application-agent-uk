from src.eligibility_checker import check_eligibility
from src.job_models import SponsorshipStatus
from src.matching_models import EligibilityStatus, HardStopType
from tests.phase4_helpers import make_job, make_profile, make_requirements


def test_confirmed_sponsorship_passes():
    job = make_job()
    result = check_eligibility(
        job,
        make_requirements(job.job_id),
        make_profile(),
    )
    sponsorship = next(
        item for item in result.checks
        if item.check_id == "sponsorship"
    )
    assert sponsorship.status == EligibilityStatus.PASSED


def test_no_sponsorship_triggers_hard_stop():
    job = make_job(
        sponsorship_status=SponsorshipStatus.EXPLICITLY_UNAVAILABLE,
        sponsorship_evidence=["No visa sponsorship is available."],
    )
    result = check_eligibility(
        job,
        make_requirements(job.job_id),
        make_profile(),
    )
    assert result.hard_stop_triggered is True
    assert result.overall_status == EligibilityStatus.FAILED
    assert result.hard_stops[0].hard_stop_type == HardStopType.NO_SPONSORSHIP


def test_missing_right_to_work_needs_review():
    job = make_job()
    result = check_eligibility(
        job,
        make_requirements(job.job_id),
        make_profile(right_to_work_uk=None),
    )
    right_to_work = next(
        item for item in result.checks
        if item.check_id == "right_to_work"
    )
    assert right_to_work.status == EligibilityStatus.REVIEW_REQUIRED
