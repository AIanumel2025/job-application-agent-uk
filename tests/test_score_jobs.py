from src.score_jobs import _evidence_quality_score, build_parser
from tests.phase4_helpers import make_profile


def test_evidence_quality_score_is_bounded():
    score = _evidence_quality_score(make_profile())
    assert 0 <= score <= 100


def test_empty_evidence_scores_zero():
    assert _evidence_quality_score(make_profile(evidence=[])) == 0


def test_cli_parser_accepts_custom_paths():
    parser = build_parser()
    args = parser.parse_args(
        [
            "--root", "/tmp/project",
            "--db", "/tmp/jobs.db",
            "--json-report", "/tmp/report.json",
            "--csv-report", "/tmp/report.csv",
            "--quiet",
        ]
    )
    assert args.repository_root == "/tmp/project"
    assert args.quiet is True
