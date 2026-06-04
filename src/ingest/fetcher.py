from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import httpx

try:
    import certifi
except ImportError:  # pragma: no cover
    certifi = None  # type: ignore[assignment]

from src.config.settings import PROJECT_ROOT, get_settings
from src.ingest.amc_spa import fetch_amc_product_page
from src.ingest.manifest import SourceEntry

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "MF-RAG-ChatBot/0.1 (+https://github.com; facts-only corpus ingest; contact: local-dev)"
)
DEFAULT_TIMEOUT = 60.0
DEFAULT_RETRIES = 3
DEFAULT_RATE_LIMIT_SECONDS = 1.0


@dataclass
class FetchResult:
    source_id: str
    url: str
    status_code: int
    content: bytes
    content_type: str
    fetched_at: datetime
    content_hash: str
    last_modified: datetime | None = None
    raw_path: Path | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status_code < 300 and bool(self.content)


def content_hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_url_allowed(url: str, allowed_domains: list[str]) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    for domain in allowed_domains:
        domain = domain.lower().strip()
        if host == domain or host.endswith(f".{domain}"):
            return True
    return False


class DocumentFetcher:
    """HTTP fetcher with retries, rate limiting, and optional raw storage (task 1.6)."""

    def __init__(
        self,
        *,
        raw_dir: Path | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        rate_limit_seconds: float = DEFAULT_RATE_LIMIT_SECONDS,
        user_agent: str = DEFAULT_USER_AGENT,
        allowed_domains: list[str] | None = None,
        client: httpx.Client | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        settings = get_settings()
        self.raw_dir = raw_dir or (PROJECT_ROOT / "corpus" / "raw")
        self.timeout = timeout
        self.retries = retries
        self.rate_limit_seconds = rate_limit_seconds
        self.user_agent = user_agent
        self.allowed_domains = allowed_domains or settings.allowed_domain_list()
        self._client = client
        self._owns_client = client is None
        self._sleep = sleep_fn
        self._last_fetch_at: float | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            settings = get_settings()
            verify: bool | str = settings.fetch_ssl_verify
            if verify is not False and certifi is not None:
                verify = certifi.where()
            self._client = httpx.Client(
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent},
                follow_redirects=True,
                verify=verify,
            )
        return self._client

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> DocumentFetcher:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _rate_limit(self) -> None:
        if self._last_fetch_at is None:
            return
        elapsed = time.monotonic() - self._last_fetch_at
        if elapsed < self.rate_limit_seconds:
            self._sleep(self.rate_limit_seconds - elapsed)

    def fetch_source(
        self,
        entry: SourceEntry,
        *,
        save_raw: bool = True,
    ) -> FetchResult:
        if entry.doc_type == "amc_product_page":
            return self._fetch_amc_product_page(entry, save_raw=save_raw)

        if not is_url_allowed(entry.url, self.allowed_domains):
            return FetchResult(
                source_id=entry.id,
                url=entry.url,
                status_code=0,
                content=b"",
                content_type="",
                fetched_at=datetime.now(timezone.utc),
                content_hash="",
                error=f"URL domain not in allowlist: {entry.url}",
            )

        last_error: str | None = None
        for attempt in range(1, self.retries + 1):
            try:
                self._rate_limit()
                client = self._get_client()
                response = client.get(entry.url)
                self._last_fetch_at = time.monotonic()

                content = response.content
                content_hash = content_hash_bytes(content) if content else ""
                last_modified = _parse_last_modified(response.headers.get("Last-Modified"))
                fetched_at = datetime.now(timezone.utc)

                raw_path: Path | None = None
                if save_raw and content and response.is_success:
                    raw_path = self._save_raw(entry, content, response.headers.get("Content-Type"))

                if not response.is_success:
                    last_error = f"HTTP {response.status_code}"
                    if attempt < self.retries:
                        self._sleep(2**attempt)
                        continue
                    return FetchResult(
                        source_id=entry.id,
                        url=entry.url,
                        status_code=response.status_code,
                        content=content,
                        content_type=response.headers.get("Content-Type", ""),
                        fetched_at=fetched_at,
                        content_hash=content_hash,
                        last_modified=last_modified,
                        raw_path=raw_path,
                        error=last_error,
                    )

                return FetchResult(
                    source_id=entry.id,
                    url=entry.url,
                    status_code=response.status_code,
                    content=content,
                    content_type=response.headers.get("Content-Type", ""),
                    fetched_at=fetched_at,
                    content_hash=content_hash,
                    last_modified=last_modified,
                    raw_path=raw_path,
                )
            except httpx.HTTPError as exc:
                last_error = str(exc)
                logger.warning(
                    "Fetch attempt %s/%s failed for %s: %s",
                    attempt,
                    self.retries,
                    entry.id,
                    exc,
                )
                if attempt < self.retries:
                    self._sleep(2**attempt)

        return FetchResult(
            source_id=entry.id,
            url=entry.url,
            status_code=0,
            content=b"",
            content_type="",
            fetched_at=datetime.now(timezone.utc),
            content_hash="",
            error=last_error or "Unknown fetch error",
        )

    def _fetch_amc_product_page(self, entry: SourceEntry, *, save_raw: bool) -> FetchResult:
        if not is_url_allowed(entry.url, self.allowed_domains):
            return FetchResult(
                source_id=entry.id,
                url=entry.url,
                status_code=0,
                content=b"",
                content_type="",
                fetched_at=datetime.now(timezone.utc),
                content_hash="",
                error=f"URL domain not in allowlist: {entry.url}",
            )

        fetched_at = datetime.now(timezone.utc)
        try:
            self._rate_limit()
            payload = fetch_amc_product_page(entry.url)
            self._last_fetch_at = time.monotonic()
            content = payload.to_bytes()
            content_hash = content_hash_bytes(content)
            raw_path: Path | None = None
            if save_raw and content:
                raw_path = self._save_raw(entry, content, "application/json")
            return FetchResult(
                source_id=entry.id,
                url=entry.url,
                status_code=200,
                content=content,
                content_type="application/json",
                fetched_at=fetched_at,
                content_hash=content_hash,
                raw_path=raw_path,
            )
        except Exception as exc:
            logger.warning("AMC product page fetch failed for %s: %s", entry.id, exc)
            return FetchResult(
                source_id=entry.id,
                url=entry.url,
                status_code=0,
                content=b"",
                content_type="",
                fetched_at=fetched_at,
                content_hash="",
                error=str(exc),
            )

    def _save_raw(self, entry: SourceEntry, content: bytes, content_type: str | None) -> Path:
        ext = _extension_for_content(content_type, content)
        directory = self.raw_dir / entry.id
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"latest{ext}"
        path.write_bytes(content)
        return path


def _parse_last_modified(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError, IndexError):
        return None


def _extension_for_content(content_type: str | None, content: bytes) -> str:
    ct = (content_type or "").lower()
    if "pdf" in ct or content[:4] == b"%PDF":
        return ".pdf"
    if "html" in ct or content[:15].lower().strip().startswith(b"<!doctype") or b"<html" in content[:500].lower():
        return ".html"
    return ".bin"
