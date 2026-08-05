from src.application_models import ApplicationPackStatus
from src.application_pack_builder import build_application_pack
from tests.phase5_helpers import make_match, make_profile


def test_builds_complete_application_pack():
    pack = build_application_pack(
        make_profile(),
        make_match(),
    )

    assert pack.cv.markdown
    assert pack.cover_letter.markdown
    assert len(pack.application_answers) == 5
    assert pack.interview_evidence_markdown
    assert pack.manifest.human_review_required is True


def test_pack_contains_selected_evidence_ids():
    pack = build_application_pack(
        make_profile(),
        make_match(),
    )
    assert pack.manifest.selected_evidence_ids


def test_pack_status_is_not_approved_automatically():
    pack = build_application_pack(
        make_profile(),
        make_match(),
    )
    assert pack.manifest.status != ApplicationPackStatus.APPROVED
