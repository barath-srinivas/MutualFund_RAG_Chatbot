from __future__ import annotations

from src.retrieval.models import RetrievedChunk
from src.retrieval.retriever import _ensure_holdings_sections


def _chunk(section: str, score: float, chunk_id: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        text=f"body for {section}",
        score=score,
        scheme_id="icici-nifty-bank",
        doc_type="amc_product_page",
        source_url="https://example.com/fund",
        section=section,
        topic=None,
        fetched_at=None,
    )


def test_ensure_holdings_sections_injects_top_holdings() -> None:
    selected = [
        _chunk("Fund metrics", 0.9, "a"),
        _chunk("Sector allocation", 0.8, "b"),
        _chunk("Product page overview", 0.7, "c"),
    ]
    candidates = selected + [_chunk("Top holdings", 0.5, "d")]
    out = _ensure_holdings_sections(selected, candidates, max_k=3)
    sections = {(c.section or "").lower() for c in out}
    assert "top holdings" in sections
