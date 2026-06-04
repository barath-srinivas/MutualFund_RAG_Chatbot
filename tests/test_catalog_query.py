from __future__ import annotations

from src.guardrails.structured_request import is_catalog_query
from src.retrieval.retriever import _filter_chunks_to_registry_scope
from src.retrieval.models import RetrievedChunk
from src.schemes.registry import get_scheme_registry


def test_is_catalog_query_detects_list_all() -> None:
    assert is_catalog_query("List the expense ratio of all the funds in a tabular format")
    assert not is_catalog_query("Expense ratio of Large Cap Fund?")


def test_filter_drops_unscoped_etf_chunks() -> None:
    registry = get_scheme_registry()
    etf = RetrievedChunk(
        chunk_id="x",
        text="ICICI Prudential Nifty 100 Low Volatility 30 ETF expense ratio 0.42% p.a.",
        score=0.9,
        scheme_id=None,
        doc_type="factsheet",
        source_url="https://digitalfactsheet.icicipruamc.com/passive/pdf/x.pdf",
        section="p1",
        topic=None,
    )
    in_scope = RetrievedChunk(
        chunk_id="y",
        text="ICICI Prudential Multi Asset Fund Total Expense Ratio Direct 0.53%",
        score=0.8,
        scheme_id="icici-multi-asset",
        doc_type="kim",
        source_url="https://www.icicipruamc.com/example.pdf",
        section="p1",
        topic=None,
    )
    filtered = _filter_chunks_to_registry_scope([etf, in_scope], registry)
    assert len(filtered) == 1
    assert filtered[0].chunk_id == "y"
