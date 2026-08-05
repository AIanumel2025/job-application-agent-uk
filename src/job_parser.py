"""Parse fetched vacancy pages into structured job records."""

from __future__ import annotations

import html as html_lib
import json
import re
from datetime import date, datetime
from html.parser import HTMLParser
from typing import Any, Iterable
from urllib.parse import urljoin

from pydantic import ValidationError

from src.job_models import (
    FetchStatus,
    FetchedJobPage,
    JobSource,
    ParseStatus,
    ParsedJobRecord,
)


_WHITESPACE_RE = re.compile(r"\s+")
_TAG_RE = re.compile(r"<[^>]+>")
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)


class JobHTMLExtractor(HTMLParser):
    """Collect useful text, metadata, and JSON-LD from an HTML document."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_text: list[str] = []
        self.visible_text: list[str] = []
        self.json_ld_blocks: list[str] = []
        self.meta: dict[str, str] = {}
        self.headings: list[tuple[str, str]] = []
        self._capture_title = False
        self._capture_json_ld = False
        self._json_buffer: list[str] = []
        self._heading_tag: str | None = None
        self._heading_buffer: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value for key, value in attrs}
        tag = tag.lower()

        if tag in {"script", "style", "noscript", "svg"}:
            if tag == "script" and (
                attrs_dict.get("type") or ""
            ).lower() == "application/ld+json":
                self._capture_json_ld = True
                self._json_buffer = []
            else:
                self._ignored_depth += 1
            return

        if tag == "title":
            self._capture_title = True

        if tag == "meta":
            key = (
                attrs_dict.get("property")
                or attrs_dict.get("name")
                or attrs_dict.get("itemprop")
            )
            content = attrs_dict.get("content")
            if key and content:
                self.meta[key.lower()] = content.strip()

        if tag in {"h1", "h2", "h3"}:
            self._heading_tag = tag
            self._heading_buffer = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()

        if tag == "script" and self._capture_json_ld:
            self.json_ld_blocks.append("".join(self._json_buffer).strip())
            self._capture_json_ld = False
            self._json_buffer = []
            return

        if tag in {"script", "style", "noscript", "svg"} and self._ignored_depth:
            self._ignored_depth -= 1
            return

        if tag == "title":
            self._capture_title = False

        if self._heading_tag == tag:
            text = clean_text(" ".join(self._heading_buffer))
            if text:
                self.headings.append((tag, text))
            self._heading_tag = None
            self._heading_buffer = []

    def handle_data(self, data: str) -> None:
        if self._capture_json_ld:
            self._json_buffer.append(data)
            return

        if self._ignored_depth:
            return

        if self._capture_title:
            self.title_text.append(data)

        if self._heading_tag:
            self._heading_buffer.append(data)

        text = clean_text(data)
        if text:
            self.visible_text.append(text)


def clean_text(value: Any) -> str:
    """Convert HTML or arbitrary text into a compact plain-text string."""

    if value is None:
        return ""

    text = str(value)
    text = _TAG_RE.sub(" ", text)
    text = html_lib.unescape(text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def parse_iso_date(value: Any) -> date | None:
    if not value:
        return None

    text = clean_text(value)
    if not text:
        return None

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    return None


def _iter_json_objects(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        graph = value.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                yield from _iter_json_objects(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_json_objects(item)


def _is_job_posting(obj: dict[str, Any]) -> bool:
    object_type = obj.get("@type")
    if isinstance(object_type, list):
        return any(str(item).lower() == "jobposting" for item in object_type)
    return str(object_type).lower() == "jobposting"


def extract_json_ld_job(blocks: list[str]) -> dict[str, Any] | None:
    for block in blocks:
        if not block:
            continue

        try:
            decoded = json.loads(block)
        except json.JSONDecodeError:
            continue

        for obj in _iter_json_objects(decoded):
            if _is_job_posting(obj):
                return obj

    return None


def _organisation_name(value: Any) -> str:
    if isinstance(value, dict):
        return clean_text(value.get("name"))
    return clean_text(value)


def _address_text(value: Any) -> str:
    if isinstance(value, list):
        parts = [_address_text(item) for item in value]
        return ", ".join(part for part in parts if part)

    if not isinstance(value, dict):
        return clean_text(value)

    address = value.get("address", value)
    if isinstance(address, dict):
        parts = [
            address.get("streetAddress"),
            address.get("addressLocality"),
            address.get("addressRegion"),
            address.get("postalCode"),
            address.get("addressCountry"),
        ]
        return ", ".join(clean_text(part) for part in parts if clean_text(part))

    return clean_text(address)


def _salary_text(value: Any) -> str | None:
    if not isinstance(value, dict):
        text = clean_text(value)
        return text or None

    currency = clean_text(value.get("currency"))
    salary_value = value.get("value")

    if isinstance(salary_value, dict):
        minimum = salary_value.get("minValue")
        maximum = salary_value.get("maxValue")
        unit = clean_text(salary_value.get("unitText"))

        if minimum is not None and maximum is not None:
            return clean_text(f"{currency} {minimum}-{maximum} {unit}")
        if minimum is not None:
            return clean_text(f"{currency} {minimum}+ {unit}")
        if salary_value.get("value") is not None:
            return clean_text(
                f"{currency} {salary_value.get('value')} {unit}"
            )

    return clean_text(value) or None


def _employment_type_text(value: Any) -> str | None:
    if isinstance(value, list):
        return ", ".join(clean_text(item) for item in value if clean_text(item))
    text = clean_text(value)
    return text or None


def _extract_sections(text: str) -> tuple[list[str], list[str], list[str], list[str]]:
    """Extract conservative bullet-like lines from common job sections."""

    categories = {
        "responsibilities": {
            "responsibilities", "what you will do", "what you'll do",
            "the role", "your role", "key duties",
        },
        "requirements": {
            "requirements", "what we are looking for", "what we're looking for",
            "essential skills", "person specification", "about you",
        },
        "preferred": {
            "preferred skills", "desirable", "nice to have", "bonus skills",
        },
        "benefits": {
            "benefits", "what we offer", "our benefits", "perks",
        },
    }

    output = {key: [] for key in categories}
    current: str | None = None

    for raw_line in re.split(r"[\r\n]+", text):
        line = clean_text(raw_line)
        if not line:
            continue

        lowered = line.lower().rstrip(":")
        matched = next(
            (
                key
                for key, headings in categories.items()
                if lowered in headings
            ),
            None,
        )
        if matched:
            current = matched
            continue

        if current and (
            raw_line.lstrip().startswith(("-", "•", "*"))
            or len(line) <= 240
        ):
            output[current].append(line.lstrip("-•* ").strip())

    return (
        output["responsibilities"],
        output["requirements"],
        output["preferred"],
        output["benefits"],
    )


def _parse_from_json_ld(
    job: dict[str, Any],
    *,
    source: JobSource,
    page_url: str,
) -> ParsedJobRecord:
    title = clean_text(job.get("title"))
    company = _organisation_name(job.get("hiringOrganization"))
    description = clean_text(job.get("description"))
    application_url = (
        clean_text(job.get("url"))
        or clean_text(job.get("applicationContact"))
        or page_url
    )

    responsibilities, requirements, preferred, benefits = _extract_sections(
        str(job.get("description") or "")
    )

    identifier = job.get("identifier")
    if isinstance(identifier, dict):
        source_job_id = clean_text(identifier.get("value"))
    else:
        source_job_id = clean_text(identifier)

    return ParsedJobRecord(
        source=source,
        source_job_id=source_job_id or None,
        application_url=urljoin(page_url, application_url),
        title=title,
        company=company,
        location_text=_address_text(job.get("jobLocation")) or None,
        salary_text=_salary_text(job.get("baseSalary")),
        employment_type_text=_employment_type_text(job.get("employmentType")),
        work_model_text=clean_text(job.get("jobLocationType")) or None,
        description=description,
        responsibilities=responsibilities,
        requirements=requirements,
        preferred_skills=preferred,
        benefits=benefits,
        posted_date=parse_iso_date(job.get("datePosted")),
        closing_date=parse_iso_date(job.get("validThrough")),
        parse_status=ParseStatus.SUCCESS,
        parser_name="json_ld_job_posting",
        raw_metadata=job,
    )


def _parse_generic(
    extractor: JobHTMLExtractor,
    *,
    source: JobSource,
    page_url: str,
) -> ParsedJobRecord:
    title = (
        extractor.meta.get("og:title")
        or extractor.meta.get("twitter:title")
        or next(
            (text for tag, text in extractor.headings if tag == "h1"),
            "",
        )
        or clean_text(" ".join(extractor.title_text))
    )

    company = (
        extractor.meta.get("og:site_name")
        or extractor.meta.get("application-name")
        or ""
    )

    description = (
        extractor.meta.get("description")
        or extractor.meta.get("og:description")
        or " ".join(extractor.visible_text)
    )
    description = clean_text(description)

    if not title:
        raise ValueError("could not identify a job title")

    if not company:
        raise ValueError("could not identify the hiring company")

    if not description:
        raise ValueError("could not identify a job description")

    visible_joined = "\n".join(extractor.visible_text)
    responsibilities, requirements, preferred, benefits = _extract_sections(
        visible_joined
    )

    email_match = _EMAIL_RE.search(visible_joined)

    return ParsedJobRecord(
        source=source,
        application_url=page_url,
        title=clean_text(title),
        company=clean_text(company),
        description=description,
        responsibilities=responsibilities,
        requirements=requirements,
        preferred_skills=preferred,
        benefits=benefits,
        recruiter_email=email_match.group(0) if email_match else None,
        parse_status=ParseStatus.PARTIAL,
        parser_name="generic_html",
        raw_metadata={
            "meta": extractor.meta,
            "headings": extractor.headings,
        },
    )


def parse_job_page(page: FetchedJobPage) -> ParsedJobRecord:
    """Parse one successfully fetched vacancy page.

    JSON-LD JobPosting data is preferred because it is structured and usually
    more reliable. A conservative generic HTML fallback is used otherwise.
    """

    if page.fetch_status != FetchStatus.SUCCESS:
        raise ValueError(
            f"cannot parse page with fetch status {page.fetch_status!r}"
        )

    if not page.html:
        raise ValueError("cannot parse a page without HTML")

    page_url = str(page.final_url or page.requested_url)

    extractor = JobHTMLExtractor()
    extractor.feed(page.html)
    extractor.close()

    json_ld_job = extract_json_ld_job(extractor.json_ld_blocks)

    try:
        if json_ld_job is not None:
            return _parse_from_json_ld(
                json_ld_job,
                source=page.source,
                page_url=page_url,
            )

        return _parse_generic(
            extractor,
            source=page.source,
            page_url=page_url,
        )
    except ValidationError as exc:
        messages = "; ".join(
            f"{'.'.join(str(item) for item in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        raise ValueError(f"parsed job data failed validation: {messages}") from exc
