"""Generate common job-application answers from validated profile data."""

from __future__ import annotations

from src.application_models import (
    ApplicationQuestion,
    GeneratedApplicationAnswer,
    SelectedEvidence,
)
from src.matching_models import CareerMatchingProfile, JobMatchResult


def _word_count(text: str) -> int:
    return len(text.split())


def _trim_words(text: str, maximum_words: int | None) -> str:
    if maximum_words is None:
        return text
    words = text.split()
    return " ".join(words[:maximum_words])


def generate_application_answer(
    question: ApplicationQuestion,
    profile: CareerMatchingProfile,
    match: JobMatchResult,
    evidence: list[SelectedEvidence],
) -> GeneratedApplicationAnswer:
    lowered = question.question.casefold()
    chosen = [
        item
        for item in evidence
        if str(item.decision) in {"selected", "review_required"}
    ][:3]

    evidence_text = " ".join(
        item.description.rstrip(".") + "."
        for item in chosen
    )

    requires_review = question.sensitive
    warnings: list[str] = []

    if "why" in lowered and "company" in lowered:
        answer = (
            f"I am interested in {match.company} because the "
            f"{match.job_title} role aligns with my experience and the type of "
            f"technical, evidence-led work I want to continue developing."
        )
    elif "why" in lowered and "role" in lowered:
        answer = (
            f"The {match.job_title} role is relevant to my background in "
            f"data, artificial intelligence, automation, and analytical "
            f"problem-solving. {evidence_text}"
        )
    elif "relevant experience" in lowered or "describe your experience" in lowered:
        answer = (
            evidence_text
            or "My relevant experience is documented in the attached CV."
        )
    elif "salary" in lowered:
        answer = (
            f"My minimum salary expectation is £{profile.minimum_salary:,}."
            if profile.minimum_salary is not None
            else "I am open to discussing salary based on the complete package."
        )
        requires_review = True
    elif "sponsor" in lowered or "visa" in lowered:
        answer = (
            "I currently have the right to work in the UK and will require "
            "sponsorship in the future."
            if profile.right_to_work_uk and profile.future_sponsorship_required
            else "My work-authorisation position requires manual confirmation."
        )
        requires_review = True
    elif "start" in lowered or "available" in lowered:
        answer = (
            f"My earliest available start date is {profile.earliest_start_date}."
            if profile.earliest_start_date
            else "My start date is open to discussion."
        )
    elif "relocat" in lowered:
        answer = (
            "Yes, I am willing to relocate for the right opportunity."
            if profile.willing_to_relocate
            else "My relocation preference requires manual confirmation."
        )
    else:
        answer = (
            f"My background is relevant to the {match.job_title} role. "
            f"{evidence_text}"
        )

    answer = _trim_words(answer.strip(), question.maximum_words)

    if any(str(item.decision) == "review_required" for item in chosen):
        warnings.append("One or more supporting evidence items need review.")
        requires_review = True

    return GeneratedApplicationAnswer(
        question_id=question.question_id,
        question=question.question,
        answer=answer,
        word_count=_word_count(answer),
        source_evidence_ids=[item.evidence_id for item in chosen],
        requires_review=requires_review,
        warnings=warnings,
    )


def generate_standard_answers(
    profile: CareerMatchingProfile,
    match: JobMatchResult,
    evidence: list[SelectedEvidence],
) -> list[GeneratedApplicationAnswer]:
    questions = [
        ApplicationQuestion(
            question_id="why_role",
            question="Why are you interested in this role?",
            maximum_words=200,
        ),
        ApplicationQuestion(
            question_id="relevant_experience",
            question="Describe your relevant experience.",
            maximum_words=250,
        ),
        ApplicationQuestion(
            question_id="salary",
            question="What are your salary expectations?",
            maximum_words=80,
            sensitive=True,
        ),
        ApplicationQuestion(
            question_id="sponsorship",
            question="Do you require visa sponsorship?",
            maximum_words=80,
            sensitive=True,
        ),
        ApplicationQuestion(
            question_id="start_date",
            question="When can you start?",
            maximum_words=60,
        ),
    ]

    return [
        generate_application_answer(
            question,
            profile,
            match,
            evidence,
        )
        for question in questions
    ]
