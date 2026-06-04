from __future__ import annotations

import re

from src.retrieval.intent import QueryIntent, preferred_doc_types, preferred_topic
from src.retrieval.models import RetrievedChunk

_DOC_TYPE_BOOST = 0.12
_TOPIC_BOOST = 0.10
_SCHEME_ID_BOOST = 0.22
_SCHEME_TEXT_BOOST = 0.18
_SHARED_PENALTY = 0.08
_KEYWORD_BOOST = 0.15

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def rerank_chunks(
    chunks: list[RetrievedChunk],
    intent: QueryIntent,
    *,
    query: str = "",
    scheme_id: str | None = None,
    scheme_phrases: list[str] | None = None,
) -> list[RetrievedChunk]:
    """Rerank by intent hints, scheme match, and keyword overlap; updates chunk.score in place."""
    doc_prefs = preferred_doc_types(intent)
    topic_pref = preferred_topic(intent)
    shared_doc_types = {"amfi", "sebi", "amc_faq"}
    query_tokens = _important_tokens(query)

    scored: list[tuple[float, RetrievedChunk]] = []
    for chunk in chunks:
        score = chunk.score
        if doc_prefs and chunk.doc_type in doc_prefs:
            score += _DOC_TYPE_BOOST
        if topic_pref and chunk.topic == topic_pref:
            score += _TOPIC_BOOST
        if intent != QueryIntent.OPERATIONAL and chunk.doc_type in shared_doc_types:
            score -= _SHARED_PENALTY

        if scheme_id:
            chunk_scheme = (chunk.scheme_id or "").strip()
            if chunk_scheme == scheme_id:
                score += _SCHEME_ID_BOOST
            elif scheme_phrases and _text_matches_scheme(chunk.text, scheme_phrases):
                score += _SCHEME_TEXT_BOOST
            elif chunk_scheme and chunk_scheme != scheme_id:
                score -= _SHARED_PENALTY

        if query_tokens and _keyword_overlap(query_tokens, chunk.text):
            score += _KEYWORD_BOOST

        chunk.score = score
        scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored]


def _important_tokens(query: str) -> set[str]:
    stop = {
        "what",
        "is",
        "the",
        "for",
        "of",
        "a",
        "an",
        "who",
        "how",
        "does",
        "do",
        "fund",
        "icici",
        "prudential",
        "direct",
        "growth",
        "plan",
    }
    return {t for t in _TOKEN_RE.findall(query.lower()) if len(t) > 2 and t not in stop}


def _keyword_overlap(query_tokens: set[str], text: str) -> bool:
    text_lower = text.lower()
    hits = sum(1 for token in query_tokens if token in text_lower)
    return hits >= min(2, len(query_tokens))


def _text_matches_scheme(text: str, phrases: list[str]) -> bool:
    text_lower = text.lower()
    for phrase in phrases:
        if phrase.lower() in text_lower:
            return True
    return False
