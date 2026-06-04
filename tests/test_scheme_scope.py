from __future__ import annotations

from src.retrieval.scheme_scope import (
    answer_mentions_foreign_fund,
    chunk_is_relevant_to_scheme,
    phrases_for_other_schemes,
)
from src.schemes.registry import get_scheme_registry


def test_chunk_rejects_nasdaq_for_phd_query() -> None:
    registry = get_scheme_registry()
    target = registry.search_phrases_for_scheme("icici-phd")
    other = phrases_for_other_schemes(registry, "icici-phd")
    nasdaq_text = (
        "ICICI Prudential NASDAQ 100 Index Fund. "
        "Coca-Cola European Partners US LLC 0.22% Microchip Technology Inc."
    )
    assert not chunk_is_relevant_to_scheme(
        text=nasdaq_text,
        scheme_id="icici-phd",
        target_phrases=target,
        other_phrases=other,
        chunk_scheme_id=None,
    )


def test_answer_mentions_foreign_fund_nasdaq_for_phd() -> None:
    registry = get_scheme_registry()
    answer = (
        "The companies in the ICICI Prudential NASDAQ 100 Index Fund include "
        "Coca-Cola European Partners US LLC."
    )
    assert answer_mentions_foreign_fund(
        answer, target_scheme_id="icici-phd", registry=registry
    )
