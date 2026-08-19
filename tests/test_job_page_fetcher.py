"""Tests for the public job-page fetcher."""

from __future__ import annotations

from email.message import Message

from src.job_models import FetchStatus, JobInputRecord
from src.job_page_fetcher import fetch_job_page


class FakeResponse:
    def __init__(
        self,
        body: bytes,
        content_type: str = "text/html",
        *,
        url: str = "https://example.com/jobs/1",
        encoding: str = "utf-8",
        status: int = 200,
    ) -> None:
        self._body = body
        self._url = url
        self.status = status

        self.headers = Message()
        self.headers["Content-Type"] = (
            f"{content_type}; charset={encoding}"
        )

    def read(self, amount: int = -1) -> bytes:
        if amount == -1:
            return self._body
        return self._body[:amount]

    def geturl(self) -> str:
        return self._url

    def getcode(self) -> int:
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_fetches_html_successfully(monkeypatch) -> None:
    def fake_urlopen(request, timeout, context=None):
        return FakeResponse(
            b"<html><h1>Data Engineer</h1></html>"
        )

    monkeypatch.setattr(
        "src.job_page_fetcher.urlopen",
        fake_urlopen,
    )

    record = JobInputRecord(
        url="https://example.com/jobs/1",
        source="manual",
    )

    page = fetch_job_page(record)

    assert page.fetch_status == FetchStatus.SUCCESS
    assert page.status_code == 200
    assert page.error_message is None
    assert page.html is not None
    assert "Data Engineer" in page.html


def test_rejects_unsupported_content(monkeypatch) -> None:
    def fake_urlopen(request, timeout, context=None):
        return FakeResponse(
            b"%PDF",
            content_type="application/pdf",
        )

    monkeypatch.setattr(
        "src.job_page_fetcher.urlopen",
        fake_urlopen,
    )

    record = JobInputRecord(
        url="https://example.com/jobs/1",
        source="manual",
    )

    page = fetch_job_page(record)

    assert page.fetch_status != FetchStatus.SUCCESS
    assert page.html is None
    assert page.error_message is not None
    assert "content" in page.error_message.casefold()


def test_rejects_oversized_response(monkeypatch) -> None:
    def fake_urlopen(request, timeout, context=None):
        return FakeResponse(b"x" * 101)

    monkeypatch.setattr(
        "src.job_page_fetcher.urlopen",
        fake_urlopen,
    )

    record = JobInputRecord(
        url="https://example.com/jobs/1",
        source="manual",
    )

    page = fetch_job_page(
        record,
        max_bytes=100,
    )

    assert page.fetch_status != FetchStatus.SUCCESS
    assert page.html is None
    assert page.error_message is not None
    assert (
        "exceeded" in page.error_message.casefold()
        or "large" in page.error_message.casefold()
        or "size" in page.error_message.casefold()
    )
