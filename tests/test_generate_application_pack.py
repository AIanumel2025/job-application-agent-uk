from src.generate_application_pack import _find_match, _slug, build_parser
from tests.phase5_helpers import make_match


def test_slug_is_filesystem_safe():
    assert _slug("Example AI Ltd / Data Engineer") == (
        "example_ai_ltd_data_engineer"
    )


def test_find_match_returns_requested_job():
    match = make_match()
    result = _find_match(match.job_id, [match])
    assert result.job_id == match.job_id


def test_cli_requires_job_id():
    parser = build_parser()
    args = parser.parse_args(["--job-id", "abc"])
    assert args.job_id == "abc"
