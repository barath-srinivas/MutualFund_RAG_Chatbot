from __future__ import annotations

import logging
from typing import Any

from src.config.settings import get_settings
from src.ingest.embedder import Embedder, create_embedder
from src.ingest.manifest import load_manifest
from src.ingest.vector_store import ChromaVectorStore
from src.retrieval.assembler import assemble_context
from src.retrieval.intent import QueryIntent, detect_intent
from src.retrieval.models import AssembledContext, RetrievedChunk, RetrievalResult
from src.retrieval.reranker import _keyword_overlap, _important_tokens, _text_matches_scheme, rerank_chunks
from src.retrieval.scheme_scope import (
    chunk_is_relevant_to_scheme,
    phrases_for_other_schemes,
)
from src.schemes.registry import SchemeRegistry, get_scheme_registry

logger = logging.getLogger(__name__)


class Retriever:
    """
    Phase 2 retriever:
    - Embed query with local BGE (same model as ingest)
    - Search Chroma with scheme/topic/doc_type hints
    - Rerank and assemble context for generation
    """

    def __init__(
        self,
        *,
        embedder: Embedder | None = None,
        vector_store: ChromaVectorStore | None = None,
        registry: SchemeRegistry | None = None,
    ) -> None:
        settings = get_settings()
        self._settings = settings
        self._embedder = embedder or create_embedder()
        self._store = vector_store or ChromaVectorStore()
        self._manifest = load_manifest()
        self._registry = registry or get_scheme_registry()

    def retrieve(
        self,
        *,
        message: str,
        scheme_id: str | None,
    ) -> tuple[RetrievalResult, AssembledContext | None]:
        intent = detect_intent(message)
        query_embedding = self._embedder.embed_query(message)

        where = self._build_where(intent=intent, scheme_id=scheme_id)
        candidate_hits = self._store.query(
            query_embedding,
            n_results=self._settings.retrieval_candidate_k,
            where=where,
        )

        chunks = [_to_retrieved_chunk(hit) for hit in candidate_hits]

        scheme_phrases = (
            self._registry.search_phrases_for_scheme(scheme_id) if scheme_id else None
        )
        other_phrases = (
            phrases_for_other_schemes(self._registry, scheme_id) if scheme_id else None
        )

        if scheme_id and scheme_phrases is not None and other_phrases is not None:
            chunks = [
                c
                for c in chunks
                if chunk_is_relevant_to_scheme(
                    text=c.text,
                    scheme_id=scheme_id,
                    target_phrases=scheme_phrases,
                    other_phrases=other_phrases,
                    chunk_scheme_id=c.scheme_id,
                )
            ]

        # Shared passive factsheet: only add chunks that mention the target scheme, never other funds.
        min_scheme_chunks = 3
        if scheme_id and scheme_phrases and len(chunks) < min_scheme_chunks:
            broad_hits = self._store.query(
                query_embedding,
                n_results=self._settings.retrieval_candidate_k * 2,
                where=None,
            )
            seen = {c.chunk_id for c in chunks}
            for hit in broad_hits:
                chunk = _to_retrieved_chunk(hit)
                if chunk.chunk_id in seen:
                    continue
                if not chunk_is_relevant_to_scheme(
                    text=chunk.text,
                    scheme_id=scheme_id,
                    target_phrases=scheme_phrases,
                    other_phrases=other_phrases or [],
                    chunk_scheme_id=chunk.scheme_id,
                ):
                    continue
                chunks.append(chunk)
                seen.add(chunk.chunk_id)

        if scheme_id is None:
            chunks = _filter_chunks_to_registry_scope(chunks, self._registry)

        if not chunks:
            return RetrievalResult(chunks=[], best_score=0.0, low_confidence=True), None

        chunks.sort(key=lambda c: c.score, reverse=True)
        chunks = rerank_chunks(
            chunks,
            intent,
            query=message,
            scheme_id=scheme_id,
            scheme_phrases=scheme_phrases,
        )
        if scheme_id and scheme_phrases and other_phrases is not None:
            relevant = [
                c
                for c in chunks
                if chunk_is_relevant_to_scheme(
                    text=c.text,
                    scheme_id=scheme_id,
                    target_phrases=scheme_phrases,
                    other_phrases=other_phrases,
                    chunk_scheme_id=c.scheme_id,
                )
            ]
            chunks = relevant

        top_k = min(self._settings.retrieval_top_k, len(chunks))
        selected = chunks[:top_k]
        if intent == QueryIntent.HOLDINGS:
            selected = _ensure_holdings_sections(selected, chunks, max_k=top_k)
        selected = _prioritize_for_context(selected, message, intent=intent)

        best_score = max((c.score for c in selected), default=0.0)
        low_confidence = _is_low_confidence(
            best_score=best_score,
            min_score=self._settings.retrieval_min_score,
            query=message,
            chunks=selected,
            scheme_phrases=scheme_phrases,
        )

        result = RetrievalResult(
            chunks=selected,
            best_score=best_score,
            low_confidence=low_confidence,
        )

        context = assemble_context(selected)
        return result, context

    def factsheet_fallback_url(self, scheme_id: str | None) -> str | None:
        if not scheme_id:
            return None
        return self._manifest.factsheet_url_for_scheme(scheme_id)

    def _build_where(self, *, intent: QueryIntent, scheme_id: str | None) -> dict[str, Any] | None:
        """Metadata filters: strict by scheme_id for scheme-specific queries, shared for operational."""
        if intent == QueryIntent.OPERATIONAL:
            return {"doc_type": {"$in": ["amc_faq", "amfi", "sebi"]}}

        if scheme_id:
            return {"scheme_id": scheme_id}

        return None


def _filter_chunks_to_registry_scope(
    chunks: list[RetrievedChunk],
    registry: SchemeRegistry,
) -> list[RetrievedChunk]:
    """Drop passive-factsheet ETF chunks that do not relate to an in-scope scheme."""
    scoped: list[RetrievedChunk] = []
    for chunk in chunks:
        sid = (chunk.scheme_id or "").strip()
        if sid and registry.is_valid_scheme_id(sid):
            scoped.append(chunk)
            continue
        for scheme in registry.list_schemes():
            phrases = registry.search_phrases_for_scheme(scheme.scheme_id)
            if _text_matches_scheme(chunk.text, phrases):
                scoped.append(chunk)
                break
    return scoped


def _prioritize_for_context(
    chunks: list[RetrievedChunk],
    query: str,
    *,
    intent: QueryIntent,
) -> list[RetrievedChunk]:
    """Put intent-relevant sections and query keyword hits first for context assembly."""
    tokens = _important_tokens(query)

    def sort_key(chunk: RetrievedChunk) -> tuple[int, int, float]:
        keyword_hit = 1 if tokens and _keyword_overlap(tokens, chunk.text) else 0
        section_hit = 1 if _section_matches_intent(chunk.section, intent) else 0
        return (section_hit, keyword_hit, chunk.score)

    return sorted(chunks, key=sort_key, reverse=True)


def _ensure_holdings_sections(
    selected: list[RetrievedChunk],
    candidates: list[RetrievedChunk],
    *,
    max_k: int,
) -> list[RetrievedChunk]:
    """Keep Top holdings (and sector allocation) in context for holdings questions."""
    required = ("top holdings", "sector allocation")
    out = list(selected)
    for heading in required:
        match = next(
            (c for c in candidates if (c.section or "").strip().lower() == heading),
            None,
        )
        if match is None or match in out:
            continue
        if len(out) < max_k:
            out.append(match)
            continue
        drop_index = next(
            (
                i
                for i, c in enumerate(out)
                if (c.section or "").strip().lower() not in required
            ),
            None,
        )
        if drop_index is not None:
            out[drop_index] = match
        else:
            out[-1] = match
    return out


def _section_matches_intent(section: str, intent: QueryIntent) -> bool:
    heading = (section or "").strip().lower()
    if intent == QueryIntent.FUND_MANAGEMENT:
        return heading == "fund manager"
    if intent == QueryIntent.HOLDINGS:
        return heading in {"top holdings", "sector allocation"}
    return False


def _is_low_confidence(
    *,
    best_score: float,
    min_score: float,
    query: str,
    chunks: list[RetrievedChunk],
    scheme_phrases: list[str] | None,
) -> bool:
    if best_score >= min_score:
        return False
    tokens = _important_tokens(query)
    for chunk in chunks:
        if tokens and _keyword_overlap(tokens, chunk.text):
            return False
        if scheme_phrases and any(p.lower() in chunk.text.lower() for p in scheme_phrases):
            return False
    return True


def _to_retrieved_chunk(hit: dict[str, Any]) -> RetrievedChunk:
    metadata = hit.get("metadata") or {}
    fetched_at = metadata.get("fetched_at")
    from datetime import datetime

    fetched_dt = None
    if isinstance(fetched_at, str):
        try:
            fetched_dt = datetime.fromisoformat(fetched_at)
        except Exception:
            fetched_dt = None

    scheme_raw = metadata.get("scheme_id")
    scheme_id = scheme_raw if scheme_raw else None

    return RetrievedChunk(
        chunk_id=str(hit.get("chunk_id") or ""),
        text=str(hit.get("text") or ""),
        score=float(hit.get("score") or 0.0),
        scheme_id=scheme_id,
        doc_type=str(metadata.get("doc_type") or ""),
        source_url=str(metadata.get("source_url") or ""),
        section=str(metadata.get("section") or ""),
        topic=(metadata.get("topic") or None) or None,
        fetched_at=fetched_dt,
    )
