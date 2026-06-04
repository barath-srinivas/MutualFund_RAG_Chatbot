from __future__ import annotations

from src.retrieval.intent import QueryIntent
from src.retrieval.models import RetrievedChunk
from src.retrieval.reranker import rerank_chunks
from src.retrieval.retriever import _is_low_confidence


def _chunk(**kwargs: object) -> RetrievedChunk:
    defaults = {
        "chunk_id": "c1",
        "text": "Exit load for Redemption: 1% within one year.",
        "score": 0.25,
        "scheme_id": "icici-multi-asset",
        "doc_type": "kim",
        "source_url": "https://www.icicipruamc.com/example.pdf",
        "section": "Scheme Details",
        "topic": None,
    }
    defaults.update(kwargs)
    return RetrievedChunk(**defaults)  # type: ignore[arg-type]


def test_rerank_boosts_scheme_kim_and_keywords() -> None:
    weak = _chunk(score=0.2, doc_type="factsheet", scheme_id="")
    strong = _chunk(score=0.22, doc_type="kim", scheme_id="icici-multi-asset")
    ranked = rerank_chunks(
        [weak, strong],
        QueryIntent.FEES,
        query="What is the exit load for the Multi Asset Fund?",
        scheme_id="icici-multi-asset",
        scheme_phrases=["Multi Asset Fund"],
    )
    assert ranked[0].chunk_id == strong.chunk_id
    assert ranked[0].score > ranked[1].score


def test_low_confidence_false_when_keywords_match() -> None:
    chunks = [_chunk()]
    assert (
        _is_low_confidence(
            best_score=0.25,
            min_score=0.58,
            query="exit load Multi Asset Fund",
            chunks=chunks,
            scheme_phrases=["Multi Asset Fund"],
        )
        is False
    )
