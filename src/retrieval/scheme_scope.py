from __future__ import annotations

import re

from src.retrieval.reranker import _text_matches_scheme
from src.schemes.registry import SchemeRegistry

# Distinctive names that appear in the passive combined factsheet but are NOT in-scope.
_PASSIVE_ONLY_FUNDS = (
    "NASDAQ 100",
    "NASDAQ-100",
    "NASDAQ 100 Index Fund",
    "BHARAT 22",
    "Passive Strategy Fund",
    "Multi Sector Passive",
)


def distinctive_phrases_for_scheme(registry: SchemeRegistry, scheme_id: str) -> list[str]:
    return registry.search_phrases_for_scheme(scheme_id)


def phrases_for_other_schemes(
    registry: SchemeRegistry, target_scheme_id: str
) -> list[str]:
    phrases: list[str] = []
    for scheme in registry.list_schemes():
        if scheme.scheme_id == target_scheme_id:
            continue
        phrases.extend(registry.search_phrases_for_scheme(scheme.scheme_id))
    for name in _PASSIVE_ONLY_FUNDS:
        phrases.append(name)
    return _dedupe_phrases(phrases)


def chunk_is_relevant_to_scheme(
    *,
    text: str,
    scheme_id: str,
    target_phrases: list[str],
    other_phrases: list[str],
    chunk_scheme_id: str | None,
) -> bool:
    """Keep chunks that support the target scheme and do not clearly describe another fund."""
    if chunk_scheme_id and chunk_scheme_id == scheme_id:
        return True

    if not _text_matches_scheme(text, target_phrases):
        return False

    return not _text_mentions_other_fund(text, other_phrases, target_phrases)


def _text_mentions_other_fund(
    text: str, other_phrases: list[str], target_phrases: list[str]
) -> bool:
    lowered = text.lower()
    for phrase in sorted(other_phrases, key=len, reverse=True):
        p = phrase.lower().strip()
        if len(p) < 6:
            continue
        if p in lowered and not _phrase_is_subsumed_by_target(p, target_phrases):
            return True
    return False


def _phrase_is_subsumed_by_target(phrase: str, target_phrases: list[str]) -> bool:
    for target in target_phrases:
        t = target.lower()
        if phrase in t or t in phrase:
            return True
    return False


def answer_mentions_foreign_fund(
    answer: str,
    *,
    target_scheme_id: str,
    registry: SchemeRegistry,
) -> bool:
    """True if the answer clearly describes a different fund than the one asked about."""
    target_phrases = distinctive_phrases_for_scheme(registry, target_scheme_id)
    other_phrases = phrases_for_other_schemes(registry, target_scheme_id)
    lowered = answer.lower()

    for phrase in sorted(other_phrases, key=len, reverse=True):
        p = phrase.lower().strip()
        if len(p) < 8:
            continue
        if p in lowered and not _phrase_is_subsumed_by_target(p, target_phrases):
            return True

    for name in _PASSIVE_ONLY_FUNDS:
        if name.lower() in lowered and not _phrase_is_subsumed_by_target(
            name.lower(), target_phrases
        ):
            return True
    return False


def _dedupe_phrases(phrases: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for phrase in phrases:
        key = re.sub(r"\s+", " ", phrase.lower().strip())
        if key and key not in seen and len(key) > 5:
            seen.add(key)
            out.append(phrase)
    return out
