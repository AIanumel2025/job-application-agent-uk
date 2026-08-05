"""Safely fetch public job vacancy pages."""

from __future__ import annotations

import gzip
import time
from datetime import datetime, timezone
from typing import Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.job_models import (
    FetchStatus,
    FetchedJobPage,
    JobInputRecord,
    JobSource,
)


DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_MAX_BYTES = 5_000_000
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; UKJobApplicationAgent/1.0; "
    "+human-in-the-loop vacancy research)"
)

ALLOWED_CONTENT_TYPES = {
    "text/html",
    "application/xhtml+xml",
}


def _decode_response_body(
    body: bytes,
    content_type_header: str | None,
    content_encoding: str | None,
) -> str:
    """Decode a fetched HTTP body into text."""

    if content_encoding and "gzip" in content_encoding.lower():
        body = gzip.decompress(body)

    charset = "utf-8"
    if content_type_header and "charset=" in content_type_header.lower():
        charset = content_type_header.lower().split("charset=", 1)[1].split(";", 1)[0].strip()

    try:
        return body.decode(charset, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def _normalise_content_type(value: str | None) -> str | None:
    if not value:
        return None
    return value.split(";", 1)[0].strip().lower()


def fetch_job_page(
    record: JobInputRecord,
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    user_agent: str = DEFAULT_USER_AGENT,
    extra_headers: Mapping[str, str] | None = None,
) -> FetchedJobPage:
    """Fetch one public vacancy page.

    The function follows ordinary redirects, uses a finite timeout, limits the
    response size, and does not attempt to bypass authentication, bot controls,
    robots restrictions, or paywalls.
    """

    requested_url = str(record.url)
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Encoding": "gzip",
        "Cache-Control": "no-cache",
    }
    if extra_headers:
        headers.update(extra_headers)

    request = Request(requested_url, headers=headers, method="GET")
    started = time.perf_counter()

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            status_code = getattr(response, "status", None) or response.getcode()
            final_url = response.geturl()
            content_type_header = response.headers.get("Content-Type")
            content_type = _normalise_content_type(content_type_header)
            content_encoding = response.headers.get("Content-Encoding")

            if content_type not in ALLOWED_CONTENT_TYPES:
                return FetchedJobPage(
                    requested_url=requested_url,
                    final_url=final_url,
                    source=record.source,
                    fetch_status=FetchStatus.UNSUPPORTED,
                    status_code=status_code,
                    content_type=content_type,
                    fetched_at=datetime.now(timezone.utc),
                    elapsed_ms=elapsed_ms,
                    error_message=(
                        f"unsupported content type: {content_type or 'unknown'}"
                    ),
                )

            body = response.read(max_bytes + 1)
            if len(body) > max_bytes:
                return FetchedJobPage(
                    requested_url=requested_url,
                    final_url=final_url,
                    source=record.source,
                    fetch_status=FetchStatus.FAILED,
                    status_code=status_code,
                    content_type=content_type,
                    fetched_at=datetime.now(timezone.utc),
                    elapsed_ms=elapsed_ms,
                    error_message=f"response exceeded {max_bytes} bytes",
                )

            html = _decode_response_body(
                body,
                content_type_header,
                content_encoding,
            )

            if not html.strip():
                return FetchedJobPage(
                    requested_url=requested_url,
                    final_url=final_url,
                    source=record.source,
                    fetch_status=FetchStatus.FAILED,
                    status_code=status_code,
                    content_type=content_type,
                    fetched_at=datetime.now(timezone.utc),
                    elapsed_ms=elapsed_ms,
                    error_message="empty response body",
                )

            return FetchedJobPage(
                requested_url=requested_url,
                final_url=final_url,
                source=record.source,
                fetch_status=FetchStatus.SUCCESS,
                status_code=status_code,
                content_type=content_type,
                html=html,
                fetched_at=datetime.now(timezone.utc),
                elapsed_ms=elapsed_ms,
            )

    except HTTPError as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        status = exc.code

        if status in {401, 403, 429}:
            fetch_status = FetchStatus.BLOCKED
        else:
            fetch_status = FetchStatus.FAILED

        return FetchedJobPage(
            requested_url=requested_url,
            final_url=exc.geturl() or requested_url,
            source=record.source,
            fetch_status=fetch_status,
            status_code=status,
            content_type=_normalise_content_type(
                exc.headers.get("Content-Type") if exc.headers else None
            ),
            fetched_at=datetime.now(timezone.utc),
            elapsed_ms=elapsed_ms,
            error_message=f"HTTP {status}: {exc.reason}",
        )

    except (URLError, TimeoutError, OSError) as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        reason = getattr(exc, "reason", exc)

        return FetchedJobPage(
            requested_url=requested_url,
            source=record.source,
            fetch_status=FetchStatus.FAILED,
            fetched_at=datetime.now(timezone.utc),
            elapsed_ms=elapsed_ms,
            error_message=f"request failed: {reason}",
        )


def fetch_job_url(
    url: str,
    *,
    source: JobSource = JobSource.MANUAL,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> FetchedJobPage:
    """Convenience wrapper for fetching a URL without building a record first."""

    record = JobInputRecord(url=url, source=source)
    return fetch_job_page(
        record,
        timeout_seconds=timeout_seconds,
        max_bytes=max_bytes,
    )
