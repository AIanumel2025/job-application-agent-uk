from src.cover_letter_generator import generate_cover_letter
from tests.phase5_helpers import (
    make_match,
    make_profile,
    make_selected_evidence,
)


def test_cover_letter_mentions_company_and_role():
    letter = generate_cover_letter(
        make_profile(),
        make_match(),
        make_selected_evidence(),
    )
    assert "Example AI Ltd" in letter.markdown
    assert "Data Engineer" in letter.markdown


def test_cover_letter_has_four_paragraphs():
    letter = generate_cover_letter(
        make_profile(),
        make_match(),
        make_selected_evidence(),
    )
    assert len(letter.paragraphs) == 4


def test_cover_letter_tracks_evidence_ids():
    letter = generate_cover_letter(
        make_profile(),
        make_match(),
        make_selected_evidence(),
    )
    assert "project_1" in letter.source_evidence_ids
