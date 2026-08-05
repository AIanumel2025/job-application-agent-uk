"""Normalise parsed UK job vacancies into canonical records."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable

from src.job_models import (
    CurrencyCode,
    EmploymentType,
    JobLocation,
    NormalisedJob,
    ParsedJobRecord,
    SalaryRange,
    SponsorshipStatus,
    WorkModel,
    canonicalise_url,
)


_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9+.#/& -]+", re.I)
_POSTCODE_RE = re.compile(
    r"\b(?:GIR 0AA|[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2})\b",
    re.I,
)
_NUMBER_RE = re.compile(r"(?P<number>\d+(?:[.,]\d+)?)\s*(?P<suffix>[kKmM]?)")


@dataclass(slots=True)
class SponsorshipClassification:
    status: SponsorshipStatus
    evidence: list[str]


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return _WHITESPACE_RE.sub(" ", value).strip()


def normalise_name(value: str) -> str:
    """Create a stable lowercase representation of a company or title."""

    cleaned = clean_text(value).lower()
    cleaned = cleaned.replace("–", "-").replace("—", "-")
    cleaned = _NON_ALNUM_RE.sub(" ", cleaned)
    return _WHITESPACE_RE.sub(" ", cleaned).strip()


def normalise_company_name(value: str) -> str:
    """Normalise common company suffixes without losing the source value."""

    company = normalise_name(value)

    suffix_patterns = (
        r"\blimited\b",
        r"\bltd\b",
        r"\bplc\b",
        r"\bllp\b",
        r"\bincorporated\b",
        r"\binc\b",
        r"\bcorp(?:oration)?\b",
    )

    for pattern in suffix_patterns:
        company = re.sub(pattern, "", company)

    return _WHITESPACE_RE.sub(" ", company).strip(" ,.-")


def normalise_job_title(value: str) -> str:
    """Normalise a title while preserving important role terms."""

    title = normalise_name(value)

    replacements = {
        r"\bsr\b\.?": "senior",
        r"\bjr\b\.?": "junior",
        r"\bml\b": "machine learning",
        r"\bai\b": "artificial intelligence",
        r"\bdata scientist ii\b": "data scientist 2",
        r"\bdata scientist iii\b": "data scientist 3",
    }

    for pattern, replacement in replacements.items():
        title = re.sub(pattern, replacement, title)

    return _WHITESPACE_RE.sub(" ", title).strip()


def _parse_numeric_token(value: str) -> int | None:
    match = _NUMBER_RE.search(value.replace(",", ""))
    if not match:
        return None

    raw_number = match.group("number").replace(",", "")
    suffix = match.group("suffix").lower()

    try:
        number = Decimal(raw_number)
    except InvalidOperation:
        return None

    multiplier = Decimal(1)
    if suffix == "k":
        multiplier = Decimal(1_000)
    elif suffix == "m":
        multiplier = Decimal(1_000_000)

    return int(number * multiplier)


def _extract_salary_numbers(text: str) -> list[int]:
    values: list[int] = []

    for match in _NUMBER_RE.finditer(text.replace(",", "")):
        parsed = _parse_numeric_token(match.group(0))
        if parsed is not None:
            values.append(parsed)

    return values


def _detect_currency(text: str) -> CurrencyCode:
    lowered = text.lower()

    if "£" in text or "gbp" in lowered or "pound" in lowered:
        return CurrencyCode.GBP
    if "$" in text or "usd" in lowered or "dollar" in lowered:
        return CurrencyCode.USD
    if "€" in text or "eur" in lowered or "euro" in lowered:
        return CurrencyCode.EUR

    return CurrencyCode.UNKNOWN


def _detect_salary_period(text: str) -> str:
    lowered = text.lower()

    if any(token in lowered for token in ("per hour", "hourly", "/hour", "p/h", "ph")):
        return "hourly"
    if any(token in lowered for token in ("per day", "daily", "/day", "pd")):
        return "daily"
    if any(token in lowered for token in ("per week", "weekly", "/week", "pw")):
        return "weekly"
    if any(token in lowered for token in ("per month", "monthly", "/month", "pcm")):
        return "monthly"

    return "annual"


def _annualise(value: int, period: str) -> int:
    if period == "hourly":
        return int(value * 37.5 * 52)
    if period == "daily":
        return int(value * 5 * 52)
    if period == "weekly":
        return int(value * 52)
    if period == "monthly":
        return int(value * 12)
    return value


def normalise_salary(text: str | None) -> SalaryRange | None:
    """Parse common salary strings and annualise periodic rates."""

    raw = clean_text(text)
    if not raw:
        return None

    lowered = raw.lower()
    if any(
        phrase in lowered
        for phrase in (
            "competitive",
            "depending on experience",
            "doe",
            "not disclosed",
            "salary unavailable",
        )
    ) and not _extract_salary_numbers(raw):
        return SalaryRange(
            currency=_detect_currency(raw),
            raw_text=raw,
            is_estimated=False,
        )

    numbers = _extract_salary_numbers(raw)
    if not numbers:
        return SalaryRange(
            currency=_detect_currency(raw),
            raw_text=raw,
            is_estimated=False,
        )

    period = _detect_salary_period(raw)
    annualised = [_annualise(value, period) for value in numbers[:2]]

    minimum = annualised[0]
    maximum = annualised[1] if len(annualised) > 1 else None

    if maximum is not None and maximum < minimum:
        minimum, maximum = maximum, minimum

    return SalaryRange(
        minimum=minimum,
        maximum=maximum,
        currency=_detect_currency(raw),
        period="annual",
        raw_text=raw,
        is_estimated=period != "annual",
    )


def normalise_employment_types(text: str | None) -> list[EmploymentType]:
    lowered = clean_text(text).lower()
    if not lowered:
        return [EmploymentType.UNKNOWN]

    patterns = (
        (EmploymentType.PERMANENT, ("permanent", "perm role")),
        (EmploymentType.CONTRACT, ("contract", "contractor")),
        (EmploymentType.FIXED_TERM, ("fixed term", "fixed-term", "ftc")),
        (EmploymentType.TEMPORARY, ("temporary", "temp role")),
        (EmploymentType.INTERNSHIP, ("internship", "intern")),
        (EmploymentType.PLACEMENT, ("placement", "industrial year")),
        (EmploymentType.GRADUATE, ("graduate scheme", "graduate role")),
        (EmploymentType.APPRENTICESHIP, ("apprenticeship", "apprentice")),
        (EmploymentType.PART_TIME, ("part time", "part-time")),
        (EmploymentType.FULL_TIME, ("full time", "full-time")),
    )

    values: list[EmploymentType] = []
    for employment_type, phrases in patterns:
        if any(phrase in lowered for phrase in phrases):
            values.append(employment_type)

    return values or [EmploymentType.UNKNOWN]


def normalise_work_model(
    work_model_text: str | None,
    location_text: str | None = None,
) -> WorkModel:
    combined = f"{clean_text(work_model_text)} {clean_text(location_text)}".lower()

    if any(
        phrase in combined
        for phrase in ("fully remote", "100% remote", "remote only", "home based")
    ):
        return WorkModel.REMOTE

    if "hybrid" in combined:
        return WorkModel.HYBRID

    if any(
        phrase in combined
        for phrase in ("on-site", "onsite", "office based", "office-based")
    ):
        return WorkModel.ONSITE

    if any(
        phrase in combined
        for phrase in ("flexible working", "flexible location", "remote options")
    ):
        return WorkModel.FLEXIBLE

    if "remote" in combined:
        return WorkModel.REMOTE

    return WorkModel.UNKNOWN


def normalise_location(
    location_text: str | None,
    work_model_text: str | None = None,
) -> JobLocation:
    raw = clean_text(location_text)
    postcode_match = _POSTCODE_RE.search(raw)

    postcode = postcode_match.group(0).upper() if postcode_match else None
    work_model = normalise_work_model(work_model_text, raw)

    parts = [part.strip() for part in raw.split(",") if part.strip()]
    city = parts[0] if parts else None
    region = parts[1] if len(parts) > 1 else None
    country = "United Kingdom"

    lowered = raw.lower()
    if any(term in lowered for term in ("united states", "usa", "u.s.")):
        country = "United States"
    elif any(term in lowered for term in ("ireland", "dublin")):
        country = "Ireland"
    elif any(term in lowered for term in ("germany", "berlin", "munich")):
        country = "Germany"

    remote_restriction = None
    if work_model == WorkModel.REMOTE and raw:
        remote_restriction = raw

    return JobLocation(
        raw_text=raw or None,
        city=city,
        region=region,
        country=country,
        postcode=postcode,
        work_model=work_model,
        remote_restriction=remote_restriction,
    )


def _matching_sentences(text: str, phrases: Iterable[str]) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+|[\r\n]+", text)
    matches: list[str] = []

    for sentence in sentences:
        cleaned = clean_text(sentence)
        lowered = cleaned.lower()

        if cleaned and any(phrase in lowered for phrase in phrases):
            matches.append(cleaned)

    return matches


def classify_sponsorship(text: str | None) -> SponsorshipClassification:
    """Classify sponsorship wording conservatively."""

    source = clean_text(text)
    if not source:
        return SponsorshipClassification(
            status=SponsorshipStatus.UNCLEAR,
            evidence=[],
        )

    lowered = source.lower()

    unavailable_phrases = (
        "unable to provide visa sponsorship",
        "cannot provide sponsorship",
        "no visa sponsorship",
        "sponsorship is not available",
        "must already have the right to work",
        "without sponsorship",
        "will not sponsor",
    )
    security_phrases = (
        "security clearance",
        "uk national only",
        "british citizen only",
        "sole uk national",
        "developed vetting",
        "dv clearance",
        "sc clearance required",
    )
    confirmed_phrases = (
        "visa sponsorship available",
        "skilled worker sponsorship",
        "certificate of sponsorship",
        "we sponsor visas",
        "sponsorship can be provided",
    )
    likely_phrases = (
        "global mobility",
        "relocation support",
        "international applicants welcome",
        "visa support",
    )

    if any(phrase in lowered for phrase in security_phrases):
        return SponsorshipClassification(
            status=SponsorshipStatus.SECURITY_RESTRICTED,
            evidence=_matching_sentences(source, security_phrases),
        )

    if any(phrase in lowered for phrase in unavailable_phrases):
        return SponsorshipClassification(
            status=SponsorshipStatus.EXPLICITLY_UNAVAILABLE,
            evidence=_matching_sentences(source, unavailable_phrases),
        )

    if any(phrase in lowered for phrase in confirmed_phrases):
        return SponsorshipClassification(
            status=SponsorshipStatus.CONFIRMED,
            evidence=_matching_sentences(source, confirmed_phrases),
        )

    if any(phrase in lowered for phrase in likely_phrases):
        return SponsorshipClassification(
            status=SponsorshipStatus.LIKELY,
            evidence=_matching_sentences(source, likely_phrases),
        )

    return SponsorshipClassification(
        status=SponsorshipStatus.UNCLEAR,
        evidence=[],
    )


def normalise_parsed_job(parsed: ParsedJobRecord) -> NormalisedJob:
    """Convert a parsed vacancy into the canonical NormalisedJob model."""

    combined_sponsorship_text = " ".join(
        part
        for part in (
            parsed.sponsorship_text,
            parsed.description,
            " ".join(parsed.requirements),
        )
        if part
    )

    sponsorship = classify_sponsorship(combined_sponsorship_text)

    return NormalisedJob(
        source=parsed.source,
        source_job_id=parsed.source_job_id,
        application_url=parsed.application_url,
        canonical_url=(
            parsed.canonical_url
            or canonicalise_url(str(parsed.application_url))
        ),
        title=clean_text(parsed.title),
        title_normalised=normalise_job_title(parsed.title),
        company=clean_text(parsed.company),
        company_normalised=normalise_company_name(parsed.company),
        location=normalise_location(
            parsed.location_text,
            parsed.work_model_text,
        ),
        salary=normalise_salary(parsed.salary_text),
        employment_types=normalise_employment_types(
            parsed.employment_type_text
        ),
        sponsorship_status=sponsorship.status,
        sponsorship_evidence=sponsorship.evidence,
        description=clean_text(parsed.description),
        responsibilities=parsed.responsibilities,
        requirements=parsed.requirements,
        preferred_skills=parsed.preferred_skills,
        benefits=parsed.benefits,
        posted_date=parsed.posted_date,
        closing_date=parsed.closing_date,
        recruiter_name=parsed.recruiter_name,
        recruiter_email=parsed.recruiter_email,
        raw_source_data={
            "parser_name": parsed.parser_name,
            "parse_status": parsed.parse_status,
            "raw_metadata": parsed.raw_metadata,
            "location_text": parsed.location_text,
            "salary_text": parsed.salary_text,
            "employment_type_text": parsed.employment_type_text,
            "work_model_text": parsed.work_model_text,
            "sponsorship_text": parsed.sponsorship_text,
        },
    )
