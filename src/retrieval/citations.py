from __future__ import annotations

from urllib.parse import urlparse

from src.ingest.fetcher import is_url_allowed
from src.ingest.manifest import CorpusManifest


def is_public_citation_url(url: str, *, allowed_domains: list[str]) -> bool:
    """Reject browser-extension wrappers and legacy digitalfactsheet PDF links."""
    if not url or not is_url_allowed(url, allowed_domains):
        return False
    lowered = url.lower().strip()
    if lowered.startswith("chrome-extension:") or "chrome-extension://" in lowered:
        return False
    if "digitalfactsheet.icicipruamc.com" in lowered and ".pdf" in lowered:
        return False
    return True


def is_amc_product_page_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host not in {"www.icicipruamc.com", "icicipruamc.com"}:
        return False
    return "/mutual-fund/" in (parsed.path or "")


def preferred_citation_url(
    *,
    scheme_id: str | None,
    candidate_urls: list[str],
    manifest: CorpusManifest,
    allowed_domains: list[str],
) -> str | None:
    """Prefer canonical AMC product page from manifest over retrieved chunk URLs."""
    if scheme_id:
        canonical = manifest.factsheet_url_for_scheme(scheme_id)
        if canonical and is_public_citation_url(canonical, allowed_domains=allowed_domains):
            return canonical

    for url in candidate_urls:
        if is_amc_product_page_url(url) and is_public_citation_url(
            url, allowed_domains=allowed_domains
        ):
            return url

    for url in candidate_urls:
        if is_public_citation_url(url, allowed_domains=allowed_domains):
            return url

    return None
