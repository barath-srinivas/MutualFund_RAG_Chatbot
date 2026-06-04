from __future__ import annotations

from datetime import date, datetime

from src.config.settings import get_settings
from src.retrieval.citations import is_amc_product_page_url, is_public_citation_url
from src.retrieval.models import AssembledContext, RetrievedChunk

# Cap per-chunk text so multiple sections from one PDF can fit in context.
_MAX_CHUNK_TEXT_CHARS = 1400


def assemble_context(chunks: list[RetrievedChunk]) -> AssembledContext:
    settings = get_settings()
    max_chars = settings.retrieval_max_context_chars

    deduped = _dedupe_by_source_url(chunks)
    selected: list[RetrievedChunk] = []
    total_chars = 0
    for chunk in deduped:
        block_len = len(chunk.text) + 120
        if selected and total_chars + block_len > max_chars:
            break
        selected.append(chunk)
        total_chars += block_len

    blocks: list[str] = []
    citation_urls: list[str] = []
    seen_urls: set[str] = set()
    latest: date | None = None

    allowed = settings.allowed_domain_list()
    for index, chunk in enumerate(selected, start=1):
        url = chunk.source_url
        if (
            url
            and url not in seen_urls
            and is_public_citation_url(url, allowed_domains=allowed)
        ):
            seen_urls.add(url)
            citation_urls.append(url)

        if chunk.fetched_at is not None:
            chunk_date = chunk.fetched_at.date()
            if latest is None or chunk_date > latest:
                latest = chunk_date
        body = chunk.text.strip()
        if len(body) > _MAX_CHUNK_TEXT_CHARS:
            body = body[:_MAX_CHUNK_TEXT_CHARS].rstrip() + " …"
        blocks.append(
            "\n".join(
                [
                    f"[Source {index}]",
                    f"doc_type: {chunk.doc_type}",
                    f"section: {chunk.section}",
                    f"url: {chunk.source_url}",
                    f"fetched_at: {chunk.fetched_at.isoformat() if chunk.fetched_at else 'unknown'}",
                    body,
                ]
            )
        )

    citation_urls.sort(
        key=lambda u: (0 if is_amc_product_page_url(u) else 1, u),
    )

    return AssembledContext(
        context_text="\n\n---\n\n".join(blocks),
        chunks=selected,
        citation_urls=citation_urls,
        last_updated=latest,
    )


def _dedupe_by_source_url(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """Keep best chunk per source section (same URL may have multiple sections, e.g. KIM pages)."""
    best_by_key: dict[str, RetrievedChunk] = {}
    for chunk in chunks:
        key = f"{chunk.source_url}::{chunk.section}"
        existing = best_by_key.get(key)
        if existing is None or chunk.score > existing.score:
            best_by_key[key] = chunk
    return sorted(best_by_key.values(), key=lambda c: c.score, reverse=True)
