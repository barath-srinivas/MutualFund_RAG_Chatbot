from __future__ import annotations

from datetime import date

from src.retrieval.holdings_answer import (
    build_holdings_answer,
    extract_holdings_rows,
)
from src.retrieval.models import AssembledContext, RetrievedChunk


def test_extract_holdings_rows_from_numbered_list() -> None:
    text = (
        "Top holdings by portfolio weight (%):\n"
        "1. HDFC Bank Ltd.: 18.92%\n"
        "2. ICICI Bank Ltd.: 14.05%\n"
        "3. Axis Bank Ltd.: 9.97%\n"
    )
    rows = extract_holdings_rows(text)
    assert rows == [
        ("HDFC Bank Ltd.", "18.92"),
        ("ICICI Bank Ltd.", "14.05"),
        ("Axis Bank Ltd.", "9.97"),
    ]


def test_build_holdings_answer_from_context() -> None:
    chunk = RetrievedChunk(
        chunk_id="x",
        text=(
            "Top holdings by portfolio weight (%):\n"
            "1. HDFC Bank Ltd.: 18.92%\n"
            "2. ICICI Bank Ltd.: 14.05%\n"
            "3. Axis Bank Ltd.: 9.97%\n"
        ),
        score=0.9,
        scheme_id="icici-nifty-bank",
        doc_type="amc_product_page",
        source_url="https://www.icicipruamc.com/mutual-fund/index-funds/icici-prudential-nifty-bank-index-fund/1839",
        section="Top holdings",
        topic=None,
        fetched_at=None,
    )
    ctx = AssembledContext(
        context_text=chunk.text,
        chunks=[chunk],
        citation_urls=[chunk.source_url],
        last_updated=date(2026, 6, 5),
    )
    answer = build_holdings_answer(
        scheme_display_name="ICICI Prudential Nifty Bank Index Fund Direct Growth",
        context=ctx,
        citation_url=chunk.source_url,
        last_updated=date(2026, 6, 5),
    )
    assert answer is not None
    assert "HDFC Bank Ltd." in answer
    assert "18.92%" in answer
    assert "ICICI Bank Ltd." in answer
    assert "not explicitly listed" not in answer.lower()
    assert "http" not in answer
