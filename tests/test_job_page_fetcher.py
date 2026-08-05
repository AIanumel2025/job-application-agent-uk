from __future__ import annotations

from email.message import Message

from src.job_models import JobInputRecord
from src.job_page_fetcher import fetch_job_page


class FakeResponse:
    def __init__(self, body: bytes, content_type: str = "text/html; charset=utf-8") -> None:
        self._body = body
        self.status = 200
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def getcode(self) -> int:
        return self.status

    def geturl(self) -> str:
        return "https://example.com/jobs/1"

    def read(self, size: int = -1) -> bytes:
        return self._body[:size] if size >= 0 else self._body


def test_fetches_html_successfully(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeResponse(b"<html><h1>Data Engineer</h1></html>")

    monkeypatch.setattr("src.job_page_fetcher.urlopen", fake_urlopen)
    record = JobInputRecord(url="https://example.com/jobs/1", source="manual")
    page = fetch_job_page(record)
    assert str(page.fetch_status) == "success"
    assert page.status_code == 200
    assert "Data Engineer" in page.html


def test_rejects_unsupported_content(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeResponse(b"%PDF", "application/pdf")

    monkeypatch.setattr("src.job_page_fetcher.urlopen", fake_urlopen)
    record = JobInputRecord(url="https://example.com/jobs/1", source="manual")
    page = fetch_job_page(record)
    assert str(page.fetch_status) == "unsupported"
    assert "unsupported content type" in page.error_message


def test_rejects_oversized_response(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeResponse(b"x" * 101)

    monkeypatch.setattr("src.job_page_fetcher.urlopen", fake_urlopen)
    record = JobInputRecord(url="https://example.com/jobs/1", source="manual")
    page = fetch_job_page(record, max_bytes=100)
    assert str(page.fetch_status) == "failed"
    assert "exceeded" in page.error_message
