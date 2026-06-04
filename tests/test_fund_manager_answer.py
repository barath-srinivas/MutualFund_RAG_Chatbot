from __future__ import annotations

from datetime import date

from src.retrieval.fund_manager_answer import (
    build_fund_manager_answer,
    extract_fund_manager_names,
)
from src.retrieval.models import AssembledContext, RetrievedChunk
from src.retrieval.preprocessor import resolve_scheme_id
from src.schemes.registry import get_scheme_registry


def test_extract_fund_manager_names() -> None:
    text = (
        "Fund managers:\n"
        "- Mr. Nishit Patel — Having experience of 8 years\n"
        "- Ms. Ashwini Shinde — Having experience of 10 years\n"
        "- Mr. Nikhil Kabra — Having experience of 11 years\n"
    )
    names = extract_fund_manager_names(text)
    assert names == ["Mr. Nishit Patel", "Ms. Ashwini Shinde", "Mr. Nikhil Kabra"]


def test_build_fund_manager_answer_from_context() -> None:
    chunk = RetrievedChunk(
        chunk_id="x",
        text=(
            "Fund managers:\n"
            "- Mr. Nishit Patel — Having experience of 8 years\n"
            "- Ms. Ashwini Shinde — Having experience of 10 years\n"
        ),
        score=0.9,
        scheme_id="icici-nifty-500",
        doc_type="amc_product_page",
        source_url="https://www.icicipruamc.com/mutual-fund/index-funds/icici-prudential-nifty-500-index-fund/1884",
        section="Fund Manager",
        topic="fund_management",
        fetched_at=None,
    )
    ctx = AssembledContext(
        context_text=chunk.text,
        chunks=[chunk],
        citation_urls=[chunk.source_url],
        last_updated=date(2026, 6, 1),
    )
    answer = build_fund_manager_answer(
        scheme_display_name="ICICI Prudential Nifty 500 Index Fund Direct Growth",
        context=ctx,
        citation_url=chunk.source_url,
        last_updated=date(2026, 6, 1),
    )
    assert answer is not None
    assert "Nishit Patel" in answer
    assert "Ashwini Shinde" in answer
    assert "http" not in answer


def test_message_scheme_wins_over_explicit_picker() -> None:
    registry = get_scheme_registry()
    sid = resolve_scheme_id(
        "Who are the fund managers of nifty 500?",
        explicit_scheme_id="icici-nifty-bank",
        registry=registry,
    )
    assert sid == "icici-nifty-500"
