from src.application_answer_generator import (
    generate_application_answer,
    generate_standard_answers,
)
from src.application_models import ApplicationQuestion
from tests.phase5_helpers import (
    make_match,
    make_profile,
    make_selected_evidence,
)


def test_salary_answer_requires_review():
    question = ApplicationQuestion(
        question_id="salary",
        question="What are your salary expectations?",
        sensitive=True,
    )
    answer = generate_application_answer(
        question,
        make_profile(),
        make_match(),
        make_selected_evidence(),
    )
    assert "£50,000" in answer.answer
    assert answer.requires_review is True


def test_sponsorship_answer_is_factual():
    question = ApplicationQuestion(
        question_id="sponsor",
        question="Do you require visa sponsorship?",
        sensitive=True,
    )
    answer = generate_application_answer(
        question,
        make_profile(),
        make_match(),
        make_selected_evidence(),
    )
    assert "right to work in the UK" in answer.answer
    assert "future" in answer.answer


def test_standard_answers_generate_five_items():
    answers = generate_standard_answers(
        make_profile(),
        make_match(),
        make_selected_evidence(),
    )
    assert len(answers) == 5
