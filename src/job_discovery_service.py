"""Discover public vacancies from supported ATS job boards."""

from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from urllib.parse import urljoin
import json
import ssl

import certifi
import yaml


GREENHOUSE_API_ROOT = "https://boards-api.greenhouse.io/v1/boards"
LEVER_API_ROOT = "https://api.lever.co/v0/postings"
ASHBY_API_ROOT = "https://api.ashbyhq.com/posting-api/job-board"
SMARTRECRUITERS_API_ROOT = (
    "https://api.smartrecruiters.com/v1/companies"
)

@dataclass(slots=True)
class DiscoveredJob:
    """One public vacancy discovered from an ATS board."""

    source: str
    company_token: str
    source_job_id: str
    title: str
    location: str | None
    url: str
    updated_at: str | None = None


def _ssl_context() -> ssl.SSLContext:
    """Return an SSL context using certifi's CA bundle."""

    return ssl.create_default_context(
        cafile=certifi.where()
    )


def _normalise(value: str | None) -> str:
    """Normalise text for simple case-insensitive matching."""

    if not value:
        return ""

    return " ".join(
        value.lower().split()
    )


def _contains_any(
    text: str | None,
    terms: list[str],
) -> bool:
    """Return True when text contains at least one search term."""

    if not terms:
        return True

    normalised_text = _normalise(
        text
    )

    return any(
        _normalise(term) in normalised_text
        for term in terms
        if _normalise(term)
    )


def load_avoided_seniority_terms(
    repository_root: Path | None = None,
) -> list[str]:
    """Load seniority terms to avoid from career_data/target_roles.yaml."""

    root = (
        repository_root
        or Path(__file__).resolve().parents[1]
    )

    target_roles_path = (
        root
        / "career_data"
        / "target_roles.yaml"
    )

    if not target_roles_path.exists():
        return []

    with target_roles_path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        data = yaml.safe_load(
            handle
        ) or {}

    seniority = data.get(
        "seniority",
        {},
    )

    avoid_terms = seniority.get(
        "avoid",
        [],
    )

    return [
        str(term).strip()
        for term in avoid_terms
        if str(term).strip()
    ]


def has_avoided_seniority(
    title: str,
    avoid_terms: list[str],
) -> bool:
    """Return True when a title contains an avoided seniority term."""

    normalised_title = _normalise(
        title
    )

    return any(
        _normalise(term) in normalised_title
        for term in avoid_terms
        if _normalise(term)
    )


def fetch_greenhouse_jobs(
    board_token: str,
    timeout_seconds: int = 20,
) -> list[dict[str, Any]]:
    """Fetch public vacancies from one Greenhouse board."""

    board_token = board_token.strip()

    if not board_token:
        return []

    url = (
        f"{GREENHOUSE_API_ROOT}/"
        f"{board_token}/jobs?content=true"
    )

    request = Request(
        url,
        headers={
            "User-Agent": (
                "job-application-agent/0.1 "
                "(public-job-discovery)"
            ),
            "Accept": "application/json",
        },
    )

    with urlopen(
        request,
        timeout=timeout_seconds,
        context=_ssl_context(),
    ) as response:
        payload = json.loads(
            response.read().decode(
                "utf-8"
            )
        )

    jobs = payload.get(
        "jobs",
        [],
    )

    if not isinstance(
        jobs,
        list,
    ):
        return []

    return jobs


def discover_greenhouse_jobs(
    board_tokens: list[str],
    role_terms: list[str] | None = None,
    location_terms: list[str] | None = None,
    limit: int = 20,
    exclude_avoided_seniority: bool = True,
) -> list[DiscoveredJob]:
    """Search configured Greenhouse boards for matching vacancies."""

    role_terms = (
        role_terms
        or []
    )

    location_terms = (
        location_terms
        or []
    )

    avoid_terms = (
        load_avoided_seniority_terms()
        if exclude_avoided_seniority
        else []
    )

    discovered: list[DiscoveredJob] = []

    for board_token in board_tokens:
        token = board_token.strip()

        if not token:
            continue

        jobs = fetch_greenhouse_jobs(
            token
        )

        for job in jobs:
            title = str(
                job.get(
                    "title"
                )
                or ""
            ).strip()

            if not title:
                continue

            if (
                exclude_avoided_seniority
                and has_avoided_seniority(
                    title,
                    avoid_terms,
                )
            ):
                continue

            location_data = job.get(
                "location"
            )

            if isinstance(
                location_data,
                dict,
            ):
                location = str(
                    location_data.get(
                        "name"
                    )
                    or ""
                ).strip() or None

            else:
                location = (
                    str(
                        location_data
                        or ""
                    ).strip()
                    or None
                )

            if not _contains_any(
                title,
                role_terms,
            ):
                continue

            if not _contains_any(
                location,
                location_terms,
            ):
                continue

            source_job_id = str(
                job.get(
                    "id"
                )
                or ""
            ).strip()

            if not source_job_id:
                continue

            url = str(
                job.get(
                    "absolute_url"
                )
                or ""
            ).strip()

            if not url:
                url = (
                    "https://job-boards.greenhouse.io/"
                    f"{token}/jobs/"
                    f"{source_job_id}"
                )

            updated_at = str(
                job.get(
                    "updated_at"
                )
                or ""
            ).strip() or None

            discovered.append(
                DiscoveredJob(
                    source="greenhouse",
                    company_token=token,
                    source_job_id=source_job_id,
                    title=title,
                    location=location,
                    url=url,
                    updated_at=updated_at,
                )
            )

            if len(discovered) >= limit:
                return discovered

    return discovered

def fetch_lever_jobs(
    site: str,
    timeout_seconds: int = 20,
) -> list[dict[str, Any]]:
    """Fetch public vacancies from one Lever site."""

    site = site.strip()

    if not site:
        return []

    url = (
        f"{LEVER_API_ROOT}/"
        f"{site}?mode=json"
    )

    request = Request(
        url,
        headers={
            "User-Agent": (
                "job-application-agent/0.1 "
                "(public-job-discovery)"
            ),
            "Accept": "application/json",
        },
    )

    with urlopen(
        request,
        timeout=timeout_seconds,
        context=_ssl_context(),
    ) as response:
        payload = json.loads(
            response.read().decode("utf-8")
        )

    if not isinstance(payload, list):
        return []

    return payload

def discover_lever_jobs(
    sites: list[str],
    role_terms: list[str] | None = None,
    location_terms: list[str] | None = None,
    limit: int = 20,
    exclude_avoided_seniority: bool = True,
) -> list[DiscoveredJob]:
    """Search configured Lever sites for matching vacancies."""

    role_terms = role_terms or []
    location_terms = location_terms or []

    avoid_terms = (
        load_avoided_seniority_terms()
        if exclude_avoided_seniority
        else []
    )

    discovered: list[DiscoveredJob] = []

    for site in sites:
        site = site.strip()

        if not site:
            continue

        jobs = fetch_lever_jobs(site)

        for job in jobs:
            title = str(
                job.get("text") or ""
            ).strip()

            if not title:
                continue

            if (
                exclude_avoided_seniority
                and has_avoided_seniority(
                    title,
                    avoid_terms,
                )
            ):
                continue

            categories = job.get(
                "categories",
                {},
            )

            location = None

            if isinstance(categories, dict):
                location = (
                    str(
                        categories.get("location")
                        or ""
                    ).strip()
                    or None
                )

            if not _contains_any(
                title,
                role_terms,
            ):
                continue

            if not _contains_any(
                location,
                location_terms,
            ):
                continue

            source_job_id = str(
                job.get("id") or ""
            ).strip()

            if not source_job_id:
                continue

            url = str(
                job.get("hostedUrl")
                or job.get("applyUrl")
                or ""
            ).strip()

            if not url:
                continue

            discovered.append(
                DiscoveredJob(
                    source="lever",
                    company_token=site,
                    source_job_id=source_job_id,
                    title=title,
                    location=location,
                    url=url,
                    updated_at=None,
                )
            )

            if len(discovered) >= limit:
                return discovered

    return discovered

def fetch_ashby_jobs(
    board_name: str,
    timeout_seconds: int = 20,
) -> list[dict[str, Any]]:
    """Fetch public vacancies from one Ashby job board."""

    board_name = board_name.strip()

    if not board_name:
        return []

    url = (
        f"{ASHBY_API_ROOT}/"
        f"{board_name}"
    )

    request = Request(
        url,
        headers={
            "User-Agent": (
                "job-application-agent/0.1 "
                "(public-job-discovery)"
            ),
            "Accept": "application/json",
        },
    )

    with urlopen(
        request,
        timeout=timeout_seconds,
        context=_ssl_context(),
    ) as response:
        payload = json.loads(
            response.read().decode("utf-8")
        )

    jobs = payload.get(
        "jobs",
        [],
    )

    if not isinstance(jobs, list):
        return []

    return jobs

def discover_ashby_jobs(
    board_names: list[str],
    role_terms: list[str] | None = None,
    location_terms: list[str] | None = None,
    limit: int = 20,
    exclude_avoided_seniority: bool = True,
) -> list[DiscoveredJob]:
    """Search configured Ashby boards for matching vacancies."""

    role_terms = role_terms or []
    location_terms = location_terms or []

    avoid_terms = (
        load_avoided_seniority_terms()
        if exclude_avoided_seniority
        else []
    )

    discovered: list[DiscoveredJob] = []

    for board_name in board_names:
        board_name = board_name.strip()

        if not board_name:
            continue

        jobs = fetch_ashby_jobs(
            board_name
        )

        for job in jobs:
            title = str(
                job.get("title") or ""
            ).strip()

            if not title:
                continue

            if (
                exclude_avoided_seniority
                and has_avoided_seniority(
                    title,
                    avoid_terms,
                )
            ):
                continue

            location = (
                str(
                    job.get("location") or ""
                ).strip()
                or None
            )

            if not _contains_any(
                title,
                role_terms,
            ):
                continue

            if not _contains_any(
                location,
                location_terms,
            ):
                continue

            source_job_id = str(
                job.get("id")
                or job.get("jobPostingId")
                or ""
            ).strip()

            job_url = str(
                job.get("jobUrl")
                or job.get("applyUrl")
                or ""
            ).strip()

            if not job_url:
                continue

            if not source_job_id:
                source_job_id = job_url.rstrip("/").split("/")[-1]

            discovered.append(
                DiscoveredJob(
                    source="ashby",
                    company_token=board_name,
                    source_job_id=source_job_id,
                    title=title,
                    location=location,
                    url=job_url,
                    updated_at=None,
                )
            )

            if len(discovered) >= limit:
                return discovered

    return discovered

def discover_workable_jobs(
    site_urls: list[str],
    role_terms: list[str] | None = None,
    location_terms: list[str] | None = None,
    limit: int = 20,
    exclude_avoided_seniority: bool = True,
) -> list[DiscoveredJob]:
    """Discover public vacancies from Workable jobs.md feeds."""

    role_terms = role_terms or []
    location_terms = location_terms or []

    avoid_terms = (
        load_avoided_seniority_terms()
        if exclude_avoided_seniority
        else []
    )

    discovered: list[DiscoveredJob] = []

    for site_url in site_urls:
        site_url = site_url.strip().rstrip("/") + "/"

        if not site_url:
            continue

        jobs_url = f"{site_url}jobs.md"

        request = Request(
            jobs_url,
            headers={
                "User-Agent": (
                    "job-application-agent/0.1 "
                    "(public-job-discovery)"
                ),
                "Accept": "text/plain",
            },
        )

        with urlopen(
            request,
            timeout=20,
            context=_ssl_context(),
        ) as response:
            text = response.read().decode(
                "utf-8",
                errors="replace",
            )

        for raw_line in text.splitlines():
            line = raw_line.strip()

            if not line.startswith("|"):
                continue

            columns = [
                column.strip()
                for column in line.strip("|").split("|")
            ]

            if len(columns) < 7:
                continue

            title = columns[0]
            location = columns[2]
            details = columns[6]

            if title.lower() in {
                "title",
                "-------",
            }:
                continue

            if not title:
                continue

            if (
                exclude_avoided_seniority
                and has_avoided_seniority(
                    title,
                    avoid_terms,
                )
            ):
                continue

            if not _contains_any(
                title,
                role_terms,
            ):
                continue

            if not _contains_any(
                location,
                location_terms,
            ):
                continue

            job_id_match = re.search(
                r"/jobs/view/([A-Za-z0-9_-]+)\.md",
                details,
                flags=re.I,
            )

            if not job_id_match:
                continue

            source_job_id = job_id_match.group(1)

            # Convert the machine-readable Workable ID
            # into the normal public vacancy URL used by ingestion.
            job_url = (
                f"{site_url}j/"
                f"{source_job_id}/"
            )

            discovered.append(
                DiscoveredJob(
                    source="workable",
                    company_token=site_url,
                    source_job_id=source_job_id,
                    title=title,
                    location=location,
                    url=job_url,
                    updated_at=None,
                )
            )

            if len(discovered) >= limit:
                return discovered

    return discovered
 
def fetch_smartrecruiters_jobs(
    company_identifier: str,
    timeout_seconds: int = 20,
    page_size: int = 100,
    max_pages: int = 20,
) -> list[dict[str, Any]]:
    """Fetch active public postings from one SmartRecruiters company."""

    company_identifier = company_identifier.strip()

    if not company_identifier:
        return []

    page_size = min(
        max(page_size, 1),
        100,
    )

    all_jobs: list[dict[str, Any]] = []
    offset = 0

    for _ in range(max_pages):
        url = (
            f"{SMARTRECRUITERS_API_ROOT}/"
            f"{company_identifier}/postings"
            f"?limit={page_size}"
            f"&offset={offset}"
        )

        request = Request(
            url,
            headers={
                "User-Agent": (
                    "job-application-agent/0.1 "
                    "(public-job-discovery)"
                ),
                "Accept": "application/json",
            },
        )

        with urlopen(
            request,
            timeout=timeout_seconds,
            context=_ssl_context(),
        ) as response:
            payload = json.loads(
                response.read().decode("utf-8")
            )

        content = payload.get(
            "content",
            [],
        )

        if not isinstance(content, list):
            break

        all_jobs.extend(content)

        total_found = int(
            payload.get(
                "totalFound",
                len(all_jobs),
            )
            or len(all_jobs)
        )

        if len(all_jobs) >= total_found:
            break

        if not content:
            break

        offset += page_size

    return all_jobs

def discover_smartrecruiters_jobs(
    company_identifiers: list[str],
    role_terms: list[str] | None = None,
    location_terms: list[str] | None = None,
    limit: int = 20,
    exclude_avoided_seniority: bool = True,
) -> list[DiscoveredJob]:
    """Search configured SmartRecruiters companies for matching vacancies."""

    role_terms = role_terms or []
    location_terms = location_terms or []

    avoid_terms = (
        load_avoided_seniority_terms()
        if exclude_avoided_seniority
        else []
    )

    discovered: list[DiscoveredJob] = []

    for company_identifier in company_identifiers:
        company_identifier = company_identifier.strip()

        if not company_identifier:
            continue

        jobs = fetch_smartrecruiters_jobs(
            company_identifier,
            page_size=100,
            )

        for job in jobs:
            title = str(
                job.get("name")
                or job.get("title")
                or ""
            ).strip()

            if not title:
                continue

            if (
                exclude_avoided_seniority
                and has_avoided_seniority(
                    title,
                    avoid_terms,
                )
            ):
                continue

            location_data = job.get(
                "location",
                {},
            )

            location_parts: list[str] = []

            if isinstance(location_data, dict):
                for key in (
                    "city",
                    "region",
                    "country",
                ):
                    value = location_data.get(key)

                    if value:
                        location_parts.append(
                            str(value).strip()
                        )

            location = (
                ", ".join(location_parts)
                if location_parts
                else None
            )

            if not _contains_any(
                title,
                role_terms,
            ):
                continue

            if not _contains_any(
                location,
                location_terms,
            ):
                continue

            source_job_id = str(
                job.get("id")
                or job.get("uuid")
                or ""
            ).strip()

            if not source_job_id:
                continue

            slug = re.sub(
                r"[^a-z0-9]+",
                "-",
                title.lower(),
                ).strip("-")

            job_url = (
                "https://jobs.smartrecruiters.com/"
                f"{company_identifier}/"
                f"{source_job_id}-"
                f"{slug}"
                )

            discovered.append(
                DiscoveredJob(
                    source="smartrecruiters",
                    company_token=company_identifier,
                    source_job_id=source_job_id,
                    title=title,
                    location=location,
                    url=job_url,
                    updated_at=None,
                )
            )

            if len(discovered) >= limit:
                return discovered

    return discovered
