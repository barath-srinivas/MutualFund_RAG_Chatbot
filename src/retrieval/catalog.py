from __future__ import annotations

from src.guardrails.structured_request import is_catalog_query
from src.retrieval.assembler import assemble_context
from src.retrieval.intent import QueryIntent, detect_intent
from src.retrieval.models import AssembledContext, RetrievedChunk
from src.retrieval.retriever import Retriever
from src.schemes.registry import SchemeRegistry

_TOPIC_QUERIES: dict[QueryIntent, str] = {
    QueryIntent.FEES: "What is the total expense ratio for the direct plan?",
    QueryIntent.FUND_MANAGEMENT: "Who manages this fund?",
    QueryIntent.BENCHMARK: "What is the benchmark index?",
    QueryIntent.GENERAL: "What are the key scheme facts?",
}


def build_catalog_context(
    *,
    message: str,
    registry: SchemeRegistry,
    retriever: Retriever,
) -> AssembledContext | None:
    """Retrieve once per in-scope scheme and merge context for list/table-style questions."""
    intent = detect_intent(message)
    per_scheme_question = _TOPIC_QUERIES.get(intent, _TOPIC_QUERIES[QueryIntent.GENERAL])

    blocks: list[str] = []
    all_chunks: list[RetrievedChunk] = []

    for scheme in registry.list_schemes():
        label = scheme.aliases[0] if scheme.aliases else scheme.display_name
        query = f"{per_scheme_question} ({label})"
        result, ctx = retriever.retrieve(message=query, scheme_id=scheme.scheme_id)
        if not ctx or not ctx.context_text.strip():
            blocks.append(f"[{scheme.scheme_id}] {scheme.display_name}: (no data in corpus)")
            continue
        all_chunks.extend(ctx.chunks[:2])
        blocks.append(
            f"=== {scheme.display_name} | scheme_id={scheme.scheme_id} ===\n{ctx.context_text[:1200]}"
        )

    if not blocks:
        return None

    merged_text = "\n\n".join(blocks)
    assembled = assemble_context(all_chunks) if all_chunks else None
    citation_urls = assembled.citation_urls if assembled else []
    last_updated = assembled.last_updated if assembled else None

    return AssembledContext(
        context_text=merged_text,
        chunks=all_chunks,
        citation_urls=citation_urls,
        last_updated=last_updated,
    )
